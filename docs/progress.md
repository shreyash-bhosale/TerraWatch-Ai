# TerraWatch AI — Progress Tracking

## Milestone Gate Status

| Milestone | Status | Verification Command / Evidence | Notes |
| --- | --- | --- | --- |
| M1: Foundation | VERIFIED | `make setup`, `curl /api/health` (200 OK), `test_health.py` | Monorepo, Makefile, FastAPI + Next.js skeletons, `.env.example`, health check |
| M2: Contracts + Fixtures | VERIFIED | `make fixtures` (SHA256 identical twice), `make types` | Pydantic schemas, deterministic synthetic GeoTIFFs + JSONs, `api-types.ts` |
| M3: Parallel Lanes A, B, C | VERIFIED | `make test` (50 pytest passed, 13 Vitest passed) | Processing pipeline, Providers & JobManager, 5-page Next.js frontend |
| M4: Integration | VERIFIED | `cd frontend && npm run test:e2e`, `docs/evidence/m4_workflow_result.png` | Full workflow in real Chrome via Playwright (`browser` subagent blocked by missing `DevToolsActivePort`) |
| M5: Hardening | VERIFIED | `npm run test:e2e` (1280px, 820px, 390px), `test_providers.py`, `test_job_fails_on_corrupt_raster` | Path traversal guards, failed-job API test, 3-width responsive E2E pass |
| M6: Deploy | PARTIAL | `make build`, `backend/Dockerfile`, `frontend/vercel.json`, `README.md`, app bundle grep | Local build & bundle secret check VERIFIED; remote cloud URL deployment PLANNED |
| M7: Resource Readiness | VERIFIED | Grep check on `nisar-integration-checklist.md`, `nisar-metadata-mapping.md`, `nisar_provider.py` | Questions-only checklist & empty mapping template; zero invented NISAR facts |

## Functional Requirements Status

| Area / Item | Status | Verification Command / Evidence | Notes |
| --- | --- | --- | --- |
| FR-01: Dashboard | VERIFIED | `tests/dashboard.test.tsx`, `e2e/workflow.spec.ts` | Title, demo banner, health status, Start analysis CTA, recent jobs |
| FR-02: Explore Map & AOI Draw | VERIFIED | `tests/explore.test.tsx`, `e2e/workflow.spec.ts` | MapLibre + terra-draw modes, Use demo area, Clear button |
| FR-03: AOI Validation | VERIFIED | `tests/geo.test.ts`, `tests/api/test_observations.py` | Client + server Shapely validation, self-intersection & area limits |
| FR-04: AOI Metrics | VERIFIED | `tests/geo.test.ts`, `tests/explore.test.tsx` | Bbox, centroid, spherical area calculation |
| FR-05: Observations Listing | VERIFIED | `tests/observations.test.tsx`, `tests/api/test_observations.py` | Missing metadata renders "Not provided", synthetic badge |
| FR-06: Observation Pair Selection | VERIFIED | `tests/observations.test.tsx`, `e2e/workflow.spec.ts` | Exactly 2 selected, auto chronological order, 3rd selection hint |
| FR-07: Analysis Validation API | VERIFIED | `tests/api/test_validation.py`, `tests/processing/test_validation.py` | All Section 8.3 rules tested individually |
| FR-08: Run Analysis UI Gate | VERIFIED | `tests/analysis.test.tsx`, `tests/api/test_analysis_jobs.py` | Disabled when incompatible; server rejects 422 `INCOMPATIBLE_OBSERVATIONS` |
| FR-09: Analysis Job Creation | VERIFIED | `tests/api/test_analysis_jobs.py` | Returns HTTP 202 `queued`, atomic JSON write to `data/jobs/` |
| FR-10: Analysis Progress Polling | VERIFIED | `tests/analysis.test.tsx`, `e2e/workflow.spec.ts` | 2s polling, discrete stage progression, zero percentages |
| FR-11: Processing Execution | VERIFIED | `tests/processing/test_pipeline.py`, `test_corrupt_raster.py` | Pure scientific pipeline; corrupt raster -> `failed` + cleanup |
| FR-12: Results Page & Map Overlay | VERIFIED | `tests/results.test.tsx`, `docs/evidence/m4_workflow_result.png` | PNG overlay, Before/After/Diff toggle, diverging legend, limitations |
| FR-13: Results API | VERIFIED | `tests/api/test_analysis_jobs.py` | Returns 409 when running/failed, 404 when missing, 200 when completed |
| FR-14: Export Artifacts | VERIFIED | `tests/processing/test_export.py` | LZW GeoTIFF re-read verified, stats/metadata JSONs, 3 PNG overlays |
| FR-15: Provider Selection | VERIFIED | `tests/api/test_providers.py` | `PROVIDER` env selects `mock`/`local`; `nisar` blocked; unknown rejected |
| FR-16: Health Endpoint | VERIFIED | `tests/api/test_health.py` | Real checks for `data_dir` writable and `fixtures` present |
| FR-17: Local Provider | VERIFIED | `tests/api/test_providers.py` | Path traversal blocked; missing sidecars skip with warning |
| FR-18: Deterministic Result Summary | VERIFIED | `tests/results.test.tsx`, `e2e/workflow.spec.ts` | Template summary built strictly from statistics |
| FR-19: Responsive Layout | VERIFIED | `npm run test:e2e` (1280x800, 820x1024, 390x844) | All 3 viewport widths complete full workflow |
| FR-20: GeoJSON Summary of Changes | PLANNED | Optional (RECOMMENDED) | Deferred beyond Phase A core workflow |
| FR-21: Real NISAR Provider | BLOCKED | `tests/api/test_providers.py` | Documented stub raising `NotImplementedError("BLOCKED: awaiting official NISAR resources")` |

