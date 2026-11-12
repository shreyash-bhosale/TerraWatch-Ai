import type { components } from "./api-types";

export type GeoJSONPolygonGeometry = components["schemas"]["GeoJSONPolygonGeometry"];

export const DEMO_AOI: GeoJSONPolygonGeometry = {
  type: "Polygon",
  coordinates: [
    [
      [73.800, 18.496],
      [73.864, 18.496],
      [73.864, 18.560],
      [73.800, 18.560],
      [73.800, 18.496],
    ],
  ],
};

export const MAX_AOI_AREA_KM2 = 50000;
export const MAX_AOI_VERTICES = 500;

export interface AOIValidationResult {
  valid: boolean;
  error?: string;
  areaKm2?: number;
  bbox?: [number, number, number, number];
  centroid?: [number, number];
  vertexCount?: number;
}

/**
 * Calculates spherical surface area of a polygon ring in square kilometers.
 * Uses spherical polygon line-integral formula with Earth mean radius R = 6371.0088 km.
 */
export function calculateSphericalAreaKm2(coords: number[][]): number {
  if (!coords || coords.length < 4) return 0;
  const R = 6371.0088; // Earth radius in km
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const [p1Lon, p1Lat] = coords[i];
    const [p2Lon, p2Lat] = coords[i + 1];
    const dLon = ((p2Lon - p1Lon) * Math.PI) / 180;
    const lat1 = (p1Lat * Math.PI) / 180;
    const lat2 = (p2Lat * Math.PI) / 180;
    total += dLon * (2 + Math.sin(lat1) + Math.sin(lat2));
  }
  return Math.abs((total * (R * R)) / 2);
}

/**
 * Calculates bounding box [west, south, east, north] (minLon, minLat, maxLon, maxLat)
 */
export function calculateBoundingBox(coords: number[][]): [number, number, number, number] {
  if (!coords || coords.length === 0) return [0, 0, 0, 0];
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  for (const [lon, lat] of coords) {
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  return [minLon, minLat, maxLon, maxLat];
}

/**
 * Calculates centroid [lon, lat] of polygon coordinates
 */
export function calculateCentroid(coords: number[][]): [number, number] {
  if (!coords || coords.length === 0) return [0, 0];
  const n = coords.length - 1;
  if (n < 3) {
    const sumLon = coords.reduce((acc, c) => acc + c[0], 0);
    const sumLat = coords.reduce((acc, c) => acc + c[1], 0);
    return [sumLon / coords.length, sumLat / coords.length];
  }

  let signedArea = 0;
  let cx = 0;
  let cy = 0;

  for (let i = 0; i < n; i++) {
    const [x0, y0] = coords[i];
    const [x1, y1] = coords[i + 1];
    const a = x0 * y1 - x1 * y0;
    signedArea += a;
    cx += (x0 + x1) * a;
    cy += (y0 + y1) * a;
  }

  signedArea *= 0.5;
  if (Math.abs(signedArea) < 1e-10) {
    const distinct = coords.slice(0, n);
    const sumLon = distinct.reduce((acc, c) => acc + c[0], 0);
    const sumLat = distinct.reduce((acc, c) => acc + c[1], 0);
    return [sumLon / distinct.length, sumLat / distinct.length];
  }

  cx = cx / (6 * signedArea);
  cy = cy / (6 * signedArea);
  return [cx, cy];
}

function ccw(p1: number[], p2: number[], p3: number[]): number {
  return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0]);
}

function segmentsIntersect(a: number[], b: number[], c: number[], d: number[]): boolean {
  const ccw1 = ccw(a, b, c);
  const ccw2 = ccw(a, b, d);
  const ccw3 = ccw(c, d, a);
  const ccw4 = ccw(c, d, b);

  return (
    ((ccw1 > 0 && ccw2 < 0) || (ccw1 < 0 && ccw2 > 0)) &&
    ((ccw3 > 0 && ccw4 < 0) || (ccw3 < 0 && ccw4 > 0))
  );
}

/**
 * Validates GeoJSON Polygon geometry according to FR-02 and FR-03:
 * - valid GeoJSON polygon structure
 * - closed ring (first vertex === last vertex)
 * - >= 3 distinct vertices
 * - lon in [-180, 180], lat in [-90, 90]
 * - vertices <= 500
 * - non-self-intersecting
 * - area > 0 and area <= 50,000 km²
 */
