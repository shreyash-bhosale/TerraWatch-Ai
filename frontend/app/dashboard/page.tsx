"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  apiClient,
  getRecentJobs,
  isApiError,
  type JobStatusResponse,
  type RecentJobRecord,
} from "@/lib/api";
import {
  getStoredAOI,
  validateAOI,
  type AOIValidationResult,
  type GeoJSONPolygonGeometry,
} from "@/lib/geo";
import {
  ArrowRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Clock,
  Layers,
  Database,
  Calendar,
  MapPin,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function DashboardPage() {
  const {
    data: health,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
  });

  const [recentJobs, setRecentJobs] = useState<RecentJobRecord[]>([]);
  const [storedAoi, setStoredAoi] = useState<GeoJSONPolygonGeometry | null>(null);
  const [aoiMetrics, setAoiMetrics] = useState<AOIValidationResult | null>(null);

  useEffect(() => {
    setRecentJobs(getRecentJobs());
    const saved = getStoredAOI();
    if (saved) {
      setStoredAoi(saved);
      setAoiMetrics(validateAOI(saved));
    }
  }, []);

  const jobIds = recentJobs.map((j) => j.jobId);
  const {
    data: liveJobs,
    isLoading: isLoadingJobs,
    error: jobsError,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ["recent-jobs-status", jobIds],
    enabled: jobIds.length > 0,
    retry: false,
    queryFn: async () => {
      const results = await Promise.all(
        recentJobs.map(async (record) => {
          try {
            const live: JobStatusResponse = await apiClient.getAnalysisStatus(record.jobId);
            return { record, live, notFound: false };
          } catch (err) {
            if (isApiError(err) && err.error.code === "JOB_NOT_FOUND") {
              return { record, live: null, notFound: true };
            }
            throw err;
          }
        })
      );
      return results;
    },
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-8">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-semibold text-blue-400">
              SAR Change Detection Pipeline
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Surface Change Detection
          </h1>
          <p className="text-slate-400 mt-1 max-w-2xl text-sm sm:text-base">
            Provider-agnostic SAR backscatter comparison engine. Track physical surface changes
            using calibrated radar backscatter differencing.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/explore">
            <Button size="lg" className="shadow-lg shadow-blue-600/20">
              <span>Start analysis</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-1 md:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  health ? "bg-emerald-500 animate-pulse" : error ? "bg-red-500" : "bg-blue-500 animate-pulse"
                }`}
              />
              API & System Health
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`} />
              <span>{isFetching ? "Checking..." : "Refresh"}</span>
            </Button>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 text-slate-400 text-sm py-4">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
              <span>Checking backend connection...</span>
            </div>
          ) : error ? (
            <Alert variant="destructive">
              <XCircle className="w-4 h-4" />
              <AlertTitle>Backend unavailable</AlertTitle>
              <AlertDescription className="mt-1">
                Could not reach the FastAPI server. Ensure the backend service is running.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
                <span className="text-xs text-slate-500 block">Status</span>
                <span className="text-sm font-semibold text-emerald-400 flex items-center gap-1 mt-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {health?.status.toUpperCase()}
                </span>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
                <span className="text-xs text-slate-500 block">Version</span>
                <span className="text-sm font-mono text-slate-200 mt-1 block">
                  v{health?.version}
                </span>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
                <span className="text-xs text-slate-500 block">Active Provider</span>
                <span className="text-sm font-medium text-slate-200 mt-1 block">
                  {health?.provider}
                </span>
              </div>
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
                <span className="text-xs text-slate-500 block">Synthetic Mode</span>
                <span className="text-sm font-medium text-amber-400 mt-1 block">
                  {health?.synthetic_mode ? "ACTIVE" : "OFF"}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Phase A Notice Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white">Phase A Pre-Hackathon</h2>
              <Badge variant="synthetic">DEMO</Badge>
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Operating with calibrated synthetic SAR backscatter fixtures. Official NISAR reader
              is intentionally blocked awaiting official challenge resource release (Nov 13, 2026).
            </p>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
            <span>NASA Space Apps 2026</span>
            <span className="text-blue-400 font-medium">Dancing with the SARs</span>
          </div>
        </div>
      </div>

      {/* Study Area Summary (FR-01) */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-400" />
              Study Area Summary
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Active Area of Interest stored in session for radar observation searches.
            </p>
          </div>
          <Link href="/explore">
            <Button variant="outline" size="sm" className="text-xs">
              {storedAoi && aoiMetrics?.valid ? "Edit AOI" : "Select AOI"}
            </Button>
          </Link>
        </div>

        {!storedAoi || !aoiMetrics?.valid ? (
          <div className="text-sm text-slate-400 py-6 text-center border border-dashed border-slate-800 rounded-lg flex flex-col items-center gap-2">
            <p className="font-medium text-slate-300">No study area selected.</p>
            <p className="text-xs text-slate-500 max-w-md">
              Draw a bounding polygon or load the synthetic demo footprint on the Explore page to define your analysis boundary.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 block">Vertices</span>
              <span className="text-sm font-mono text-slate-200 mt-1 block">
                {storedAoi.coordinates[0].length} vertices
              </span>
            </div>
            <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 block">Approx. Area</span>
              <span className="text-sm font-mono text-slate-200 mt-1 block">
                {aoiMetrics.areaKm2?.toFixed(2)} km²
              </span>
            </div>
            <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 block">Centroid</span>
              <span className="text-xs font-mono text-slate-200 mt-1 block">
                {aoiMetrics.centroid ? `${aoiMetrics.centroid[0].toFixed(4)}, ${aoiMetrics.centroid[1].toFixed(4)}` : "—"}
              </span>
            </div>
            <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 block">Bounding Box</span>
              <span className="text-[11px] font-mono text-slate-300 mt-1 block break-all">
                {aoiMetrics.bbox ? `[${aoiMetrics.bbox.map((b) => b.toFixed(3)).join(", ")}]` : "—"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Recent Analyses (FR-01) */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Recent Analyses
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Saved job IDs hydrated with live execution status from the backend jobs API.
            </p>
          </div>
        </div>

        {jobsError && (
          <Alert variant="destructive">
            <XCircle className="w-4 h-4" />
            <AlertTitle>Unable to Refresh Recent Jobs</AlertTitle>
            <AlertDescription className="text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-1">
              <span>Failed to fetch live job status from the backend API.</span>
              <Button type="button" size="sm" variant="outline" onClick={() => refetchJobs()}>
                <RotateCcw className="w-3.5 h-3.5 mr-1" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {recentJobs.length === 0 ? (
          <div className="text-sm text-slate-400 py-10 text-center border border-dashed border-slate-800 rounded-lg flex flex-col items-center justify-center gap-2">
            <Layers className="w-8 h-8 text-slate-600 mb-1" />
            <p className="font-medium text-slate-300">No recent analyses found.</p>
            <p className="text-xs text-slate-500 max-w-sm">
              Start by selecting an Area of Interest on the Explore page, then pair two radar observations to run change detection.
            </p>
            <Link href="/explore" className="mt-2">
              <Button size="sm" variant="outline">
                Go to Explore
              </Button>
            </Link>
          </div>
        ) : (
          <div className="border border-slate-800 rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Before Observation</TableHead>
                  <TableHead>After Observation</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentJobs.map((job) => {
                  const hydrated = liveJobs?.find((entry) => entry.record.jobId === job.jobId);
                  const liveStatus = hydrated?.live?.status;
                  const displayBefore = hydrated?.live?.before_id ?? job.beforeId;
                  const displayAfter = hydrated?.live?.after_id ?? job.afterId;
                  const displaySynthetic = hydrated?.live?.synthetic ?? job.synthetic;
                  const isCompleted = liveStatus === "completed";
                  const targetHref = isCompleted
                    ? `/results?job=${encodeURIComponent(job.jobId)}`
                    : `/analysis?job=${encodeURIComponent(job.jobId)}`;

                  return (
                    <TableRow key={job.jobId}>
                      <TableCell className="font-mono text-xs text-blue-400 font-medium">
                        {job.jobId}
                      </TableCell>
                      <TableCell>
                        {isLoadingJobs ? (
                          <Badge variant="outline">CHECKING</Badge>
                        ) : liveStatus === "completed" ? (
                          <Badge variant="success">COMPLETED</Badge>
                        ) : liveStatus === "failed" ? (
                          <Badge variant="destructive">FAILED</Badge>
                        ) : liveStatus ? (
                          <Badge variant="default">{liveStatus.toUpperCase()}</Badge>
                        ) : hydrated?.notFound ? (
                          <Badge variant="outline">MISSING</Badge>
                        ) : (
                          <Badge variant="outline">UNKNOWN</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-slate-500" />
                          {displayBefore}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-slate-500" />
                          {displayAfter}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          {new Date(job.createdAt).toLocaleString()}
                        </div>
                      </TableCell>
                      <TableCell>
                        {displaySynthetic ? (
                          <Badge variant="synthetic">SYNTHETIC</Badge>
                        ) : (
                          <Badge variant="secondary">OBSERVATION</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link href={targetHref}>
                          <Button size="sm" variant="outline" className="text-xs">
                            {isCompleted ? "View Results" : "View Status"}
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
