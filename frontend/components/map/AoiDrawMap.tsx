"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { KEYLESS_BASEMAP_STYLE } from "@/lib/config";
import {
  DEMO_AOI,
  DEMO_BBOX,
  type GeoJSONPolygonGeometry,
  validateAOI,
} from "@/lib/geo";
import { Button } from "@/components/ui/button";
import { Square, Pentagon, MousePointer, Trash2, Sparkles } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";

interface AoiDrawMapProps {
  initialAoi?: GeoJSONPolygonGeometry | null;
  onAoiChange: (aoi: GeoJSONPolygonGeometry | null) => void;
  onClear: () => void;
  onUseDemoArea: () => void;
}

export function AoiDrawMap({
  initialAoi,
  onAoiChange,
  onClear,
  onUseDemoArea,
}: AoiDrawMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const terraDrawRef = useRef<any>(null);

  const [activeMode, setActiveMode] = useState<string>("polygon");
  const [webGlSupported, setWebGlSupported] = useState<boolean>(true);
  const [mapLoaded, setMapLoaded] = useState<boolean>(false);

  // Initialize Map and TerraDraw
  useEffect(() => {
    let map: any = null;
    let terraDraw: any = null;

    async function initMap() {
      if (!mapContainerRef.current) return;

      try {
        const maplibregl = (await import("maplibre-gl")).default;

        // Check WebGL support safely (maplibre-gl v4 removed .supported())
        const canvas = document.createElement("canvas");
        const hasWebGL = !!(
          typeof window !== "undefined" &&
          (canvas.getContext("webgl2") || canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
        );
        if (!hasWebGL) {
          setWebGlSupported(false);
          return;
        }

        map = new maplibregl.Map({
          container: mapContainerRef.current,
          style: KEYLESS_BASEMAP_STYLE as any,
          center: [73.832, 18.528], // Synthetic demo center
          zoom: 12,
        });

        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

        map.on("load", async () => {
          mapInstanceRef.current = map;
          setMapLoaded(true);

          try {
            const {
              TerraDraw,
              TerraDrawMapLibreGLAdapter,
              TerraDrawPolygonMode,
              TerraDrawRectangleMode,
              TerraDrawSelectMode,
              TerraDrawRenderMode,
            } = await import("terra-draw");

            terraDraw = new TerraDraw({
              adapter: new TerraDrawMapLibreGLAdapter({ map }),
              modes: [
                new TerraDrawPolygonMode({
                  styles: {
                    fillColor: "#3b82f6",
                    fillOpacity: 0.25,
                    outlineColor: "#60a5fa",
                    outlineWidth: 2,
                  },
                }),
                new TerraDrawRectangleMode({
                  styles: {
                    fillColor: "#3b82f6",
                    fillOpacity: 0.25,
                    outlineColor: "#60a5fa",
                    outlineWidth: 2,
                  },
                }),
                new TerraDrawSelectMode({
                  flags: {
                    polygon: {
                      feature: {
                        draggable: true,
                        coordinates: {
                          midpoints: true,
                          draggable: true,
                          deletable: true,
                        },
                      },
                    },
                  },
                }),
                new TerraDrawRenderMode({ modeName: "render", styles: {} }),
              ],
            });

            terraDraw.start();
            terraDraw.setMode("polygon");
            terraDrawRef.current = terraDraw;

            const handleGeometryUpdate = () => {
              const snapshot = terraDraw.getSnapshot();
              if (snapshot && snapshot.length > 0) {
                const latest = snapshot[snapshot.length - 1];
                if (latest && latest.geometry && latest.geometry.type === "Polygon") {
                  onAoiChange(latest.geometry as GeoJSONPolygonGeometry);
                }
              }
            };

            terraDraw.on("finish", handleGeometryUpdate);
            terraDraw.on("change", (ids: any[], type: string) => {
              if (type === "delete") {
                const snapshot = terraDraw.getSnapshot();
                if (!snapshot || snapshot.length === 0) {
                  onAoiChange(null);
                } else {
                  handleGeometryUpdate();
                }
              } else {
                handleGeometryUpdate();
              }
            });

            // If initial AOI is provided, display it
            if (initialAoi) {
              displayAoiOnMap(map, initialAoi);
            }
          } catch (tdErr) {
            console.warn("TerraDraw could not be initialized:", tdErr);
          }
        });
      } catch (err) {
        console.warn("MapLibre GL could not be loaded:", err);
        setWebGlSupported(false);
      }
    }

    initMap();

    return () => {
      if (terraDraw) {
        try {
          terraDraw.stop();
        } catch {
          // ignore
        }
      }
      if (map) {
        try {
          map.remove();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const displayAoiOnMap = useCallback((map: any, aoi: GeoJSONPolygonGeometry) => {
    if (!map || !map.isStyleLoaded()) return;

    if (map.getSource("custom-aoi-source")) {
      map.getSource("custom-aoi-source").setData(aoi);
    } else {
      map.addSource("custom-aoi-source", {
        type: "geojson",
        data: aoi,
      });

      map.addLayer({
        id: "custom-aoi-fill",
        type: "fill",
        source: "custom-aoi-source",
        paint: {
          "fill-color": "#3b82f6",
          "fill-opacity": 0.25,
        },
      });

      map.addLayer({
        id: "custom-aoi-outline",
        type: "line",
        source: "custom-aoi-source",
        paint: {
          "line-color": "#60a5fa",
          "line-width": 2,
          "line-dasharray": [2, 1],
        },
      });
    }

    const val = validateAOI(aoi);
    if (val.valid && val.bbox) {
      const [w, s, e, n] = val.bbox;
      map.fitBounds(
        [
          [w, s],
          [e, n],
        ],
        { padding: 40, duration: 600 }
      );
    }
  }, []);

  const handleModeChange = (mode: string) => {
    setActiveMode(mode);
    if (terraDrawRef.current) {
      try {
        terraDrawRef.current.setMode(mode);
      } catch (err) {
        console.warn("Failed to set TerraDraw mode:", err);
      }
    }
  };

  const handleClearMap = () => {
    if (terraDrawRef.current) {
      try {
        terraDrawRef.current.clear();
      } catch {
        // ignore
      }
    }
    const map = mapInstanceRef.current;
    if (map && map.getSource("custom-aoi-source")) {
      if (map.getLayer("custom-aoi-fill")) map.removeLayer("custom-aoi-fill");
      if (map.getLayer("custom-aoi-outline")) map.removeLayer("custom-aoi-outline");
      map.removeSource("custom-aoi-source");
    }
    onClear();
  };

  const handleUseDemo = () => {
    const map = mapInstanceRef.current;
    if (terraDrawRef.current) {
      try {
        terraDrawRef.current.clear();
      } catch {
        // ignore
      }
    }
    if (map) {
      displayAoiOnMap(map, DEMO_AOI);
    }
    onUseDemoArea();
  };

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden border border-slate-800 bg-slate-950 flex flex-col">
      {/* Top Map Control Bar */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 bg-slate-900/90 backdrop-blur border border-slate-800 p-1.5 rounded-lg shadow-lg">
        <span className="text-xs font-semibold text-slate-400 px-2 uppercase tracking-wider">
          Draw AOI:
        </span>
        <Button
          type="button"
          size="sm"
          variant={activeMode === "polygon" ? "default" : "ghost"}
          onClick={() => handleModeChange("polygon")}
          className="text-xs"
          title="Draw Polygon Mode"
        >
          <Pentagon className="w-3.5 h-3.5 mr-1" />
          Polygon
        </Button>
        <Button
          type="button"
          size="sm"
          variant={activeMode === "rectangle" ? "default" : "ghost"}
          onClick={() => handleModeChange("rectangle")}
          className="text-xs"
          title="Draw Rectangle Mode"
        >
          <Square className="w-3.5 h-3.5 mr-1" />
          Rectangle
        </Button>
        <Button
          type="button"
          size="sm"
          variant={activeMode === "select" ? "default" : "ghost"}
          onClick={() => handleModeChange("select")}
          className="text-xs"
          title="Select and Edit Drawn Polygon"
        >
          <MousePointer className="w-3.5 h-3.5 mr-1" />
          Select/Edit
        </Button>

        <div className="h-4 w-[1px] bg-slate-700 mx-1" />

        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleUseDemo}
          className="text-xs text-amber-300 border-amber-500/40 hover:bg-amber-500/10"
        >
          <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" />
          Use demo area
        </Button>

        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={handleClearMap}
          className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
        >
          <Trash2 className="w-3.5 h-3.5 mr-1" />
          Clear
        </Button>
      </div>

      {/* Map Canvas / Container */}
      <div
        ref={mapContainerRef}
        data-testid="maplibre-container"
        className="w-full h-full flex-1"
      >
        {!webGlSupported && (
          <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-slate-400 bg-slate-900/50">
            <p className="font-semibold text-slate-200">WebGL Map Container</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              Standard OpenStreetMap raster basemap. Interactive drawing active in browser.
            </p>
          </div>
        )}
      </div>

      {/* Coordinate & Basemap Watermark */}
      <div className="absolute bottom-2 left-3 z-10 bg-slate-900/80 backdrop-blur px-2.5 py-1 rounded text-[11px] font-mono text-slate-400 border border-slate-800 pointer-events-none">
        OpenStreetMap · EPSG:4326
      </div>
    </div>
  );
}
