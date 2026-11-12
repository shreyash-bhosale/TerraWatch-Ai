# TerraWatch AI

*Making Earth's changing surface easier to observe, understand, and communicate.*

**Phase A (Pre-Hackathon Foundation)** · NASA Space Apps 2026 · "Dancing with the SARs"

---

## Overview

TerraWatch AI is a provider-agnostic SAR (Synthetic Aperture Radar) surface change detection web application. Users select an Area of Interest (AOI), discover radar acquisitions from a configured provider, validate pairwise compatibility, execute calibrated dB backscatter differencing ($D = B_2 - B_1$), and inspect georeferenced overlays, valid-pixel statistics, and explicit scientific limitations.

> **Important Notice:** Phase A operates exclusively with deterministic **synthetic demo data** (`DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS`) and local GeoTIFF datasets. Real NISAR data access and product-specific rules are intentionally **BLOCKED** pending official NASA/ISRO challenge resources release.

---

## Core Workflow

`Dashboard (/dashboard)` → `Explore (/explore)` → `Observations (/observations)` → `Analysis (/analysis)` → `Results (/results)`

1. **Dashboard**: Displays API health status, active provider (`mock` / `local`), synthetic data warning banner, and recent analyses.
2. **Explore**: Interactive MapLibre map with `terra-draw` polygon/rectangle drawing, "Use demo area" preset, AOI geometry validation, bounding box, centroid, and spherical geodesic area calculation.
3. **Observations**: Searches the configured provider for intersecting observations, displays metadata (using `"Not provided"` for missing optional fields), and enforces 2-observation selection with automatic chronological ordering.
4. **Analysis**: Runs compatibility validation rules (`V-SAME-ID`, `V-ORDER`, `V-UNITS`, `V-POL`, `V-BAND`, `V-ORBIT`, `V-LEVEL`, `V-CRS`, `V-GRID`, `V-AOI`, `V-VALID`), dispatches asynchronous jobs, and polls discrete pipeline stages (`queued → validating → reading → aligning → differencing → statistics → exporting → completed/failed`) without fabricated percentages.
5. **Results**: Renders georeferenced PNG overlays on MapLibre (`Difference`, `Before`, `After`), symmetric diverging dB color scale legend, valid/invalid pixel statistics, deterministic quantitative summary, scientific limitations, and downloadable GeoTIFF/PNG/JSON exports.

---

## Local Setup & Commands

### Prerequisites
- Python 3.11+
- Node.js 18+ / npm

### Quick Start
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Install backend & frontend dependencies
make setup

# 3. Generate deterministic synthetic SAR fixtures
make fixtures

# 4. Generate TypeScript API contracts from FastAPI OpenAPI schema
make types

# 5. Run backend + frontend locally
make dev
```

Open `http://localhost:3000` in your browser. Backend API docs are available at `http://localhost:8000/docs`.

### Testing & Building
```bash
# Run all backend (pytest) and frontend (Vitest) unit/integration tests
make test

# Build frontend production bundle
make build

# Run Playwright E2E workflow across desktop, tablet, and mobile viewports
cd frontend && npm run test:e2e
```

---

## Environment Variables

Configured in `.env` (see `.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `PROVIDER` | `mock` | Active observation provider: `mock` (synthetic fixtures) or `local` (directory scan). Setting `nisar` raises `BLOCKED`. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed frontend origins. |
| `DATA_DIR` | `data` | Root directory for synthetic fixtures, job state JSONs, and exported artifacts. |
| `LOCAL_DATA_DIR` | `data/local` | Directory scanned by `LocalProvider` for `.tif` + sidecar `.json` pairs. |
| `MAX_AOI_AREA_KM2` | `50000.0` | Maximum allowed study area size in $\text{km}^2$. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Base URL for FastAPI backend consumed by Next.js client. |

---

## Deployment

### Backend (Docker)
Build and run the FastAPI processing container using `backend/Dockerfile`:
```bash
docker build -f backend/Dockerfile -t terrawatch-backend .
docker run -p 8000:8000 -e CORS_ORIGINS=https://your-frontend.vercel.app terrawatch-backend
```
The container automatically runs `backend/scripts/make_synthetic.py` on startup and exposes a health check at `GET /api/health`.

### Frontend (Vercel)
Deploy `frontend/` to Vercel using `frontend/vercel.json`:
- Root Directory: `frontend`
- Build Command: `npm run build`
- Environment Variable: `NEXT_PUBLIC_API_BASE_URL=https://your-backend-url`

---

## Scientific Scope & Known Limitations (Phase A)

- **dB Backscatter Difference Only**: Outputs represent raw calibrated backscatter difference ($D = B_2 - B_1$ in dB). No flood threshold or land-cover classification is applied.
- **Physical Ambiguity**: Backscatter differences can be caused by inundation, soil moisture changes, vegetation growth, wind roughening on water, incidence angle variation, speckle noise, or processing differences.
- **Strict Alignment Guard**: Rasters with mismatched CRS, resolution, or non-integer grid shifts fail cleanly with `ALIGNMENT_MISMATCH` rather than silently resampling across incompatible projections.
- **NISAR Integration Blocked**: `backend/app/providers/nisar_provider.py` is an intentionally unimplemented stub raising `NotImplementedError("BLOCKED: awaiting official NISAR resources")`. See `docs/nisar-integration-checklist.md` and `docs/nisar-metadata-mapping.md`.

