"use client";

import React, { Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { apiClient } from "@/lib/api";

function BannerContent() {
  return (
    <div
      role="banner"
      aria-label="Demo mode synthetic data warning"
      className="bg-amber-500/15 border-b border-amber-500/30 text-amber-300 px-4 py-2 text-xs md:text-sm font-medium flex items-center justify-center gap-2"
    >
      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" aria-hidden="true" />
      <span>
        <strong>DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS.</strong> No real-world conclusion can be drawn.
      </span>
    </div>
  );
}

function SyntheticBannerDynamic() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job");
  const isResultsPage = pathname?.startsWith("/results") ?? false;

  const {
    data: health,
    isSuccess: healthSuccess,
    isError: healthError,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
  });

  const healthExplicitlyNonSynthetic =
    healthSuccess && !healthError && health?.synthetic_mode === false;

  const {
    data: jobStatus,
    isSuccess: jobSuccess,
    isError: jobError,
  } = useQuery({
    queryKey: ["analysis-status-for-banner", jobId],
    queryFn: () => {
      if (!jobId) throw new Error("No job ID");
      return apiClient.getAnalysisStatus(jobId);
    },
    enabled: Boolean(jobId) && healthExplicitlyNonSynthetic,
    retry: false,
  });

  const jobExplicitlyNonSynthetic =
    jobSuccess && !jobError && jobStatus?.synthetic === false;

  const shouldCheckResults =
    isResultsPage &&
    Boolean(jobId) &&
    healthExplicitlyNonSynthetic &&
    jobExplicitlyNonSynthetic &&
    jobStatus?.status === "completed";

  const {
    data: jobResults,
    isSuccess: resultsSuccess,
    isError: resultsError,
  } = useQuery({
    queryKey: ["analysis-results-for-banner", jobId],
    queryFn: () => {
      if (!jobId) throw new Error("No job ID");
      return apiClient.getAnalysisResults(jobId);
    },
    enabled: shouldCheckResults,
    retry: false,
  });

  if (healthExplicitlyNonSynthetic) {
    if (isResultsPage) {
      const resultsOk =
        jobStatus?.status !== "completed" ||
        (resultsSuccess && !resultsError && jobResults?.synthetic === false);
      if (jobId && jobExplicitlyNonSynthetic && resultsOk) {
        return null;
      }
    } else if (!jobId || jobExplicitlyNonSynthetic) {
      return null;
    }
  }

  return <BannerContent />;
}

export function SyntheticBanner({ show }: { show?: boolean }) {
  if (show === true) {
    return <BannerContent />;
  }
  if (show === false) {
    return null;
  }

  return (
    <Suspense fallback={<BannerContent />}>
      <SyntheticBannerDynamic />
    </Suspense>
  );
}
