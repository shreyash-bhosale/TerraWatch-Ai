# TerraWatch AI — System Architecture

> Reflects actual implemented Phase A codebase (`backend/app/**`, `frontend/**`, `data/`). No invented NISAR resources or unimplemented microservices are claimed.

## 1. System Overview

TerraWatch AI is a monorepo composed of a **Next.js 14 (App Router, TypeScript)** frontend and a **FastAPI (Python 3.11+)** backend backed by atomic filesystem persistence under `data/`. No external database, message broker, tile server, authentication layer, or AI/LLM service is used.

```mermaid
flowchart LR
  U["User Browser"] --> FE["Next.js Frontend<br/>MapLibre + TerraDraw + TanStack Query"]
  FE -->|"REST JSON (/api/*)"| API["FastAPI API<br/>CORS + MAX_BODY_BYTES + ErrorEnvelope handlers"]
  API --> REG["Provider Registry<br/>get_provider() via PROVIDER env"]
  REG --> MP["MockProvider<br/>(data/synthetic catalog)"]
  REG --> LP["LocalProvider<br/>(LOCAL_DATA_DIR + sidecar JSON)"]
  REG -. "BLOCKED stub (NotImplementedError -> 503)" .-> NP["NisarProvider"]
  API --> JM["JobManager<br/>ThreadPoolExecutor(max_workers=2) + atomic JSON"]
  JM --> PIPE["Processing Pipeline<br/>app.processing.pipeline"]
  PIPE --> FS[("data/ filesystem<br/>synthetic/, jobs/, outputs/")]
  API -->|"Static route /files/outputs/{job_id}/{filename}"| FS
  FE -->|"PNG overlays, GeoTIFF, metadata JSON"| API
```

## 2. Backend Module Layout

- `backend/app/main.py`: FastAPI initialization, CORS middleware (`CORS_ORIGINS`), `enforce_max_body_size` HTTP middleware (`MAX_BODY_BYTES`, default `1_048_576`), global exception handlers (`RequestValidationError`, `StarletteHTTPException`, unhandled `Exception`), and `GET /api/health`.
- `backend/app/config.py`: `Settings` (`pydantic_settings.BaseSettings`) loading environment configuration and validating `PROVIDER` on startup (`validate_provider`).
- `backend/app/schemas/`: Source-of-truth Pydantic models (`common.py`, `observation.py`, `analysis.py`) exported to `backend/openapi.json`.
- `backend/app/providers/`: Provider abstraction and catalog adapters (`base.py`, `registry.py`, `mock_provider.py`, `local_provider.py`, and blocked stub `nisar_provider.py`).
- `backend/app/services/`:
  - `validator.py`: AOI geometry validation (`validate_aoi_geometry` using Shapely + PyProj `Geod` geodesic area against `MAX_AOI_AREA_KM2` and max 500 vertices).
  - `job_manager.py`: In-process `ThreadPoolExecutor(max_workers=2)` worker pool, atomic job JSON writes (`temp` + `os.replace` to `data/jobs/<job_id>.json`), compatibility gate via `app.processing.validation.validate_compatibility`, and output artifact lookup.
- `backend/app/processing/`: Pure geospatial/SAR computation engine (`readers/`, `metadata.py`, `validation.py`, `preprocessing.py`, `alignment.py`, `change_detection.py`, `statistics.py`, `export.py`, `pipeline.py`).

## 3. Provider Architecture

```mermaid
classDiagram
  class BaseProvider {
    <<abstract>>
    +search(aoi, start_date, end_date) Tuple~List~Observation~, List~str~~
    +list(limit, offset) Tuple~List~Observation~, int~
    +get(id) Observation
    +open_asset(id) Path
  }
  BaseProvider <|-- MockProvider
  BaseProvider <|-- LocalProvider
  BaseProvider <|-- NisarProvider
  class MockProvider {
    Reads data/synthetic/*.json
    All records tagged synthetic=true
  }
  class LocalProvider {
    Scans LOCAL_DATA_DIR rasters + sidecar .json
    Blocks path traversal outside LOCAL_DATA_DIR
    Logs missing/invalid sidecars as warnings
  }
  class NisarProvider {
    BLOCKED stub raising NotImplementedError
    Never registered in active provider registry
  }
```

