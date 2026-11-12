import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "outline" | "destructive" | "warning" | "success" | "synthetic";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-blue-500/10 border-blue-500/30 text-blue-400",
    secondary: "bg-slate-800 border-slate-700 text-slate-300",
    outline: "border-slate-700 text-slate-300",
    destructive: "bg-red-500/10 border-red-500/30 text-red-400",
    warning: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    success: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    synthetic: "bg-amber-500/15 border-amber-500/40 text-amber-300 font-mono tracking-wide",
  }[variant];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variantStyles,
        className
      )}
      {...props}
    />
  );
}
