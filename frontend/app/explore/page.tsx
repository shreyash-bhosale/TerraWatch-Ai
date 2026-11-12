"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  DEMO_AOI,
  validateAOI,
  getStoredAOI,
  setStoredAOI,
  clearStoredAOI,
  type GeoJSONPolygonGeometry,
  type AOIValidationResult,
} from "@/lib/geo";
import { AoiDrawMap } from "@/components/map/AoiDrawMap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Sparkles,
  Trash2,
  AlertTriangle,
  Info,
  MapPin,
  CheckCircle2,
} from "lucide-react";

export default function ExplorePage() {
  const router = useRouter();
  const [aoi, setAoi] = useState<GeoJSONPolygonGeometry | null>(null);
  const [validation, setValidation] = useState<AOIValidationResult | null>(null);

  // Initialize from sessionStorage on mount
  useEffect(() => {
    const stored = getStoredAOI();
    if (stored) {
      setAoi(stored);
      setValidation(validateAOI(stored));
    }
  }, []);

  const handleAoiChange = (newAoi: GeoJSONPolygonGeometry | null) => {
    setAoi(newAoi);
    if (!newAoi) {
      setValidation(null);
      clearStoredAOI();
    } else {
      const res = validateAOI(newAoi);
      setValidation(res);
      if (res.valid) {
        setStoredAOI(newAoi);
      }
    }
  };

  const handleUseDemoArea = () => {
    setAoi(DEMO_AOI);
    const res = validateAOI(DEMO_AOI);
    setValidation(res);
    setStoredAOI(DEMO_AOI);
  };

  const handleClear = () => {
    setAoi(null);
    setValidation(null);
    clearStoredAOI();
  };

  const handleProceed = () => {
    if (aoi && validation?.valid) {
      setStoredAOI(aoi);
      router.push("/observations");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-blue-400 border-blue-500/30">
              Step 1 of 4
            </Badge>
            <span className="text-xs text-slate-400">Area of Interest (AOI)</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Select Study Area
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl">
            Draw a custom polygon/rectangle on the map or click <strong>Use demo area</strong> to load the pre-computed synthetic test fixture footprint.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleUseDemoArea}
            className="text-amber-300 border-amber-500/40 hover:bg-amber-500/10 text-xs"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" />
            Use demo area
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={!aoi}
            className="text-slate-400 hover:text-red-400 text-xs"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Main Grid: Map + Metrics Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Column */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          <AoiDrawMap
            initialAoi={aoi}
            onAoiChange={handleAoiChange}
            onClear={handleClear}
            onUseDemoArea={handleUseDemoArea}
          />

          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>Keyless OpenStreetMap basemap · WGS84 (EPSG:4326)</span>
            <span>Maximum AOI area: 50,000 km² · Max vertices: 500</span>
          </div>
        </div>

        {/* Metrics & Action Column */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
                  <MapPin className="w-4 h-4 text-blue-400" />
                  AOI Metrics
                </CardTitle>
                {validation?.valid && (
                  <Badge variant="success" className="text-[11px]">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Valid Geometry
                  </Badge>
                )}
              </div>
              <CardDescription>
                Calculated surface area and spatial bounds for the selected study region.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {validation?.error ? (
                <Alert variant="destructive">
                  <AlertTriangle className="w-4 h-4" />
                  <AlertTitle>Invalid Geometry</AlertTitle>
                  <AlertDescription className="text-xs mt-1">
                    {validation.error}
                  </AlertDescription>
                </Alert>
              ) : validation?.valid ? (
                <div className="flex flex-col gap-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                      <span className="text-[11px] text-slate-500 block uppercase tracking-wider">
                        Surface Area
                      </span>
                      <span className="text-base font-semibold text-white mt-0.5 block">
                        {validation.areaKm2 !== undefined
                          ? `${validation.areaKm2.toFixed(2)} km²`
                          : "—"}
                      </span>
                    </div>
                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                      <span className="text-[11px] text-slate-500 block uppercase tracking-wider">
                        Vertices
                      </span>
                      <span className="text-base font-semibold text-white mt-0.5 block">
                        {validation.vertexCount ?? "—"}
                      </span>
                    </div>
                  </div>

                  {validation.centroid && (
                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                      <span className="text-[11px] text-slate-500 block uppercase tracking-wider">
                        Centroid (Lon, Lat)
                      </span>
                      <span className="text-xs font-mono text-slate-200 mt-0.5 block">
                        {validation.centroid[0].toFixed(4)}°, {validation.centroid[1].toFixed(4)}°
                      </span>
                    </div>
                  )}

                  {validation.bbox && (
                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                      <span className="text-[11px] text-slate-500 block uppercase tracking-wider">
                        Bounding Box (W, S, E, N)
                      </span>
                      <span className="text-xs font-mono text-slate-200 mt-0.5 block">
                        [{validation.bbox[0].toFixed(3)}°, {validation.bbox[1].toFixed(3)}°,{" "}
                        {validation.bbox[2].toFixed(3)}°, {validation.bbox[3].toFixed(3)}°]
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-slate-500 flex flex-col items-center justify-center gap-2 border border-dashed border-slate-800 rounded-lg">
                  <Info className="w-6 h-6 text-slate-600" />
                  <p className="text-xs font-medium text-slate-400">No area selected yet</p>
                  <p className="text-[11px] text-slate-500 max-w-xs">
                    Draw a polygon using the controls on the map, or click <strong>Use demo area</strong> above.
                  </p>
                </div>
              )}

              {/* Next Step CTA */}
              <div className="pt-2 border-t border-slate-800/80 flex flex-col gap-2">
                <Button
                  type="button"
                  size="lg"
                  disabled={!aoi || !validation?.valid}
                  onClick={handleProceed}
                  className="w-full shadow-lg shadow-blue-600/20"
                >
                  <span>Next: Select Observations</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
                <p className="text-[11px] text-center text-slate-500">
                  Searches provider catalog for radar observations covering this AOI.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