## 4. Raster-Processing Pipeline

```mermaid
flowchart LR
  A["Open 2 GeoTIFF assets<br/>GeoTIFFReader.read()"] --> V["validate_compatibility()<br/>11 rules V-SAME-ID..V-VALID"]
  V -- fail --> VI["IncompatiblePipelineError<br/>(INCOMPATIBLE_OBSERVATIONS)"]
  V -- pass --> B["crop_to_aoi()<br/>AOI window + nodata -> NaN"]
  B --> C["align()<br/>CRS, resolution, integer grid check"]
  C -- mismatch --> E["AlignmentMismatchError<br/>(ALIGNMENT_MISMATCH)"]
  C -- aligned --> F["difference_db()<br/>D = after - before on shared valid mask"]
  F --> G["compute_stats()<br/>counts, mean, median, min, max, std"]
  G --> H["export_results()<br/>difference.tif, JSONs, colorized PNGs"]
```

## 5. User Workflow & Frontend Architecture

- Five App Router pages under `frontend/app/`:
  - `/dashboard`: API health status (`GET /api/health`), Study Area Summary (from `sessionStorage` AOI), and Recent Analyses hydrated from `localStorage` job IDs via `GET /api/analysis/{job_id}` (preserving 8 endpoints with inline error + Retry).
  - `/explore`: Interactive MapLibre GL + TerraDraw polygon/rectangle AOI selection, `"Use demo area"` action (syncing `custom-aoi-source` and fitting bounds immediately on `style.load`), client-side metrics (`lib/geo.ts`), and map style failure Alert + Retry.
  - `/observations`: Provider search (`POST /api/observations/search`), metadata table (`"Not provided"` fallback), and 2-observation selection with automatic chronological ordering.
  - `/analysis`: Supports both `?before=...&after=...` validation/submission and `?job=<id>` direct job tracking. Polls `GET /api/analysis/{job_id}` every 2s cleanly, pauses on network error with an inline Alert + Retry preserving the last known state, and stops on `completed`/`failed`.
  - `/results`: Fetches `GET /api/analysis/{job_id}/results`, renders `Before` / `After` / `Difference (dB)` layers on MapLibre (scaling power-of-two textures cleanly via canvas data URLs in `ResultsMap.tsx` with style-error Alert + Retry and direct raster fallback), displays legend range from backend `metadata.color_scales.difference`, summary stats, deterministic template summary, and scientific limitations.
- Mobile navigation collapses at `< 768px` (`md`) into a keyboard-operable toggle menu (`Escape` to close) to keep `390px` viewports overflow-free (`scrollWidth === clientWidth`).

```mermaid
flowchart TD
  S["/dashboard<br/>Health + Study Area + Recent Jobs"] --> A["/explore<br/>Draw AOI or Use demo area"]
  A --> B["/observations<br/>Search + Select 2 Observations"]
  B --> C["/analysis<br/>Validate Compatibility"]
  C -- incompatible --> B
  C -- compatible --> E["POST /api/analysis<br/>Create Queued Job"]
  E --> F["Poll GET /api/analysis/job_id (2s)<br/>or /analysis?job=id"]
  F -- network error --> R["Alert + Retry<br/>(keeps last known state)"] --> F
  F -- failed --> G["Show Job Error Code/Message + Retry"]
  F -- completed --> H["/results?job=id<br/>Map Overlays, Stats, Downloads, Limitations"]
```

## 6. Job Lifecycle & Persistence

Job records are stored atomically as JSON files (`data/jobs/<job_id>.json`) written via temp file + `os.replace`. Pipeline output artifacts live under `data/outputs/<job_id>/` and are cleaned up atomically if any processing stage raises an exception.

```mermaid
stateDiagram-v2
  [*] --> queued: POST /api/analysis (202)
  queued --> running: ThreadPoolExecutor worker starts
  running --> completed: stages validating->reading->aligning->differencing->statistics->exporting finish
  running --> failed: any error (cleanup partial outputs)
  completed --> [*]
  failed --> [*]
```
