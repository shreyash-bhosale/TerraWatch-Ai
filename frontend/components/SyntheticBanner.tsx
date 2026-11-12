"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

export function SyntheticBanner({ show = true }: { show?: boolean }) {
  if (!show) return null;

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