## Recorded Verification Outputs

- **Backend & Frontend Unit/Integration Tests (`make test`):**
  - `pytest backend/tests -v`: `50 passed, 5 warnings in 0.75s`
  - `vitest run`: `6 test files passed, 13 tests passed in 712ms`
- **Playwright E2E (`cd frontend && npm run test:e2e`):**
  - `3 passed (8.1s)` across `desktop (1280x800)`, `tablet (820x1024)`, and `mobile (390x844)`
- **Production Build & Secret Scan (`make build`):**
  - Next.js 14.2.18 compiled and prerendered 9/9 routes cleanly; grep for secret keys in `frontend/.next/static/chunks/app/` returned 0 matches.
- **M7 NISAR Fact Audit:**
  - `grep -rnE "https?://|/science/|/LSAR/|/SSAR/|\.h5"` on M7 docs and `nisar_provider.py` returned 0 matches.

## Audit Remediation Log

### Group 1 — Validation Single Source of Truth (`F-07`, `F-08`) — VERIFIED
- **Pre-fix failing tests (`pytest backend/tests/processing/test_validation.py -v` before fix):**
  - `2 failed, 12 passed in 0.28s`: `test_v_valid_under_one_percent_fails` (`TypeError: validate_compatibility() got an unexpected keyword argument 'before_raster'`) and `test_validation_single_source_of_truth` (`AssertionError` because `app.services.validator` still duplicated `validate_compatibility`).
- **Post-fix verification:**
  - `make test`: `60 passed, 5 warnings in 0.65s` (pytest, including all 11 rule tests `V-SAME-ID`..`V-VALID`, `V-POL`/`V-ORBIT` warning cases, `test_identical_dimensions_alone_do_not_pass_validation`, and `test_validation_single_source_of_truth`) and `6 test files passed, 13 tests passed in 622ms` (Vitest).
  - `make build`: Next.js 14.2.18 built `9/9` routes cleanly.
  - `cd frontend && npm run test:e2e`: `3 passed (7.2s)` across `1280x800`, `820x1024`, and `390x844`.

### Group 2 — API Hardening (`F-09`) — VERIFIED
- **Pre-fix failing tests (`pytest backend/tests/api/test_health.py backend/tests/api/test_api_hardening.py --tb=no` before fix):**
  - `8 failed, 2 passed, 1 warning in 0.22s` (`test_health_503_when_fixtures_absent`, `test_malformed_json_returns_error_envelope`, `test_wrong_field_type_returns_validation_details`, `test_oversize_request_body_returns_413_envelope`, `test_unknown_route_returns_error_envelope`, `test_unhandled_exception_returns_500_without_stacktrace`, `test_provider_not_implemented_maps_to_503_everywhere`, `test_path_traversal_and_absolute_paths_safe_envelope`).
- **Post-fix verification:**
  - `pytest backend/tests/api/test_health.py backend/tests/api/test_api_hardening.py -v`: `10 passed, 3 warnings in 0.24s`.
  - `make test`: `69 passed, 7 warnings in 0.67s` (pytest) and `6 test files passed, 13 tests passed in 885ms` (Vitest).
  - `make build`: Next.js 14.2.18 built `9/9` routes cleanly.
  - `cd frontend && npm run test:e2e`: `3 passed (9.5s)` across `1280x800`, `820x1024`, and `390x844`.

### Group 3 — Frontend Fixes (`F-02` to `F-06`) — VERIFIED
- **Pre-fix failing tests (`cd frontend && npm test` before fixes):**
  - `4 test files failed | 4 passed (8)`, `7 tests failed | 12 passed (19)` (`navbar.test.tsx`, `analysis.test.tsx` F-03/F-04, `dashboard.test.tsx` F-06, `map_components.test.tsx` F-05/F-06).
