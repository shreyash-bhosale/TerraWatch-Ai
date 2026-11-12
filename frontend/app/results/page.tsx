"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getAssetUrl, isApiError } from "@/lib/api";
import { ResultsMap, type LayerType } from "@/components/map/ResultsMap";
import { ResultsStatsCard } from "@/components/results/ResultsStatsCard";
import { ResultsExportsCard } from "@/components/results/ResultsExportsCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertTriangle,
  Download,
  Info,
  Layers,
  ArrowLeft,
  FileText,
  RefreshCw,
  ShieldAlert,
  Clock,
  XCircle,
} from "lucide-react";

function ResultsContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job");

  const [activeLayer, setActiveLayer] = useState<LayerType>("difference");
  const [opacity, setOpacity] = useState<number>(0.85);

  const {
    data: jobStatus,
    isLoading: isLoadingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ["analysis-status-for-results", jobId],
    queryFn: () => {
      if (!jobId) throw new Error("No job ID");
      return apiClient.getAnalysisStatus(jobId);
    },
    enabled: !!jobId,
    retry: false,
  });

  const {
    data: results,
    isLoading: isLoadingResults,
    error: resultsError,
    refetch,
  } = useQuery({
    queryKey: ["analysis-results", jobId],
    queryFn: () => {
      if (!jobId) throw new Error("No job ID");
      return apiClient.getAnalysisResults(jobId);
    },
    enabled: !!jobId && jobStatus?.status === "completed",
    retry: false,
  });

  if (!jobId) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        <div className="border-b border-slate-800 pb-5">
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Analysis Results
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Georeferenced SAR backscatter difference map and statistical summary.
          </p>
        </div>
        <Alert className="bg-slate-900 border-slate-800">
          <Info className="h-4 w-4 text-blue-400" />
          <AlertTitle className="text-white">No Analysis Selected</AlertTitle>
          <AlertDescription className="text-slate-400 mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <span>
              Select an Area of Interest and run a comparison, or open a completed job from the Dashboard.
            </span>
            <div className="flex gap-2">
              <Link href="/dashboard">
                <Button variant="outline" size="sm">
                  Back to Dashboard
                </Button>
              </Link>
              <Link href="/explore">
                <Button size="sm">Start New Analysis</Button>
              </Link>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoadingStatus || (jobStatus?.status === "completed" && isLoadingResults)) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="lg:col-span-2 h-[460px] w-full rounded-xl" />
          <Skeleton className="h-[460px] w-full rounded-xl" />
        </div>
      </div>
    );
  }

  const statusErrorBanner = statusError ? (
    <Alert variant="destructive">
      <XCircle className="h-4 w-4" />
      <AlertTitle>Results Not Available</AlertTitle>
      <AlertDescription className="mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <span>
          {isApiError(statusError)
            ? `${statusError.error.code}: ${statusError.error.message}`
            : "Unable to load analysis job status. Last known state is preserved if available."}
        </span>
        <div className="flex gap-2 shrink-0">
          <Button type="button" variant="outline" size="sm" onClick={() => refetchStatus()}>
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Retry
          </Button>
          <Link href="/dashboard">
            <Button variant="outline" size="sm">
              Return to Dashboard
            </Button>
          </Link>
        </div>
      </AlertDescription>
    </Alert>
  ) : null;

  if (statusError && !jobStatus) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        {statusErrorBanner}
      </div>
    );
  }

  if (jobStatus && (jobStatus.status === "queued" || jobStatus.status === "running")) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        {statusErrorBanner}
        <Alert className="border-blue-500/30 bg-blue-500/10 text-blue-200">
          <Clock className="h-4 w-4 text-blue-400" />
          <AlertTitle>Analysis Still In Progress</AlertTitle>
          <AlertDescription className="mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <span>
              Job <code className="font-mono">{jobId}</code> is currently at stage:{" "}
              <strong className="uppercase">{jobStatus.stage}</strong>.
            </span>
            <Link href={`/analysis?job=${encodeURIComponent(jobId)}`}>
              <Button size="sm">View Live Progress</Button>
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (jobStatus?.status === "failed") {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        {statusErrorBanner}
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Analysis Job Failed</AlertTitle>
          <AlertDescription className="mt-1">
            {jobStatus.error ? (
              <p>
                <strong>{jobStatus.error.code}:</strong> {jobStatus.error.message}
              </p>
            ) : (
              <p>Job processing failed before outputs could be generated.</p>
            )}
            <div className="mt-3">
              <Link href="/explore">
                <Button variant="outline" size="sm">
                  Start New Analysis
                </Button>
              </Link>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (resultsError || !results) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        {statusErrorBanner}
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Results Not Available</AlertTitle>
          <AlertDescription className="mt-1 flex items-center justify-between">
            <span>
              {isApiError(resultsError)
                ? `${resultsError.error.code}: ${resultsError.error.message}`
                : "Result artifacts could not be loaded."}
            </span>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const { statistics: stats, bounds, layers, geotiff_url, metadata, limitations, synthetic } =
    results;

  const colorScales = (metadata?.color_scales || {}) as Record<string, any>;
  const diffScale = colorScales.difference || { vmin: -7, vmax: 7, units: "dB" };
  const beforeScale = colorScales.before || { vmin: -25, vmax: 0, units: "dB" };
  const afterScale = colorScales.after || { vmin: -25, vmax: 0, units: "dB" };

  const activeScale =
    activeLayer === "difference"
      ? diffScale
      : activeLayer === "before"
      ? beforeScale
      : afterScale;

  // Deterministic, template-based result summary (FR-18)
  const deterministicSummary = `Mean difference ${stats.mean >= 0 ? "+" : ""}${stats.mean.toFixed(
    2
  )} dB over ${stats.valid_pixel_count.toLocaleString()} valid pixels (median ${stats.median.toFixed(
    2
  )} dB, range ${stats.min.toFixed(2)} to ${stats.max.toFixed(2)} dB, std ${stats.std.toFixed(
    2
  )} dB). ${stats.invalid_pixel_count.toLocaleString()} pixels masked as nodata.`;

  const layerUrls = {
    difference: getAssetUrl(layers.difference_png),
    before: getAssetUrl(layers.before_png),
    after: getAssetUrl(layers.after_png),
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
      {statusErrorBanner}
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <Badge variant="outline" className="text-blue-400 border-blue-500/30">
              Step 4 of 4
            </Badge>
            <span className="text-xs font-mono text-slate-400">{jobId}</span>
            {synthetic && (
              <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/40">
                DEMO DATA — SYNTHETIC
              </Badge>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            SAR Backscatter Difference Results
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Comparing <code className="text-slate-200">{jobStatus?.before_id}</code> (Before) →{" "}
            <code className="text-slate-200">{jobStatus?.after_id}</code> (After)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/explore">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-1.5" />
              New Analysis
            </Button>
          </Link>
          <a href={getAssetUrl(geotiff_url)} download="difference.tif">
            <Button size="sm">
              <Download className="w-4 h-4 mr-1.5" />
              Download GeoTIFF
            </Button>
          </a>
        </div>
      </div>

      {/* Deterministic Summary Banner (FR-18) */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-start gap-3">
        <FileText className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Quantitative Summary
          </h2>
          <p className="text-sm text-slate-100 mt-0.5 font-medium" data-testid="deterministic-summary">
            {deterministicSummary}
          </p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map & Layer Controls */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <Card>
            <CardHeader className="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-400" />
                  Georeferenced Raster Overlay
                </CardTitle>
                <CardDescription>
                  Toggle between backscatter difference (D = B2 − B1) and source acquisitions.
                </CardDescription>
              </div>
              <Tabs
                value={activeLayer}
                onValueChange={(v) => setActiveLayer(v as LayerType)}
              >
                <TabsList>
                  <TabsTrigger value="difference">Difference (dB)</TabsTrigger>
                  <TabsTrigger value="before">Before</TabsTrigger>
                  <TabsTrigger value="after">After</TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <ResultsMap
                bounds={bounds as [number, number, number, number]}
                layers={layerUrls}
                activeLayer={activeLayer}
                opacity={opacity}
              />

              {/* Legend & Opacity Control */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-950/60 border border-slate-800 rounded-lg p-3.5">
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">
                      {activeLayer === "difference"
                        ? "Diverging Scale (Δ dB)"
                        : `${activeLayer === "before" ? "Before" : "After"} Backscatter (dB)`}
                    </span>
                    <span className="font-mono text-slate-300">
                      [{Number(activeScale.vmin).toFixed(2)}, {Number(activeScale.vmax).toFixed(2)}] dB
                    </span>
                  </div>
                  <div
                    className="h-3 w-full rounded"
                    style={{
                      background:
                        activeLayer === "difference"
                          ? "linear-gradient(to right, #3b4cc0, #dddcdc, #b40426)"
                          : "linear-gradient(to right, #000000, #ffffff)",
                    }}
                    aria-label="Color scale bar"
                  />
                  <div className="flex justify-between text-[11px] font-mono text-slate-500">
                    <span>{Number(activeScale.vmin).toFixed(2)} dB</span>
                    {activeLayer === "difference" && <span>0.00 dB (No change)</span>}
                    <span>
                      {activeScale.vmax > 0 && activeLayer === "difference" ? "+" : ""}
                      {Number(activeScale.vmax).toFixed(2)} dB
                    </span>
                  </div>
                </div>

                <div className="flex flex-col justify-center gap-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <label htmlFor="opacity-slider" className="text-slate-400 font-medium">
                      Overlay Opacity
                    </label>
                    <span className="font-mono text-slate-300">{Math.round(opacity * 100)}%</span>
                  </div>
                  <input
                    id="opacity-slider"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={opacity}
                    onChange={(e) => setOpacity(parseFloat(e.target.value))}
                    className="w-full accent-blue-500 cursor-pointer"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Scientific Limitations Card (Section 8.4) */}
          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2 text-amber-300">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Scientific Scope & Limitations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-slate-300">
                {limitations.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* Statistics & Metadata Sidebar */}
        <div className="flex flex-col gap-6">
          <ResultsStatsCard stats={stats} />
          <ResultsExportsCard
            jobId={jobId}
            beforeId={jobStatus?.before_id}
            afterId={jobStatus?.after_id}
            synthetic={synthetic}
            geotiffUrl={geotiff_url}
            differencePngUrl={layers.difference_png}
          />
        </div>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
          <Skeleton className="h-10 w-64 mb-6" />
          <Skeleton className="h-[460px] w-full rounded-xl" />
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
