"use client";

import React from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

export const PIPELINE_STAGES = [
  { id: "queued", label: "Queued in worker pool" },
  { id: "validating", label: "Pre-execution validation" },
  { id: "reading", label: "Reading raster data window" },
  { id: "aligning", label: "Checking grid alignment & CRS" },
  { id: "differencing", label: "SAR backscatter differencing (dB)" },
  { id: "statistics", label: "Computing valid pixel statistics" },
  { id: "exporting", label: "Exporting GeoTIFF & visual overlays" },
  { id: "completed", label: "Completed" },
] as const;

interface PipelineStagesGridProps {
  currentStage: string;
  isJobCompleted: boolean;
  isJobFailed: boolean;
}

export function PipelineStagesGrid({
  currentStage,
  isJobCompleted,
  isJobFailed,
}: PipelineStagesGridProps) {
  const currentStageIndex = PIPELINE_STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="space-y-3 py-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Pipeline Stages
      </span>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isPassed = !isJobFailed && (isJobCompleted || idx < currentStageIndex);
          const isCurrent = !isJobCompleted && !isJobFailed && stage.id === currentStage;

          return (
            <div
              key={stage.id}
              className={`p-3 rounded-lg border flex items-start gap-2.5 transition-colors ${
                isPassed
                  ? "bg-emerald-950/20 border-emerald-500/30 text-slate-200"
                  : isCurrent
                  ? "bg-blue-950/40 border-blue-500/60 text-white ring-1 ring-blue-500/30"
                  : "bg-slate-950/40 border-slate-800/80 text-slate-500"
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isPassed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : (
                  <span className="w-4 h-4 rounded-full border border-slate-700 flex items-center justify-center text-[10px] font-mono">
                    {idx + 1}
                  </span>
                )}
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold block capitalize">{stage.id}</span>
                <span className="text-[11px] leading-tight block text-slate-400 mt-0.5">
                  {stage.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

