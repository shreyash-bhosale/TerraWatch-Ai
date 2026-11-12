"use client";

import React from "react";
import { Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAssetUrl } from "@/lib/api";

interface ResultsExportsCardProps {
  jobId: string;
  beforeId?: string;
  afterId?: string;
  synthetic: boolean;
  geotiffUrl: string;
  differencePngUrl: string;
}

export function ResultsExportsCard({
  jobId,
  beforeId,
  afterId,
  synthetic,
  geotiffUrl,
  differencePngUrl,
}: ResultsExportsCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Exported Artifacts & Metadata</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-xs">
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 space-y-1.5 font-mono">
          <div className="flex justify-between">
            <span className="text-slate-500">Before ID:</span>
            <span className="text-slate-200">{beforeId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">After ID:</span>
            <span className="text-slate-200">{afterId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Synthetic Flag:</span>
            <span className={synthetic ? "text-amber-400" : "text-emerald-400"}>
              {synthetic ? "true (DEMO)" : "false"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">CRS Bounds:</span>
            <span className="text-slate-300">EPSG:4326</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 pt-1">
          <a
            href={getAssetUrl(geotiffUrl)}
            download="difference.tif"
            className="flex items-center justify-between px-3 py-2 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 transition-colors"
          >
            <span>Georeferenced Difference (GeoTIFF)</span>
            <Download className="w-3.5 h-3.5 text-blue-400" />
          </a>
          <a
            href={getAssetUrl(differencePngUrl)}
            download="difference.png"
            className="flex items-center justify-between px-3 py-2 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 transition-colors"
          >
            <span>Colorized Difference Overlay (PNG)</span>
            <Download className="w-3.5 h-3.5 text-blue-400" />
          </a>
          <a
            href={getAssetUrl(`/files/outputs/${jobId}/statistics.json`)}
            download="statistics.json"
            className="flex items-center justify-between px-3 py-2 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 transition-colors"
          >
            <span>Statistics Summary (JSON)</span>
            <Download className="w-3.5 h-3.5 text-blue-400" />
          </a>
          <a
            href={getAssetUrl(`/files/outputs/${jobId}/metadata.json`)}
            download="metadata.json"
            className="flex items-center justify-between px-3 py-2 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 transition-colors"
          >
            <span>Provenance & Metadata (JSON)</span>
            <Download className="w-3.5 h-3.5 text-blue-400" />
          </a>
        </div>
      </CardContent>
    </Card>
  );
}

