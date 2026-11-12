"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  apiClient,
  isApiError,
  saveRecentJob,
  type ValidateResponse,
  type JobStatusResponse,
} from "@/lib/api";
import { getStoredAOI, type GeoJSONPolygonGeometry } from "@/lib/geo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  Loader2,
  Clock,
  Sparkles,
  MapPin,
  ShieldCheck,
  Activity,
} from "lucide-react";

const PIPELINE_STAGES = [
  { id: "queued", label: "Queued in worker pool" },
  { id: "validating", label: "Pre-execution validation" },
  { id: "reading", label: "Reading raster data window" },
  { id: "aligning", label: "Checking grid alignment & CRS" },
  { id: "differencing", label: "SAR backscatter differencing (dB)" },
  { id: "statistics", label: "Computing valid pixel statistics" },
  { id: "exporting", label: "Exporting GeoTIFF & visual overlays" },
  { id: "completed", label: "Completed" },
] as const;

function AnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const beforeId = searchParams.get("before");
  const afterId = searchParams.get("after");
  const existingJobId = searchParams.get("job");

  const [aoi, setAoi] = useState<GeoJSONPolygonGeometry | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(existingJobId || null);

  // Load AOI from session storage
  useEffect(() => {
    const stored = getStoredAOI();
    if (stored) {
      setAoi(stored);
    }
  }, []);

  // Validation query
  const {
    data: validationData,
    isLoading: isValidating,
    error: validationError,
    refetch: revalidate,
  } = useQuery({
    queryKey: ["validate-pair", beforeId, afterId, aoi],
    queryFn: () => {
      if (!beforeId || !afterId || !aoi) {
        throw new Error("Missing required parameters for validation");
      }
      return apiClient.validateAnalysis({
        before_id: beforeId,
        after_id: afterId,
        aoi,
      });
    },
    enabled: !!beforeId && !!afterId && !!aoi && !activeJobId,
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: async () => {
      if (!beforeId || !afterId || !aoi) {
        throw new Error("Missing parameters to start analysis");
      }
      return apiClient.createAnalysis({
        before_id: beforeId,
        after_id: afterId,
        aoi,
      });
    },
    onSuccess: (res) => {
      setActiveJobId(res.job_id);
      saveRecentJob({
        jobId: res.job_id,
        beforeId: beforeId!,
        afterId: afterId!,
        createdAt: new Date().toISOString(),
        synthetic: true, // Updated on status response if needed
      });
    },
  });

  // Polling query for active job
  const {
    data: jobStatus,
    error: jobError,
    refetch: refetchJob,
  } = useQuery<JobStatusResponse>({
    queryKey: ["analysis-status", activeJobId],
    queryFn: () => {
      if (!activeJobId) throw new Error("No active job");
      return apiClient.getAnalysisStatus(activeJobId);
    },
    enabled: !!activeJobId,
    retry: false,
    refetchInterval: (query) => {
      const state = query.state.data?.status;
      if (state === "completed" || state === "failed") {
        return false;
      }
      if (query.state.status === "error") {
        return false;
      }
      return 2000; // Poll every 2 seconds (FR-10)
    },
  });

  // Update synthetic flag in local storage once status is fetched
  useEffect(() => {
    if (jobStatus && activeJobId) {
      saveRecentJob({
        jobId: activeJobId,
        beforeId: jobStatus.before_id,
        afterId: jobStatus.after_id,
        createdAt: jobStatus.created_at,
        synthetic: jobStatus.synthetic,
      });
    }
  }, [jobStatus, activeJobId]);

  if (!activeJobId && (!beforeId || !afterId)) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center flex flex-col items-center gap-4">
        <Activity className="w-12 h-12 text-slate-600 mb-2" />
        <h2 className="text-xl font-bold text-white">No Observations Selected</h2>
        <p className="text-slate-400 text-sm max-w-md">
          To validate and execute SAR change analysis, please select two observations from the catalog.
        </p>
        <Link href="/observations">
          <Button>
            <span>Go to Observations</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </Link>
      </div>
    );
  }

  const displayBeforeId = beforeId || jobStatus?.before_id || "Loading...";
  const displayAfterId = afterId || jobStatus?.after_id || "Loading...";
  const isCompatible = validationData?.compatible ?? false;
  const currentStage = jobStatus?.stage || "queued";
  const isJobRunning =
    activeJobId && jobStatus?.status !== "completed" && jobStatus?.status !== "failed";
  const isJobCompleted = jobStatus?.status === "completed";
  const isJobFailed = jobStatus?.status === "failed";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-blue-400 border-blue-500/30">
              Step 3 of 4
            </Badge>
            <span className="text-xs text-slate-400">Pair Validation & Processing</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Analysis & Execution
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl">
            Strict compatibility validation prevents comparing incompatible radar acquisitions.
            Jobs run asynchronously with live discrete stage tracking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!activeJobId && (
            <Link href="/observations">
              <Button variant="outline" size="sm" className="text-xs">
                Back to Observations
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Observation Pair Header Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-slate-900/60">
          <CardHeader className="pb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400">
              Before Observation
            </span>
            <CardTitle className="font-mono text-base">{displayBeforeId}</CardTitle>
          </CardHeader>
        </Card>

        <Card className="bg-slate-900/60">
          <CardHeader className="pb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-400">
              After Observation
            </span>
            <CardTitle className="font-mono text-base">{displayAfterId}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* SECTION 1: Active Job Execution Tracker */}
      {activeJobId ? (
        <Card className="border-blue-500/30 bg-slate-900/80">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400">
                  Execution State
                </span>
                <CardTitle className="text-lg flex items-center gap-2 mt-0.5">
                  <span>Job {activeJobId}</span>
                  {jobStatus?.synthetic && <Badge variant="synthetic">SYNTHETIC</Badge>}
                </CardTitle>
              </div>

              <div>
                {isJobRunning && (
                  <Badge variant="default" className="bg-blue-600/30 text-blue-300 border-blue-500/40">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    RUNNING
                  </Badge>
                )}
                {isJobCompleted && (
                  <Badge variant="success">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    COMPLETED
                  </Badge>
                )}
                {isJobFailed && (
                  <Badge variant="destructive">
                    <XCircle className="w-3 h-3 mr-1" />
                    FAILED
                  </Badge>
                )}
              </div>
            </div>
            <CardDescription>
              Discrete processing stages. Honest stage reporting without artificial progress percentages.
            </CardDescription>
          </CardHeader>

          <CardContent className="flex flex-col gap-6">
            {/* Polling Error Alert (FR-10 / F-04: preserve last known status and offer Retry) */}
            {jobError && (
              <Alert variant="destructive">
                <AlertTriangle className="w-4 h-4" />
                <AlertTitle>Polling Connection Error</AlertTitle>
                <AlertDescription className="mt-1 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <span>
                    {isApiError(jobError)
                      ? jobError.error.message
                      : "Failed to poll job status. Last known execution state is preserved."}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => refetchJob()}
                    className="shrink-0"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1" />
                    Retry
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Failure Alert */}
            {isJobFailed && (
              <Alert variant="destructive">
                <XCircle className="w-4 h-4" />
                <AlertTitle>
                  Analysis Failed: {jobStatus?.error?.code || "INTERNAL_ERROR"}
                </AlertTitle>
                <AlertDescription className="mt-1 text-xs">
                  {jobStatus?.error?.message || "An unhandled error occurred during pipeline execution."}
                </AlertDescription>
              </Alert>
            )}

            {/* Success Action Alert */}
            {isJobCompleted && (
              <Alert variant="success" className="bg-emerald-950/30 border-emerald-500/40">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <AlertTitle className="text-emerald-300">Processing Finished</AlertTitle>
                <AlertDescription className="text-xs text-emerald-400/90 mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <span>
                    Calibrated backscatter difference and statistical exports are ready for visualization.
                  </span>
                  <Link href={`/results?job=${encodeURIComponent(activeJobId)}`}>
                    <Button size="sm" className="bg-emerald-600 hover:bg-emerald-500 text-white">
                      <span>View Results Map</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </Link>
                </AlertDescription>
              </Alert>
            )}

            {/* Discrete Stages Stepper (Speed Accelerator & R4: No Percentages!) */}
            <div className="space-y-3 py-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Pipeline Stages
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {PIPELINE_STAGES.map((stage, idx) => {
                  const currentStageIndex = PIPELINE_STAGES.findIndex((s) => s.id === currentStage);
                  const isPassed = !isJobFailed && (isJobCompleted || idx < currentStageIndex);
                  const isCurrent = !isJobCompleted && !isJobFailed && stage.id === currentStage;
                  const isPending = !isJobCompleted && !isJobFailed && idx > currentStageIndex;

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
                        <span className="text-xs font-semibold block capitalize">
                          {stage.id}
                        </span>
                        <span className="text-[11px] leading-tight block text-slate-400 mt-0.5">
                          {stage.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <div className="text-xs text-slate-500">
                {jobStatus?.created_at && (
                  <span>Started: {new Date(jobStatus.created_at).toLocaleTimeString()}</span>
                )}
              </div>

              {isJobCompleted && (
                <Link href={`/results?job=${encodeURIComponent(activeJobId)}`}>
                  <Button size="lg" className="shadow-lg shadow-blue-600/20">
                    <span>Go to Results</span>
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </Link>
              )}

              {isJobFailed && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setActiveJobId(null);
                    revalidate();
                  }}
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  Try Again
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        /* SECTION 2: Pre-execution Validation Rules Table */
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-blue-400" />
                    Compatibility Rules Validation
                  </CardTitle>
                  <CardDescription className="mt-0.5">
                    Evaluates scientific compatibility rules (units, polarization, band, orbit, geometry, valid pixels).
                  </CardDescription>
                </div>

                {isValidating ? (
                  <Badge variant="outline">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    Validating...
                  </Badge>
                ) : isCompatible ? (
                  <Badge variant="success">COMPATIBLE</Badge>
                ) : (
                  <Badge variant="destructive">INCOMPATIBLE</Badge>
                )}
              </div>
            </CardHeader>

            <CardContent className="flex flex-col gap-4">
              {/* Validation Status Banner */}
              {isValidating ? (
                <div className="space-y-2 py-4">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : validationError ? (
                <Alert variant="destructive">
                  <AlertTriangle className="w-4 h-4" />
                  <AlertTitle>Validation Service Error</AlertTitle>
                  <AlertDescription className="text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-1">
                    <span>Failed to validate observation pair against server.</span>
                    <Button type="button" size="sm" variant="outline" onClick={() => revalidate()}>
                      <RotateCcw className="w-3.5 h-3.5 mr-1" />
                      Retry
                    </Button>
                  </AlertDescription>
                </Alert>
              ) : (
                <>
                  {isCompatible ? (
                    <Alert variant="success">
                      <CheckCircle2 className="w-4 h-4" />
                      <AlertTitle>Pair is Compatible</AlertTitle>
                      <AlertDescription className="text-xs">
                        All mandatory compatibility checks passed. Calibrated radar backscatter difference can be executed.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert variant="destructive">
                      <XCircle className="w-4 h-4" />
                      <AlertTitle>Pair Incompatibility Detected</AlertTitle>
                      <AlertDescription className="text-xs">
                        One or more critical compatibility checks failed. Analysis execution is blocked to maintain scientific validity.
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Rules Table */}
                  <div className="border border-slate-800 rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10 text-center">Status</TableHead>
                          <TableHead className="w-32">Rule ID</TableHead>
                          <TableHead className="w-24">Severity</TableHead>
                          <TableHead>Check Description & Message</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {validationData?.rules?.map((rule) => {
                          const isPassed = rule.passed;
                          const isWarning = rule.severity === "warning";

                          return (
                            <TableRow key={rule.id}>
                              <TableCell className="text-center">
                                {isPassed ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400 inline-block" />
                                ) : isWarning ? (
                                  <AlertTriangle className="w-4 h-4 text-amber-400 inline-block" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-red-400 inline-block" />
                                )}
                              </TableCell>
                              <TableCell className="font-mono text-xs font-semibold text-slate-200">
                                {rule.id}
                              </TableCell>
                              <TableCell>
                                {isWarning ? (
                                  <Badge variant="warning" className="text-[10px]">
                                    WARNING
                                  </Badge>
                                ) : (
                                  <Badge variant="destructive" className="text-[10px]">
                                    ERROR
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell className="text-xs text-slate-300">
                                {rule.message}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}

              {/* Run Analysis Action Button (FR-08: disabled if incompatible or AOI missing) */}
              <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="text-xs text-slate-500">
                  <span>Backend will re-validate inputs upon job dispatch.</span>
                </div>

                <Button
                  size="lg"
                  disabled={!isCompatible || !aoi || isValidating || createJobMutation.isPending}
                  onClick={() => createJobMutation.mutate()}
                  className="shadow-lg shadow-blue-600/20"
                >
                  {createJobMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Dispatching Job...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2 fill-current" />
                      Run Analysis
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
          <Skeleton className="h-12 w-64 mb-6" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <AnalysisContent />
    </Suspense>
  );
}