- **Post-fix verification:**
  - `make test`: `69 passed` (pytest) and `8 test files passed (8), 19 tests passed (19)` (Vitest).
  - `cd frontend && npm run build`: Next.js 14.2.18 built `9/9` routes cleanly.
  - `cd frontend && npm run test:e2e`: `3 passed (9.6s)` across `1280x800`, `820x1024`, and `390x844` (including 390px `scrollWidth === clientWidth`, keyboard mobile nav, MapLibre `custom-aoi-source` geometry equality check, `/analysis?job=<id>` load, and Dashboard Study Area + Recent Analyses live status).
  - Real-Chrome backend-stop test (`f04_polling_error.png`): killing `uvicorn` mid-run showed `Polling Connection Error` + `Retry` while keeping `RUNNING` visible; restarting backend + clicking `Retry` resumed polling and reached `COMPLETED`.
  - Mobile width verification at 390px: `{"sw":390,"cw":390}` (`docs/evidence/fixes/f02_mobile_390px.png`).
  - Explore MapLibre `style.load` fix (`f05_demo_aoi_map.png`): `{"hasSource":true,"hasFill":true,"hasOutline":true}`.

### Group 4 — Documentation & Lint (`F-01` & Lint Gap) — VERIFIED
- Created `docs/architecture.md`, `docs/api-contracts.md`, and `docs/processing-method.md` directly from inspected source modules and regenerated `backend/openapi.json` / `frontend/lib/api-types.ts` via `make types`.
- Added `frontend/.eslintrc.json` (`next/core-web-vitals`) and pinned `eslint@8.57.1` + `eslint-config-next@14.2.18`:
  - `cd frontend && npm run lint`: `✔ No ESLint warnings or errors`.
- Docker build and deployed URL: NOT VERIFIED, run on a machine with Docker.

---

## Post-reaudit fixes

| Finding | Status | Proof |
| --- | --- | --- |
| **F-05** (`results/page.tsx` `statusError` Retry & last-known state) | **VERIFIED** | Commit `a74b076`. Pre-fix: `vitest run tests/results.test.tsx` (`1 failed \| 4 passed`, missing `Retry`) and Playwright `e2e/results-retry.spec.ts` (`1 failed`, `getByRole('button', { name: /retry/i })` not found). Post-fix: `results.test.tsx` (`5/5` pass including status-refresh preservation test), `npm run lint` (`✔ No ESLint warnings or errors`), `make test` (`69 passed` pytest; `8 files / 20 tests passed` Vitest), `make build` (`9/9` routes), and `cd frontend && npm run test:e2e` (`4 passed (8.9s)` including real backend stop/restart recovery). |
| **F-11** (Unused `sonner`, `DEMO_BBOX`, unused imports/exports) | **VERIFIED** | Commit `ac684bd`. Uninstalled `sonner`, removed `DEMO_BBOX`, removed `clearRecentJobs`, and cleaned all unused locals/imports. Pre-fix `tsc --noEmit --noUnusedLocals` (`12 errors in 3 files`) and Python AST scan (`8` files with unused imports) -> Post-fix grep for `sonner\|DEMO_BBOX\|clearRecentJobs` (`0` matches in `frontend/` and `backend/`), `tsc --noUnusedLocals` (`0` errors), Python AST (`PYTHON_AST_CLEAN`), `npm run lint` (`✔ No ESLint warnings or errors`), `make test` (`69 passed` pytest; `8 files / 20 tests passed` Vitest), `make build` (`9/9` routes), `npm run test:e2e` (`4 passed (8.8s)`). |
| **F-10** (`SyntheticBanner` gating on `health.synthetic_mode` & `job.synthetic`) | **VERIFIED** | Commit `ba5ad3e`. Pre-fix `vitest run tests/synthetic_banner.test.tsx` (`1 failed \| 2 passed`, banner rendered when `synthetic_mode=false`) -> Post-fix `synthetic_banner.test.tsx` (`3/3` pass), `npm run lint` (`✔ No ESLint warnings or errors`), `make test` (`69 passed` pytest; `9 files / 23 tests passed` Vitest), `make build` (`9/9` routes), `npm run test:e2e` (`4 passed (11.2s)`). |

### Deferred

- **F-12** (**PARTIAL** / Deferred): Requires `M`-effort edits to scientific processing and validation modules (`pipeline.py`, `export.py`, `validation.py`), excluded by the `S`-effort and non-scientific boundary.
- **F-13** (**PARTIAL** / Deferred): Extracting `components/{observations,analysis,results}/` exceeds `S`-effort refactoring across working pages, and the extra root prompt file is the active user-opened prompt document.
- **F-14** (**PARTIAL** / Deferred): Requires `M`-effort test harness refactoring (`explore.test.tsx` unmocking and provider test restructuring), deferred per the `S`-effort threshold.
- **Docker / Remote Deployment** (**PARTIAL**): Intentionally untouched per scope (`Docker build and deployed URL: NOT VERIFIED, run on a machine with Docker`).

