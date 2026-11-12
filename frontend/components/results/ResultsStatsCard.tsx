"use client";

import React from "react";
import { BarChart2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/api";

interface ResultsStatsCardProps {
  stats: Stats;
}

export function ResultsStatsCard({ stats }: ResultsStatsCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-400" />
          Valid Pixel Statistics
        </CardTitle>
        <CardDescription>Computed strictly on non-nodata intersecting pixels.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <span className="text-xs text-slate-500 block">Mean Difference</span>
            <span className="text-lg font-mono font-bold text-white" data-testid="stat-mean">
              {stats.mean.toFixed(4)} dB
            </span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <span className="text-xs text-slate-500 block">Std Deviation</span>
            <span className="text-lg font-mono font-bold text-white" data-testid="stat-std">
              {stats.std.toFixed(4)} dB
            </span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <span className="text-xs text-slate-500 block">Median</span>
            <span className="text-sm font-mono font-semibold text-slate-200">
              {stats.median.toFixed(4)} dB
            </span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
            <span className="text-xs text-slate-500 block">Min / Max</span>
            <span className="text-sm font-mono font-semibold text-slate-200">
              {stats.min.toFixed(2)} / {stats.max.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800 space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-400">Valid Pixels:</span>
            <span className="font-mono text-emerald-400" data-testid="stat-valid-pixels">
              {stats.valid_pixel_count.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Invalid / Masked (nodata):</span>
            <span className="font-mono text-amber-400" data-testid="stat-invalid-pixels">
              {stats.invalid_pixel_count.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Total Window Pixels:</span>
            <span className="font-mono text-slate-300">
              {stats.total_pixel_count.toLocaleString()}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

