"use client";

import React, { useEffect, useRef, useState } from "react";
import { KEYLESS_BASEMAP_STYLE } from "@/lib/config";
import { AlertCircle, Layers } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";

export type LayerType = "difference" | "before" | "after";

interface ResultsMapProps {
  bounds: [number, number, number, number]; // [west, south, east, north]
  layers: {
    difference: string;
    before: string;
    after: string;
  };
  activeLayer: LayerType;
  opacity?: number;
}

const LAYER_KEYS: LayerType[] = ["difference", "before", "after"];

function isPowerOfTwo(n: number): boolean {
  return n > 0 && (n & (n - 1)) === 0;
}

/**
 * Loads an image URL and returns a crisp nearest-neighbor data URL whose dimensions
 * are guaranteed not to be powers of two. This avoids a MapLibre GL JS v4 WebGL
 * incomplete-texture bug where power-of-two ImageSources sample black when
 * mipmaps are not generated.
 */
async function loadNonPotCrispImageUrl(url: string): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const scale = img.width < 256 ? Math.ceil(256 / img.width) : 1;
        let targetW = img.width * scale;
        let targetH = img.height * scale;
        if (isPowerOfTwo(targetW)) targetW += 1;
        if (isPowerOfTwo(targetH)) targetH += 1;

        const canvas = document.createElement("canvas");
        canvas.width = targetW;
        canvas.height = targetH;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(url);
          return;
        }
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, 0, 0, targetW, targetH);
        resolve(canvas.toDataURL("image/png"));
      } catch {
        resolve(url);
      }
    };
    img.onerror = () => resolve(url);
    img.src = url;
  });
}

export function ResultsMap({
  bounds,
  layers,
  activeLayer,
  opacity = 0.85,
}: ResultsMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [webGlSupported, setWebGlSupported] = useState(true);
  const [styleError, setStyleError] = useState(false);

  const activeUrl = layers[activeLayer];

  useEffect(() => {
    let map: any = null;
    let cancelled = false;

    async function initMap() {
      if (!mapContainerRef.current) return;

      try {
        const canvas = document.createElement("canvas");
        const hasWebGL = !!(
          typeof window !== "undefined" &&
          (canvas.getContext("webgl2") ||
            canvas.getContext("webgl") ||
            canvas.getContext("experimental-webgl"))
        );
        if (!hasWebGL) {
          setWebGlSupported(false);
          return;
        }

        const maplibregl = (await import("maplibre-gl")).default;
        const [west, south, east, north] = bounds;
        const centerLon = (west + east) / 2;
        const centerLat = (south + north) / 2;

        // Preload crisp non-POT image URLs in parallel
        const preparedEntries = await Promise.all(
          LAYER_KEYS.map(async (key) => {
            const rawUrl = layers[key];
            if (!rawUrl) return [key, ""] as const;
            const prepared = await loadNonPotCrispImageUrl(rawUrl);
            return [key, prepared] as const;
          })
        );
        if (cancelled) return;

        const preparedLayers = Object.fromEntries(preparedEntries) as Record<
          LayerType,
          string
        >;

        map = new maplibregl.Map({
          container: mapContainerRef.current,
          style: KEYLESS_BASEMAP_STYLE as any,
          center: [centerLon, centerLat],
          zoom: 12,
        });

        map.addControl(
          new maplibregl.NavigationControl({ showCompass: false }),
          "top-right"
        );

        map.on("error", () => {
          // Non-fatal tile load errors shouldn't crash overlay
        });

        map.on("load", () => {
          if (cancelled) return;
          mapInstanceRef.current = map;
          setMapLoaded(true);

          const coords: [
            [number, number],
            [number, number],
            [number, number],
            [number, number]
          ] = [
            [west, north],
            [east, north],
            [east, south],
            [west, south],
          ];

          for (const key of LAYER_KEYS) {
            const url = preparedLayers[key];
            if (!url) continue;
            map.addSource(`sar-source-${key}`, {
              type: "image",
              url,
              coordinates: coords,
            });

            map.addLayer({
              id: `sar-layer-${key}`,
              type: "raster",
              source: `sar-source-${key}`,
              layout: {
                visibility: key === activeLayer ? "visible" : "none",
              },
              paint: {
                "raster-opacity": opacity,
                "raster-fade-duration": 0,
              },
            });
          }

          // Add AOI bounding box outline
          map.addSource("result-bbox", {
            type: "geojson",
            data: {
              type: "Feature",
              properties: {},
              geometry: {
                type: "Polygon",
                coordinates: [
                  [
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                  ],
                ],
              },
            },
          });

          map.addLayer({
            id: "result-bbox-line",
            type: "line",
            source: "result-bbox",
            paint: {
              "line-color": "#60a5fa",
              "line-width": 2,
              "line-dasharray": [2, 2],
            },
          });

          map.fitBounds(
            [
              [west, south],
              [east, north],
            ],
            { padding: 48, duration: 0 }
          );
        });
      } catch (err) {
        console.error("Results map initialization failed:", err);
        setStyleError(true);
      }
    }

    initMap();

    return () => {
      cancelled = true;
      if (map) {
        map.remove();
      }
      mapInstanceRef.current = null;
      setMapLoaded(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bounds[0], bounds[1], bounds[2], bounds[3]]);

  // Toggle visibility cleanly between preloaded image layers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapLoaded) return;

    for (const key of LAYER_KEYS) {
      const layerId = `sar-layer-${key}`;
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(
          layerId,
          "visibility",
          key === activeLayer ? "visible" : "none"
        );
      }
    }
  }, [activeLayer, mapLoaded]);

  // Update opacity
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapLoaded) return;
    for (const key of LAYER_KEYS) {
      const layerId = `sar-layer-${key}`;
      if (map.getLayer(layerId)) {
        map.setPaintProperty(layerId, "raster-opacity", opacity);
      }
    }
  }, [opacity, mapLoaded]);

  if (!webGlSupported || styleError) {
    return (
      <div className="w-full h-[460px] rounded-xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden">
        <div className="mb-3 flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>WebGL map renderer unavailable; showing direct raster preview</span>
        </div>
        <div className="relative border border-slate-700 bg-slate-950 p-2 rounded-lg shadow-inner max-w-sm">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={activeUrl}
            alt={`SAR ${activeLayer} overlay`}
            className="w-64 h-64 object-contain [image-rendering:pixelated]"
          />
        </div>
        <div className="mt-3 text-xs font-mono text-slate-400">
          Bounds: [{bounds.map((b) => b.toFixed(4)).join(", ")}]
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[460px] rounded-xl overflow-hidden border border-slate-800 bg-slate-950">
      <div ref={mapContainerRef} className="w-full h-full" data-testid="results-map-container" />
      <div className="absolute top-3 left-3 z-10 bg-slate-950/85 backdrop-blur border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 flex items-center gap-2 shadow">
        <Layers className="w-3.5 h-3.5 text-blue-400" />
        <span className="capitalize font-medium">{activeLayer} Layer</span>
      </div>
    </div>
  );
}
