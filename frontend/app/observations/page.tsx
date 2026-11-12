"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient, type Observation } from "@/lib/api";
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
  Database,
  Calendar,
  AlertTriangle,
  RefreshCw,
  Check,
  MapPin,
  Clock,
  Info,
} from "lucide-react";

export default function ObservationsPage() {
  const router = useRouter();
  const [aoi, setAoi] = useState<GeoJSONPolygonGeometry | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectionHint, setSelectionHint] = useState<string | null>(null);

  // Load AOI from session storage
  useEffect(() => {
    const stored = getStoredAOI();
    if (stored) {
      setAoi(stored);
    }
  }, []);

  // Fetch observations intersecting AOI
  const {
    data: searchResponse,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["observations-search", aoi],
    queryFn: () => {
      if (!aoi) throw new Error("No AOI provided");
      return apiClient.searchObservations({ aoi });
    },
    enabled: !!aoi,
  });

  const observations = useMemo(() => {
    return searchResponse?.observations || [];
  }, [searchResponse]);

  // Determine chronological order for selected observations
  const { beforeObs, afterObs } = useMemo(() => {
    if (selectedIds.length === 0) return { beforeObs: null, afterObs: null };

    const selectedList = selectedIds
      .map((id) => observations.find((o) => o.id === id))
      .filter((o): o is Observation => !!o);

    if (selectedList.length === 1) {
      return { beforeObs: selectedList[0], afterObs: null };
    }

    if (selectedList.length >= 2) {
      const [obs1, obs2] = selectedList;
      const date1 = new Date(obs1.acquisition_date).getTime();
      const date2 = new Date(obs2.acquisition_date).getTime();

      if (date1 <= date2) {
        return { beforeObs: obs1, afterObs: obs2 };
      } else {
        return { beforeObs: obs2, afterObs: obs1 };
      }
    }

    return { beforeObs: null, afterObs: null };
  }, [selectedIds, observations]);

  // Toggle selection
  const handleToggleSelect = (obsId: string) => {
    setSelectionHint(null);

    if (selectedIds.includes(obsId)) {
      // Deselect
      setSelectedIds(selectedIds.filter((id) => id !== obsId));
    } else {
      if (selectedIds.length >= 2) {
        // Enforce FR-06: Third selection does not overwrite; show hint banner
        setSelectionHint("You can only select two observations. Deselect one first.");
      } else {
        setSelectedIds([...selectedIds, obsId]);
      }
    }
  };

  const handleProceed = () => {
    if (beforeObs && afterObs) {
      router.push(
        `/analysis?before=${encodeURIComponent(beforeObs.id)}&after=${encodeURIComponent(
          afterObs.id
        )}`
      );
    }
  };

  if (!aoi) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center flex flex-col items-center gap-4">
        <MapPin className="w-12 h-12 text-slate-600 mb-2" />
        <h2 className="text-xl font-bold text-white">No Area of Interest Selected</h2>
        <p className="text-slate-400 text-sm max-w-md">
          To search and list SAR radar observations, please define or select an Area of Interest first.
        </p>
        <Link href="/explore">
          <Button>
            <span>Go to Explore</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-blue-400 border-blue-500/30">
              Step 2 of 4
            </Badge>
            <span className="text-xs text-slate-400">Pair Selection</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Observation Catalog
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl">
            Select exactly two radar observations covering your study area to perform change analysis.
            Chronological ordering is assigned automatically.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
          <Link href="/explore">
            <Button variant="outline" size="sm" className="text-xs">
              Change AOI
            </Button>
          </Link>
        </div>
      </div>

      {/* Third Selection Hint Alert (FR-06) */}
      {selectionHint && (
        <Alert variant="warning" className="animate-in fade-in">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>Selection limit reached</AlertTitle>
          <AlertDescription>{selectionHint}</AlertDescription>
        </Alert>
      )}

      {/* Warnings Banner if returned by provider */}
      {searchResponse?.warnings && searchResponse.warnings.length > 0 && (
        <Alert variant="warning">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>Catalog Warnings</AlertTitle>
          <AlertDescription className="text-xs space-y-1">
            {searchResponse.warnings.map((w, i) => (
              <p key={i}>• {w}</p>
            ))}
          </AlertDescription>
        </Alert>
      )}

      {/* Selected Pair Bar */}
      <Card className="border-blue-500/30 bg-blue-950/20">
        <CardContent className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Selected Pair
              </span>
              <span className="text-sm font-medium text-white">
                {selectedIds.length} of 2 observations selected
              </span>
            </div>

            <div className="flex items-center gap-4">
              {/* Before Slot */}
              <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                  Before
                </span>
                {beforeObs ? (
                  <div className="text-xs">
                    <span className="font-mono text-white font-medium">{beforeObs.id}</span>
                    <span className="text-slate-400 ml-1.5">
                      ({new Date(beforeObs.acquisition_date).toLocaleDateString()})
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-slate-500 italic">None selected</span>
                )}
              </div>

              <span className="text-slate-600 font-bold">→</span>

              {/* After Slot */}
              <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">
                  After
                </span>
                {afterObs ? (
                  <div className="text-xs">
                    <span className="font-mono text-white font-medium">{afterObs.id}</span>
                    <span className="text-slate-400 ml-1.5">
                      ({new Date(afterObs.acquisition_date).toLocaleDateString()})
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-slate-500 italic">None selected</span>
                )}
              </div>
            </div>
          </div>

          <div>
            <Button
              type="button"
              disabled={selectedIds.length !== 2}
              onClick={handleProceed}
              className="w-full md:w-auto shadow-md shadow-blue-600/20"
            >
              <span>Proceed to Analysis</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Observations Table */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>Error querying observations</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>Failed to load radar catalog from configured provider.</span>
            <Button size="sm" variant="outline" onClick={() => refetch()} className="ml-4">
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : observations.length === 0 ? (
        <div className="text-sm text-slate-400 py-16 text-center border border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center gap-2">
          <Database className="w-10 h-10 text-slate-600 mb-1" />
          <p className="font-semibold text-slate-300">No observations found</p>
          <p className="text-xs text-slate-500 max-w-sm">
            No radar acquisitions match the selected Area of Interest. Try selecting the demo study area.
          </p>
          <Link href="/explore" className="mt-3">
            <Button size="sm" variant="outline">
              Return to Explore
            </Button>
          </Link>
        </div>
      ) : (
        <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12 text-center">Select</TableHead>
                <TableHead>Observation ID</TableHead>
                <TableHead>Acquisition Date</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Polarization</TableHead>
                <TableHead>Band</TableHead>
                <TableHead>Orbit</TableHead>
                <TableHead>Units</TableHead>
                <TableHead>Dataset</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {observations.map((obs) => {
                const isSelected = selectedIds.includes(obs.id);
                const isBefore = beforeObs?.id === obs.id;
                const isAfter = afterObs?.id === obs.id;

                return (
                  <TableRow
                    key={obs.id}
                    onClick={() => handleToggleSelect(obs.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-blue-950/40 hover:bg-blue-950/60" : ""
                    }`}
                  >
                    <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        role="checkbox"
                        aria-checked={isSelected}
                        onClick={() => handleToggleSelect(obs.id)}
                        className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-blue-600 border-blue-500 text-white"
                            : "border-slate-700 bg-slate-900 hover:border-slate-500"
                        }`}
                      >
                        {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                      </button>
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-white">
                          {obs.id}
                        </span>
                        {isBefore && (
                          <Badge variant="default" className="text-[10px] bg-blue-600">
                            BEFORE
                          </Badge>
                        )}
                        {isAfter && (
                          <Badge variant="default" className="text-[10px] bg-purple-600">
                            AFTER
                          </Badge>
                        )}
                      </div>
                    </TableCell>

                    <TableCell className="text-xs text-slate-300">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>{new Date(obs.acquisition_date).toLocaleDateString()}</span>
                        <span className="text-[11px] text-slate-500">
                          {new Date(obs.acquisition_date).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </TableCell>

                    <TableCell className="text-xs text-slate-300 font-mono">
                      {obs.provider}
                    </TableCell>

                    {/* Missing metadata shows "Not provided" (FR-05) */}
                    <TableCell className="text-xs">
                      {obs.polarization ? (
                        <span className="font-mono text-slate-200">{obs.polarization}</span>
                      ) : (
                        <span className="text-slate-500 italic">Not provided</span>
                      )}
                    </TableCell>

                    <TableCell className="text-xs">
                      {obs.frequency_band ? (
                        <span className="font-mono text-slate-200">{obs.frequency_band}-band</span>
                      ) : (
                        <span className="text-slate-500 italic">Not provided</span>
                      )}
                    </TableCell>

                    <TableCell className="text-xs">
                      {obs.orbit_direction ? (
                        <span className="capitalize text-slate-200">{obs.orbit_direction}</span>
                      ) : (
                        <span className="text-slate-500 italic">Not provided</span>
                      )}
                    </TableCell>

                    <TableCell className="text-xs">
                      {obs.measurement_units ? (
                        <span className="font-mono text-slate-200">{obs.measurement_units}</span>
                      ) : (
                        <span className="text-slate-500 italic">Not provided</span>
                      )}
                    </TableCell>

                    <TableCell>
                      {obs.synthetic ? (
                        <Badge variant="synthetic">SYNTHETIC</Badge>
                      ) : (
                        <Badge variant="secondary">REAL SAR</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
