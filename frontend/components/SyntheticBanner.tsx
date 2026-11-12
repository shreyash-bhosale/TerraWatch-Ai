"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
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
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job");

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
  });

  const { data: jobStatus } = useQuery({
    queryKey: ["analysis-status-for-banner", jobId],
    queryFn: () => {
      if (!jobId) throw new Error("No job ID");
      return apiClient.getAnalysisStatus(jobId);
    },
    enabled: Boolean(jobId) && health?.synthetic_mode === false,
    retry: false,
  });

  if (!health?.synthetic_mode && !jobStatus?.synthetic) {
    return null;
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
    <Suspense fallback={null}>
      <SyntheticBannerDynamic />
    </Suspense>
  );
}