export function validateAOI(geom: unknown): AOIValidationResult {
  if (!geom || typeof geom !== "object") {
    return { valid: false, error: "Invalid geometry: geometry must be an object." };
  }

  const p = geom as Partial<GeoJSONPolygonGeometry>;
  if (p.type !== "Polygon") {
    return { valid: false, error: `Invalid geometry type: expected 'Polygon', got '${p.type}'.` };
  }

  if (!Array.isArray(p.coordinates) || p.coordinates.length === 0) {
    return { valid: false, error: "Invalid coordinates: coordinates must be a non-empty array of rings." };
  }

  const outerRing = p.coordinates[0];
  if (!Array.isArray(outerRing) || outerRing.length < 4) {
    return {
      valid: false,
      error: "A valid polygon requires at least 4 coordinates (at least 3 distinct vertices and a closing vertex).",
    };
  }

  if (outerRing.length > MAX_AOI_VERTICES) {
    return {
      valid: false,
      error: `AOI has ${outerRing.length} vertices, exceeding maximum allowed limit of ${MAX_AOI_VERTICES}.`,
    };
  }

  for (let i = 0; i < outerRing.length; i++) {
    const pt = outerRing[i];
    if (!Array.isArray(pt) || pt.length < 2) {
      return { valid: false, error: `Vertex at index ${i} is not a valid coordinate pair.` };
    }
    const [lon, lat] = pt;
    if (typeof lon !== "number" || isNaN(lon) || typeof lat !== "number" || isNaN(lat)) {
      return { valid: false, error: `Vertex at index ${i} contains non-numeric coordinates.` };
    }
    if (lon < -180 || lon > 180) {
      return { valid: false, error: `Longitude ${lon} at index ${i} is out of bounds [-180, 180].` };
    }
    if (lat < -90 || lat > 90) {
      return { valid: false, error: `Latitude ${lat} at index ${i} is out of bounds [-90, 90].` };
    }
  }

  // Check ring closure
  const first = outerRing[0];
  const last = outerRing[outerRing.length - 1];
  if (Math.abs(first[0] - last[0]) > 1e-7 || Math.abs(first[1] - last[1]) > 1e-7) {
    return { valid: false, error: "Polygon ring is not closed: first and last vertex must be identical." };
  }

  // Check distinct vertices
  const distinctVertices: number[][] = [];
  for (let i = 0; i < outerRing.length - 1; i++) {
    const cur = outerRing[i];
    const exists = distinctVertices.some(
      (v) => Math.abs(v[0] - cur[0]) < 1e-7 && Math.abs(v[1] - cur[1]) < 1e-7
    );
    if (!exists) {
      distinctVertices.push(cur);
    }
  }

  if (distinctVertices.length < 3) {
    return {
      valid: false,
      error: `Polygon has only ${distinctVertices.length} distinct vertex/vertices; at least 3 are required.`,
    };
  }

  // Check self-intersection for non-adjacent segments
  const n = outerRing.length - 1;
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      // Don't test the pair (0, n-1) because they share the first/last point
      if (i === 0 && j === n - 1) continue;

      if (
        segmentsIntersect(
          outerRing[i],
          outerRing[i + 1],
          outerRing[j],
          outerRing[j + 1]
        )
      ) {
        return { valid: false, error: "Polygon is self-intersecting." };
      }
    }
  }

  const areaKm2 = calculateSphericalAreaKm2(outerRing);
  if (areaKm2 <= 0.00001) {
    return { valid: false, error: "Polygon has zero surface area." };
  }

  if (areaKm2 > MAX_AOI_AREA_KM2) {
    return {
      valid: false,
      error: `AOI area (${areaKm2.toFixed(1)} km²) exceeds the maximum allowed area of ${MAX_AOI_AREA_KM2} km².`,
    };
  }

  const bbox = calculateBoundingBox(outerRing);
  const centroid = calculateCentroid(outerRing);

  return {
    valid: true,
    areaKm2,
    bbox,
    centroid,
    vertexCount: outerRing.length,
  };
}

const AOI_SESSION_KEY = "terrawatch_aoi";

export function getStoredAOI(): GeoJSONPolygonGeometry | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(AOI_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const result = validateAOI(parsed);
    if (result.valid) {
      return parsed as GeoJSONPolygonGeometry;
    }
    return null;
  } catch {
    return null;
  }
}

export function setStoredAOI(aoi: GeoJSONPolygonGeometry): boolean {
  if (typeof window === "undefined") return false;
  try {
    sessionStorage.setItem(AOI_SESSION_KEY, JSON.stringify(aoi));
    return true;
  } catch {
    return false;
  }
}

export function clearStoredAOI(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(AOI_SESSION_KEY);
  } catch {
    // ignore
  }
}
