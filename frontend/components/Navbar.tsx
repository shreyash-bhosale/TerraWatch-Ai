"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Compass, Database, BarChart3, Layers } from "lucide-react";

const NAV_ITEMS = [
  { name: "Dashboard", href: "/dashboard", icon: Activity },
  { name: "Explore", href: "/explore", icon: Compass },
  { name: "Observations", href: "/observations", icon: Database },
  { name: "Analysis", href: "/analysis", icon: BarChart3 },
  { name: "Results", href: "/results", icon: Layers },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold text-slate-100 hover:text-white">
            <span className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center text-xs font-bold text-white">
              TW
            </span>
            <span className="tracking-tight text-base font-bold">TerraWatch AI</span>
          </Link>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
            Phase A · Synthetic
          </span>
        </div>

        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Main Navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-slate-800 text-blue-400 border border-slate-700"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

