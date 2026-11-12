import { API_BASE_URL } from "./config";
import type { components } from "./api-types";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type Observation = components["schemas"]["Observation"];
export type ObservationSearchRequest = components["schemas"]["ObservationSearchRequest"];
export type ObservationSearchResponse = components["schemas"]["ObservationSearchResponse"];
export type ObservationListResponse = components["schemas"]["ObservationListResponse"];
export type ValidateRequest = components["schemas"]["ValidateRequest"];
export type ValidateResponse = components["schemas"]["ValidateResponse"];
export type JobCreateRequest = components["schemas"]["JobCreateRequest"];
export type JobCreateResponse = components["schemas"]["JobCreateResponse"];
export type JobStatusResponse = components["schemas"]["JobStatusResponse"];
export type JobResultsResponse = components["schemas"]["JobResultsResponse"];
export type RuleResult = components["schemas"]["RuleResult"];
export type Stats = components["schemas"]["Stats"];
export type GeoJSONPolygonGeometry = components["schemas"]["GeoJSONPolygonGeometry"];
export type ErrorDetail = components["schemas"]["ErrorDetail"];

export interface ApiError {
  error: ErrorDetail;
}

export function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === "object" &&
    err !== null &&
    "error" in err &&
    typeof (err as ApiError).error?.code === "string" &&
    typeof (err as ApiError).error?.message === "string"
  );
}

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: {
          code: "INTERNAL_ERROR",
          message: `HTTP error ${response.status}: ${response.statusText}`,
        },
      };
    }
    throw errorData;
  }

  return response.json();
}

export const apiClient = {
  getHealth: () => fetchApi<HealthResponse>("/api/health"),

  searchObservations: (request: ObservationSearchRequest) =>
    fetchApi<ObservationSearchResponse>("/api/observations/search", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  listObservations: (limit = 50, offset = 0) =>
    fetchApi<ObservationListResponse>(`/api/observations?limit=${limit}&offset=${offset}`),

  getObservation: (id: string) =>
    fetchApi<Observation>(`/api/observations/${encodeURIComponent(id)}`),

  validateAnalysis: (request: ValidateRequest) =>
    fetchApi<ValidateResponse>("/api/analysis/validate", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  createAnalysis: (request: JobCreateRequest) =>
    fetchApi<JobCreateResponse>("/api/analysis", {
      method: "POST",
      body: JSON.stringify(request),
    }),

  getAnalysisStatus: (jobId: string) =>
    fetchApi<JobStatusResponse>(`/api/analysis/${encodeURIComponent(jobId)}`),

  getAnalysisResults: (jobId: string) =>
    fetchApi<JobResultsResponse>(`/api/analysis/${encodeURIComponent(jobId)}/results`),
};

/**
 * Returns full URL for static assets (PNG, GeoTIFF, JSON) served from backend.
 */
export function getAssetUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export interface RecentJobRecord {
  jobId: string;
  beforeId: string;
  afterId: string;
  createdAt: string;
  synthetic: boolean;
}

const RECENT_JOBS_KEY = "terrawatch_recent_jobs";

export function getRecentJobs(): RecentJobRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_JOBS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveRecentJob(job: RecentJobRecord): void {
  if (typeof window === "undefined") return;
  try {
    const existing = getRecentJobs();
    const filtered = existing.filter((j) => j.jobId !== job.jobId);
    filtered.unshift(job);
    localStorage.setItem(RECENT_JOBS_KEY, JSON.stringify(filtered.slice(0, 10)));
  } catch {
    // ignore
  }
}
