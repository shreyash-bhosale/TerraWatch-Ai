# TerraWatch AI — API Contracts

> Generated from FastAPI routes (`backend/app/main.py`, `backend/app/api/*.py`), Pydantic models (`backend/app/schemas/*.py`), and `backend/openapi.json`.
> Frontend types in `frontend/lib/api-types.ts` are auto-generated via `make types` (`openapi-typescript ../backend/openapi.json -o ./lib/api-types.ts`).

## 1. Global Middleware & Error Envelope

- **Request Body Size Limit (`enforce_max_body_size`):** Rejects requests whose `Content-Length` or actual body exceeds `MAX_BODY_BYTES` (default `1,048,576` bytes / 1 MB) with HTTP `413`.
- **Unified Non-2xx Error Envelope:** All FastAPI `RequestValidationError` (422), `StarletteHTTPException` (404/405/etc.), custom endpoint errors, and unhandled `Exception` (500, without stack traces) return:

```json
{
  "error": {
    "code": "STRING",
    "message": "Human readable summary",
    "details": {}
  }
}
```

Documented error codes:
`INVALID_REQUEST`, `INVALID_GEOMETRY`, `OBSERVATION_NOT_FOUND`, `INCOMPATIBLE_OBSERVATIONS`, `JOB_NOT_FOUND`, `JOB_NOT_COMPLETED`, `RESULT_NOT_FOUND`, `PROVIDER_ERROR`, `PROVIDER_NOT_AVAILABLE`, `INTERNAL_ERROR`.

---

## 2. REST API Endpoints (8 Total)

### 2.1 `GET /api/health`
Returns service version, active provider, synthetic mode flag, and filesystem readiness checks (`data_dir` writable + synthetic fixtures present). Returns **200** when both `data_dir` and `fixtures` checks pass, or **503** (`status: "unhealthy"`) if either check fails. *(OpenAPI declares 200; runtime handler sets `503` dynamically on `HealthResponse`.)*

Response (`HealthResponse`):
```json
{
  "status": "ok",
  "version": "0.1.0",
  "provider": "mock",
  "synthetic_mode": true,
  "checks": { "data_dir": true, "fixtures": true }
}
```

### 2.2 `POST /api/observations/search`
Searches the configured provider for observations intersecting a GeoJSON `Polygon` AOI and optional ISO date range.
- **Request (`ObservationSearchRequest`):** `{ "aoi": GeoJSONPolygonGeometry, "start_date"?: string, "end_date"?: string }`
- **200 (`ObservationSearchResponse`):** `{ "observations": Observation[], "warnings": string[] }`
- **Errors:** `403 INVALID_REQUEST` (path traversal in local sidecar), `413 INVALID_REQUEST` (body > `MAX_BODY_BYTES`), `422 INVALID_GEOMETRY` / `422 INVALID_REQUEST` (malformed body), `502 PROVIDER_ERROR`, `503 PROVIDER_NOT_AVAILABLE` (`PROVIDER=nisar`).

### 2.3 `GET /api/observations`
Lists cataloged observations from the active provider.
- **Query Params:** `limit` (`1..200`, default `50`), `offset` (`>= 0`, default `0`)
- **200 (`ObservationListResponse`):** `{ "observations": Observation[], "total": int }`
- **Errors:** `403 INVALID_REQUEST`, `422 INVALID_REQUEST`, `502 PROVIDER_ERROR`, `503 PROVIDER_NOT_AVAILABLE`.

### 2.4 `GET /api/observations/{id}`
Fetches a single normalized `Observation` by ID.
- **200 (`Observation`):** `{ id, provider, synthetic, acquisition_date, geometry, asset_location, asset_format, product_name?, polarization?, frequency_band?, orbit_direction?, processing_level?, measurement_units?, resolution?, crs?, source_metadata? }`
- **Errors:** `403 INVALID_REQUEST` (path traversal ID), `404 OBSERVATION_NOT_FOUND`, `502 PROVIDER_ERROR`, `503 PROVIDER_NOT_AVAILABLE`.

### 2.5 `POST /api/analysis/validate`
Runs all 11 Section 8.3 compatibility rules via `app.processing.validation.validate_compatibility` and determines chronological order (`before_id`, `after_id`).
- **Request (`ValidateRequest`):** `{ "before_id": string, "after_id": string, "aoi": GeoJSONPolygonGeometry }`
- **200 (`ValidateResponse`):** `{ "compatible": boolean, "rules": [{ "id": string, "severity": "error" | "warning", "passed": boolean, "message": string }], "order": { "before_id": string, "after_id": string } }`
- **Errors:** `403 INVALID_REQUEST`, `404 OBSERVATION_NOT_FOUND`, `422 INVALID_GEOMETRY` / `422 INVALID_REQUEST`, `502 PROVIDER_ERROR`, `503 PROVIDER_NOT_AVAILABLE`.

### 2.6 `POST /api/analysis`
Re-validates AOI and compatibility rules synchronously, then enqueues a background differencing job.
- **Request (`JobCreateRequest`):** `{ "before_id": string, "after_id": string, "aoi": GeoJSONPolygonGeometry }`
- **202 Accepted (`JobCreateResponse`):** `{ "job_id": string, "status": "queued" }`
- **Errors:** `403 INVALID_REQUEST`, `404 OBSERVATION_NOT_FOUND`, `422 INVALID_GEOMETRY`, `422 INCOMPATIBLE_OBSERVATIONS`, `422 INVALID_REQUEST`, `502 PROVIDER_ERROR`, `503 PROVIDER_NOT_AVAILABLE`, `500 INTERNAL_ERROR`.

### 2.7 `GET /api/analysis/{job_id}`
Reads atomic persisted job state from `data/jobs/<job_id>.json`.
- **200 (`JobStatusResponse`):** `{ "job_id": string, "status": "queued" | "running" | "completed" | "failed", "stage": "queued" | "validating" | "reading" | "aligning" | "differencing" | "statistics" | "exporting" | "completed" | "failed", "created_at": string, "started_at"?: string, "finished_at"?: string, "before_id": string, "after_id": string, "synthetic": boolean, "error"?: { "code": string, "message": string } }`
- **Errors:** `404 JOB_NOT_FOUND`.

### 2.8 `GET /api/analysis/{job_id}/results`
Returns computed statistics, WGS84 bounds, layer PNG URLs, GeoTIFF export URL, metadata, limitations, and synthetic flag once completed.
- **200 (`JobResultsResponse`):** `{ "statistics": Stats, "bounds": [west, south, east, north], "layers": { "difference_png": string, "before_png": string, "after_png": string }, "geotiff_url": string, "metadata": object, "limitations": string[], "synthetic": boolean }`
- **Errors:** `404 JOB_NOT_FOUND`, `409 JOB_NOT_COMPLETED` (when job is `queued`, `running`, or `failed`), `404 RESULT_NOT_FOUND` (if result artifacts are missing on disk).

---

## 3. Static Output Asset Route (Non-API)

- **`GET /files/outputs/{job_id}/{filename}`** (`include_in_schema=False`): Serves `difference.tif`, `difference.png`, `before.png`, `after.png`, `statistics.json`, and `metadata.json` from `data/outputs/{job_id}/`.
- Enforces path traversal protection (`..`, `/`, `\`, and `relative_to` containment), returning `403 INVALID_REQUEST` on traversal attempts (without leaking filesystem paths) and `404 RESULT_NOT_FOUND` if the artifact does not exist.
