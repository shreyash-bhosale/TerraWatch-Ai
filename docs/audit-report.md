# TerraWatch AI — Independent Phase A Code Audit Report

**Audit Date:** 2026-11-12  
**Audit Mode:** Read-only inspection & live verification against `PRD.md` and `AGENTS.md` (R1–R10)  
**Scope:** Phase A (`PROVIDER=mock` & `PROVIDER=local`; `nisar` stubbed/BLOCKED)

---

## 1. Verdict

**Phase A MAJOR findings F-01 through F-09 remediated and VERIFIED locally.**  
All 9 MAJOR findings identified in the initial read-only audit have been fixed across 4 commits (`e6b5ee5`, `ed02ffe`, `3f9179a`, `8606440`) and verified with `make fixtures` (determinism hash-identical twice), `cd frontend && npm run lint` (`No ESLint warnings or errors`), `make test` (`69 passed` pytest, `8 files / 19 tests passed` Vitest), `make build` (`9/9` Next.js routes), and `cd frontend && npm run test:e2e` (`3 passed` across `1280x800`, `820x1024`, `390x844`). Minor findings `F-10`–`F-14` were intentionally left untouched per remediation scope; Docker image build and remote deployed URL remain NOT VERIFIED in this environment without Docker.

---

## 1A. Remediation Verification Log (`F-01` to `F-09`)

*(Note: Prompt Group 3 mapped `F-02`→Navbar overflow, `F-03`→`/analysis?job=<id>`, `F-04`→Polling network-error retry, `F-05`→Demo AOI MapLibre sync, `F-06`→Map style failure retry & Dashboard summary/jobs. Both original audit IDs and Group 3 commit scopes are cross-referenced below.)*

| Audit ID | Status | Commit | Proving Verification Output |
| --- | --- | --- | --- |
| **F-01** (+ Lint) | **FIXED** | `8606440` | Created `docs/architecture.md`, `docs/api-contracts.md`, `docs/processing-method.md` from inspected modules & `openapi.json`; added `.eslintrc.json` + pinned ESLint; `npm run lint` -> `✔ No ESLint warnings or errors`. |
| **F-02** (Dashboard) | **FIXED** | `3f9179a` | Added Study Area Summary + live `GET /api/analysis/{job_id}` job status hydration + error Retry in `dashboard/page.tsx`; `dashboard.test.tsx` (2/2 pass), `e2e` (`3 passed`), `f06_dashboard_live.png`. |
| **F-03** (Navbar) | **FIXED** | `3f9179a` | Added keyboard-operable `<md` mobile menu toggle (`Escape` close); `navbar.test.tsx` (1/1 pass); Playwright at `390px` verified `scrollWidth === clientWidth` (`{"sw":390,"cw":390}`, `f02_mobile_390px.png`). |
| **F-04** (`/analysis?job=`) | **FIXED** | `3f9179a` | `analysis/page.tsx` supports `?job=<id>` alone; `analysis.test.tsx` (`loads by job ID alone without before/after params`) and `e2e` (`3 passed`) pass. |
| **F-05** (Polling Retry) | **FIXED** | `3f9179a` | Pauses polling on error cleanly with Alert + Retry preserving last status; `analysis.test.tsx` (F-04 test) pass; real Chrome mid-run `uvicorn` kill & restart resumed to `COMPLETED` (`f04_polling_error.png`). |
| **F-06** (Map Sync & Style Retry) | **FIXED** | `3f9179a` | `AoiDrawMap.tsx` syncs `initialAoi` via `style.load` + `useEffect` (`custom-aoi-source` equals `DEMO_AOI`, `f05_demo_aoi_map.png`); `AoiDrawMap` & `ResultsMap` render `Alert + Retry` on `error`; `map_components.test.tsx` (2/2 pass). |
| **F-07** (Rule & Health Tests) | **FIXED** | `e6b5ee5`, `ed02ffe` | `test_validation.py` tests all 11 rules `V-SAME-ID`..`V-VALID` + warning cases + identical-dimensions failure; `test_health.py` tests 503 missing/unwritable `DATA_DIR` and absent fixtures (`69 passed`). |
| **F-08** (`validation.py` SSoT) | **FIXED** | `e6b5ee5` | Consolidated compatibility rules into `backend/app/processing/validation.py` with real `< 1%` `V-VALID` check; removed duplicate in `services/validator.py`; pre-fix `2 failed, 12 passed` -> post-fix `14 passed`. |
| **F-09** (API Hardening) | **FIXED** | `ed02ffe` | Registered `RequestValidationError`, `StarletteHTTPException`, and unhandled `Exception` `ErrorEnvelope` handlers, `MAX_BODY_BYTES` 413 middleware, `NotImplementedError` -> `503 PROVIDER_NOT_AVAILABLE` everywhere, and path-safe traversal envelopes; pre-fix `8 failed, 2 passed` -> post-fix `10 passed`. |

---

## 2. Functional Requirements Table (`FR-01` to `FR-21`)

| ID | Status | Evidence & Notes |
| --- | --- | --- |
| **FR-01** | **PARTIAL** | `frontend/app/dashboard/page.tsx:29-247` renders title, description, `"Start analysis"` link, health card, and `SyntheticBanner`; verified `GET /api/health` 200 and `01_dashboard.png`. **Gaps:** study-area summary (`DASHBOARD_HAS_STUDY_AREA_SUMMARY: false`) is missing; recent analyses read browser `localStorage` (`getRecentJobs()`) rather than `data/jobs` via API, with no jobs API failure+retry state. |
| **FR-02** | **PARTIAL** | `frontend/components/map/AoiDrawMap.tsx` initializes MapLibre GL (`terra-draw` polygon/rectangle/select modes) and map-bar `"Use demo area"` / `"Clear"` controls. **Gaps:** No `map.on("error")` Alert with retry on style load failure; header `"Use demo area"` (`explore/page.tsx:101`) updates AOI Metrics (`48.02 km²`) without drawing the polygon on MapLibre (`02_explore_demo.png`). |
| **FR-03** | **VERIFIED** | Client validation in `frontend/lib/geo.ts:134-248` (`4/4` `geo.test.ts` pass). Server validation in `backend/app/services/validator.py:26-73` (`Shapely is_valid`, `<= 500` vertices, `pyproj.Geod` `<= MAX_AOI_AREA_KM2`): live `POST /api/observations/search` returned HTTP 422 `INVALID_GEOMETRY` for bowtie and oversized polygons. *(Minor caveat: malformed Pydantic payload returns FastAPI `{"detail":...}` rather than `ErrorEnvelope`.)* |
| **FR-04** | **VERIFIED** | `frontend/app/explore/page.tsx:168-212` displays Surface Area (`48.02 km²`), Vertices (`5`), Centroid (`73.8320°, 18.5280°`), Bounding Box (`[73.800°, 18.496°, 73.864°, 18.560°]`) via `frontend/lib/geo.ts:36-106`, hidden when no AOI (`02_explore_demo.png`). *(Note: uses spherical line-integral `R=6371.0088 km`, whereas backend uses WGS84 `pyproj.Geod`.)* |
| **FR-05** | **VERIFIED** | `frontend/app/observations/page.tsx:301-426` displays id, date, provider, polarization, band, orbit, units, synthetic badge, with `"Not provided"` fallback (`observations.test.tsx` pass); empty & provider error+retry states present (`OBS_ERR: true HAS_RETRY: true`). |
| **FR-06** | **VERIFIED** | `frontend/app/observations/page.tsx:69-110`: selecting `syn_after` then `syn_before` auto-assigns `syn_before` (`Before`) and `syn_after` (`After`), and clicking a 3rd observation (`syn_misaligned`) displays `"You can only select two observations. Deselect one first."` without overwriting (`OBS_3RD_HINT_VISIBLE: true`, `03_observations_selected.png`). |
| **FR-07** | **PARTIAL** | `backend/app/services/validator.py:76-440` implements all 11 rules `V-SAME-ID`..`V-VALID` (`POST /api/analysis/validate` returns 200 with per-rule results and 404 `OBSERVATION_NOT_FOUND`). **Gap:** `test_validation.py` only tests failure for `V-SAME-ID`, `V-UNITS`, `V-GRID` (8 of 11 rules lack individual failure/warning tests); dead duplicate `backend/app/processing/validation.py:219` fakes `V-VALID`. |
| **FR-08** | **VERIFIED** | `frontend/app/analysis/page.tsx:508` disables `Run Analysis` when incompatible (`ANALYSIS_INCOMPAT_RUN_DISABLED: true`, `04_analysis_incompatible.png`, `analysis.test.tsx`); `backend/app/api/analysis.py:144-161` re-validates and rejects with HTTP 422 `INCOMPATIBLE_OBSERVATIONS`. |
| **FR-09** | **VERIFIED** | `POST /api/analysis` returns HTTP 202 `{"job_id": ..., "status": "queued"}` (`test_create_and_run_analysis_job` pass); invalid pair returns 422 and creates no job file (`test_create_job_incompatible_rejected`). |
| **FR-10** | **PARTIAL** | `frontend/app/analysis/page.tsx:118-136` polls every `2000ms` and stops on terminal state (`POLLS_AT_COMPLETE: 1 POLLS_AFTER_4_5S: 1 STOPPED: true`), showing discrete stages without percentages (`05_analysis_completed.png`). **Gaps:** `jobError` (`line 120`) is ignored on network failure (`ANALYSIS_POLL_NETFAIL_SHOWN: false`, stuck showing `RUNNING` in `09_netfail_analysis_poll.png`); `validationError` lacks retry; `/analysis?job=<id>` without `before`/`after` shows `"No Observations Selected"` (`DIRECT_ANALYSIS_JOB_QUERY_HAS_NO_OBS_BUG: true`). |
| **FR-11** | **VERIFIED** | `backend/app/processing/pipeline.py:14-119` runs stages sequentially and cleans up outputs on exception; `test_job_fails_on_corrupt_raster` and `test_pipeline_atomic_cleanup_on_corrupt_raster` pass. |
| **FR-12** | **PARTIAL** | `frontend/app/results/page.tsx` renders MapLibre PNG overlay (`Difference`, `Before`, `After` toggle verified), symmetric diverging legend from `metadata.color_scales`, stats, source IDs, limitations, synthetic badge (`06_results_desktop_1280.png`). **Gap:** `statusError` on network failure (`results/page.tsx:111-133`) lacks a Retry button (`RESULTS_NETFAIL: true HAS_RETRY: false`). |
| **FR-13** | **VERIFIED** | `GET /api/analysis/{id}/results` returns 200 when completed, 409 `JOB_NOT_COMPLETED` when running/queued/failed, and 404 `JOB_NOT_FOUND` / `RESULT_NOT_FOUND` (`test_analysis_jobs.py` + live API calls). |
| **FR-14** | **VERIFIED** | Exported GeoTIFF, `statistics.json`, `metadata.json`, and 3 RGBA PNGs verified via `test_export.py` and live rasterio re-read of `difference.tif` (`shape=(64,64)`, `CRS=EPSG:4326`, `nodata=-9999.0`, `32` nodata, `400` at `-7.0`, `3664` at `0.0`). *(Minor: `before`/`after` PNGs use `viridis` rather than single-hue ramp.)* |
| **FR-15** | **VERIFIED** | `backend/app/config.py:42-50` rejects unknown `PROVIDER` at startup; `backend/app/providers/registry.py:17-26` switches `mock`/`local` by env and raises `NotImplementedError("BLOCKED: awaiting official NISAR resources")` on `nisar` (`test_providers.py` pass). |
| **FR-16** | **PARTIAL** | Live `GET /api/health` returned HTTP 200 `{"status":"ok","version":"0.1.0","provider":"mock","synthetic_mode":true,"checks":{"data_dir":true,"fixtures":true}}`; `main.py:65-66` returns 503 when `data_dir` check fails. **Gap:** 503 failure path has no automated test (`test_health.py` tests 200 only). |
| **FR-17** | **VERIFIED** | `backend/app/providers/local_provider.py:29-147` scans `LOCAL_DATA_DIR`, emits warnings for missing/invalid sidecars, and blocks path traversal (`test_providers.py` pass). *(Minor: traversal `asset_location` inside a sidecar raises `PermissionError` aborting `_scan()` instead of warning/skipping.)* |
| **FR-18** | **VERIFIED** | `frontend/app/results/page.tsx:219-227, 282` renders `"Mean difference -0.69 dB over 4,064 valid pixels..."` deterministically from `statistics.json` (`results.test.tsx`, `workflow.spec.ts` pass). |
| **FR-19** | **PARTIAL** | Desktop (`1280x800`) and tablet (`820x1024`) pass with zero horizontal overflow (`scrollW === clientW`); **Gap:** mobile (`390x844`) overflows horizontally (`scrollW: 747`, `navOverflow: true` in `07_results_390.png`) due to non-wrapping navbar links. |
| **FR-20** | **MISSING** *(RECOMMENDED/Optional)* | Optional GeoJSON changed-area bounding polygons not implemented (allowed by PRD: "build only if Milestones 1–6 are green"). |
| **FR-21** | **BLOCKED** | `backend/app/providers/nisar_provider.py:21-46` is a documented stub raising `NotImplementedError("BLOCKED: awaiting official NISAR resources")` and is never registered (`test_nisar_provider_stub_raises_blocked`, `test_registry_nisar_raises_blocked`). |

---

## 3. Findings Table (Sorted by Severity)

| ID | Severity | Location | PRD Ref | Problem | Recommended Fix | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| **F-01** | **MAJOR** | `docs/` (missing files) | Sec. 12 (M7), Sec. 15 | Three mandatory Phase A docs (`docs/architecture.md`, `docs/api-contracts.md`, `docs/processing-method.md`) do not exist; only `decisions.md`, `progress.md`, `nisar-integration-checklist.md`, `nisar-metadata-mapping.md` are present. | Author concise `architecture.md`, `api-contracts.md`, and `processing-method.md` reflecting the verified implementation. | M |
| **F-02** | **MAJOR** | `frontend/app/dashboard/page.tsx:41-45, 162-244` | FR-01 | Dashboard lacks study-area summary (or empty state), reads Recent Analyses from browser `localStorage` instead of `data/jobs`, and has no jobs API error+retry state. *(Note PRD Sec. 4/6 omits a `GET /api/analysis` list endpoint.)* | Add Study Area summary card on Dashboard; either document `localStorage` decision per R10 or add a scoped read-only jobs listing if permitted in Phase B. | M |
| **F-03** | **MAJOR** | `frontend/components/Navbar.tsx:21-55` | FR-19, Sec. 10 | At `390x844` mobile width, the top `<header>` overflows to `747px` (`navOverflow: true`, visible in `07_results_390.png`) because all 5 nav links + brand badge sit in a single `flex` row without wrapping. | Make `Navbar` wrap cleanly on `< 640px` (`flex-wrap`, compact icon/text spacing, or mobile menu). | S |
| **F-04** | **MAJOR** | `frontend/app/analysis/page.tsx:151-167` | FR-10, Sec. 2 | Direct link `/analysis?job=<id>` (linked from `results/page.tsx:146`) fails with `"No Observations Selected"` because line 151 checks `if (!beforeId || !afterId)` before handling `activeJobId`. | Change guard to `if (!activeJobId && (!beforeId || !afterId))` and display `jobStatus.before_id`/`after_id` when `activeJobId` is set. | S |
| **F-05** | **MAJOR** | `frontend/app/analysis/page.tsx:120, 419-426`; `frontend/app/results/page.tsx:111-133` | FR-10, Sec. 10 | Job polling network failure leaves `/analysis` stuck on `RUNNING` / `Queued` with no error or retry (`jobError` & `refetchJob` unused, `09_netfail_analysis_poll.png`). `validationError` and Results `statusError` also lack `Retry` buttons. | Render `Alert` + `Retry` for `jobError` (`refetchJob()`), `validationError` (`revalidate()`), and network-level `statusError`. | S |
| **F-06** | **MAJOR** | `frontend/components/map/AoiDrawMap.tsx:37-178`; `ResultsMap.tsx:132`; `explore/page.tsx:97-118` | FR-02 | (1) Clicking header `"Use demo area"` or `"Clear"` updates metrics without drawing/clearing the MapLibre polygon (`02_explore_demo.png`) because `AoiDrawMap` reads `initialAoi` only on mount. (2) Neither map shows an Alert with Retry on MapLibre style load errors. | Sync `initialAoi` prop via `useEffect` in `AoiDrawMap` and render an Alert + Retry button on `map.on("error")` style/tile failures. | M |
| **F-07** | **MAJOR** | `backend/tests/api/test_validation.py`; `test_health.py` | FR-07, FR-16, Sec. 10 | 8 of 11 compatibility rules (`V-ORDER` equal dates, `V-POL`, `V-BAND`, `V-ORBIT`, `V-LEVEL`, `V-CRS`, `V-AOI`, `V-VALID`) have no individual failure/warning tests; `GET /api/health` 503 failure path is untested. | Add unit/API tests covering failure & warning cases for all 11 `V-*` rules and 503 health check with unwritable `DATA_DIR`. | M |
| **F-08** | **MAJOR** | `backend/app/processing/validation.py:8-236` | R8, Sec. 8.1, 8.3 | Duplicate `validate_compatibility` exists in `processing/validation.py` (never called by API/pipeline; tested only by `tests/processing/test_validation.py`), and line 219 fakes `V-VALID` as `passed=aoi_pass` without checking raster pixels. | Consolidate compatibility validation into a single module with real pixel validation and remove dead duplicate. | S |
| **F-09** | **MAJOR** | `backend/app/main.py`; `observations.py:135`; `analysis.py:48-55, 229` | Sec. 6, Sec. 10 | (1) Malformed request JSON/Pydantic types return FastAPI `{"detail":[...]}` instead of `{error:{code,message,details}}`. (2) No request body size limit middleware (`NO_BODY_SIZE_LIMIT`). (3) Traversal handlers emit `"FORBIDDEN"` (not in Sec. 6 code list); `analysis.py:48` catches `NotImplementedError` as `502 PROVIDER_ERROR` instead of `503 PROVIDER_NOT_AVAILABLE`. | Register global `RequestValidationError`/`HTTPException` handlers returning `ErrorEnvelope`, add body size limit middleware, and catch `NotImplementedError` cleanly in `analysis.py`. | S |
| **F-10** | **MINOR** | `frontend/app/layout.tsx:21`; `SyntheticBanner.tsx` | R3, Step 5 | `<SyntheticBanner />` renders unconditionally in `RootLayout` (`show = true`), so it would still warn even if `PROVIDER=local` were used with non-synthetic (`synthetic: false`) data. | Gate `SyntheticBanner` on `/api/health` `synthetic_mode` and result-level `synthetic` flags. | S |
| **F-11** | **MINOR** | `frontend/package.json:22`; `AoiDrawMap.tsx:7`; `frontend/` | R9, Sec. 2 | Unused `sonner` (`1.5.0`) dependency in `package.json`; unused `DEMO_BBOX` import in `AoiDrawMap.tsx:7`; `npm run lint` stalls prompting for ESLint setup (no `.eslintrc.json`); `_parse_iso_date` duplicated in `mock_provider.py` & `local_provider.py`; `ruff` configured in `pyproject.toml` but absent from `requirements.txt`. | Remove unused `sonner` / `DEMO_BBOX`, commit `.eslintrc.json`, extract shared date parser helper. | S |
| **F-12** | **MINOR** | `pipeline.py:48-63`; `export.py:137-149`; `validator.py:403-417` | Sec. 8.2, 8.3 | `pipeline.py` reads full raster before cropping instead of passing `window` to `reader.read()`; `export.py` uses multi-hue `viridis` for `before`/`after` instead of single-hue ramp; `validator.py` `V-VALID` assumes WGS84 raster CRS and swallows exceptions (`except Exception: valid_pixels_ok = True`); `analysis/page.tsx:478` renders red `ERROR` severity badges on passing rows. | Pass window into `GeoTIFFReader.read`, switch `before`/`after` to single-hue ramp (e.g. `gray`), handle non-4326 CRS in `V-VALID`, and clarify rule badge styling. | M |
| **F-13** | **MINOR** | `frontend/components/`; repo root | Sec. 10, 12 | `components/{observations,analysis,results}/` subdirectories from Sec. 10 do not exist (UI lives in `app/*/page.tsx`); initial prompt file `TerraWatch AI — Antigravity Master Prompt & PRD.md` remains alongside `PRD.md` at repo root. | Extract page subcomponents only if complexity grows; archive or remove duplicate root prompt copy. | S |
| **F-14** | **MINOR** | `frontend/tests/explore.test.tsx:10-14`; `test_providers.py:79-83` | Sec. 10 | `explore.test.tsx` mocks `AoiDrawMap` reactively (masking F-06); `dashboard.test.tsx` lacks populated/error tests; `test_providers.py:80` sends 4 segments to `/files/outputs/..%2F..%2Fetc/passwd` (triggers router 404 before handler traversal check). | Unmock/sync `AoiDrawMap` in tests, add populated/error Dashboard tests, and assert single-segment traversal paths hit handler 403/404. | M |

---

## 4. Definition of Done Checklist (PRD Section 15)

- [x] `make setup`, `make dev`, `make test`, `make build` all succeed — **VERIFIED** (`make setup` exit 0; `make dev` started uvicorn + Next.js with `/api/health` 200 and `/dashboard` 200; `make test` `50 passed` backend + `13 passed` frontend; `make build` compiled 9/9 Next.js routes).
- [ ] Five pages work; map loads; AOI select/clear/invalid handled — **PARTIAL** (works end-to-end via map-bar controls, but header `"Use demo area"` fails to draw on MapLibre (`F-06`), MapLibre lacks style-error retry (`F-06`), `/analysis?job=<id>` breaks without `before`/`after` (`F-04`), and mobile navbar overflows (`F-03`)).
- [x] Mock and local providers work; switching needs only an env change — **VERIFIED** (`PROVIDER=mock` verified live; `LocalProvider` + `registry.py` verified by `test_providers.py` and source inspection).
- [ ] Compatibility rules tested individually; incompatible pairs cannot run — **PARTIAL** (server rejects incompatible pairs with 422 `INCOMPATIBLE_OBSERVATIONS` and `Run Analysis` disables cleanly, **but** 8 of 11 rules lack individual failure/warning tests (`F-07`)).
- [x] Synthetic stats equal `expected_stats.json`; nodata handled; GeoTIFF re-reads correctly — **VERIFIED** (`total=4096`, `invalid=32`, `valid=4064`, `mean=-0.6889764`, `median=0.0`, `min=-7.0`, `max=0.0`, `std=2.0852208`; GeoTIFF re-read confirmed shape `(64, 64)`, `EPSG:4326`, `-9999.0` nodata, `400` pixels at `-7.0`; `difference.png` nodata alpha `0`).
- [ ] Job status is real; failed-job path tested — **PARTIAL** (atomic `os.replace` job persistence survived backend restart HTTP 200 and corrupt-raster test yields `failed`, **but** frontend ignores polling network failure (`F-05`)).
- [x] Results map, legend, stats, limitations, synthetic banner visible — **VERIFIED** (`06_results_desktop_1280.png` shows crisp non-black difference overlay, symmetric `[-7.00, 7.00] dB` scale from metadata, exact stats, limitations, source IDs, and synthetic badge/banner).
- [x] Playwright E2E passes — **VERIFIED** (`cd frontend && npm run test:e2e` -> `3 passed (9.3s)` at `1280x800`, `820x1024`, `390x844`).
- [ ] Deployed workflow verified; no secrets exposed — **PARTIAL** (`frontend/.next/static/chunks/app/` and git history secret scans returned 0 secrets, `.env` is git-ignored, `backend/Dockerfile` & `frontend/vercel.json` exist; live Docker build & remote deployed URL could not be verified locally).
- [ ] README and the four docs files complete; NISAR stub documented and BLOCKED — **PARTIAL** (`README.md`, `nisar_provider.py`, `nisar-integration-checklist.md`, `nisar-metadata-mapping.md`, `progress.md`, `decisions.md` verified with 0 invented NISAR URLs/HDF5 paths; **missing** `docs/architecture.md`, `docs/api-contracts.md`, `docs/processing-method.md` (`F-01`)).
- [ ] No dead buttons, fake metrics, unused dependencies or dead code — **PARTIAL** (0 dead buttons, 0 fake metrics/percentages, 0 flood thresholds; **but** unused `sonner` dependency (`F-11`), dead `backend/app/processing/validation.py` (`F-08`), unused `DEMO_BBOX` / `jobError`, and unconfigured `npm run lint` (`F-11`)).

---

## 5. Could Not Verify

1. **Docker image build & container startup (`backend/Dockerfile`):** `docker not found` in this environment (`Step 10`).
2. **Remote deployed Vercel + cloud backend URL (`PRD Section 12 M6`):** No live remote deployment URL was provided or reachable (`Step 10`).
3. **Antigravity Chrome DevTools MCP interactive browser session (`Step 8`):** `browser` subagent failed with `ENOENT: no such file or directory, open '.../Google/Chrome/DevToolsActivePort'`. Verified Step 8 instead via headless Google Chrome through Playwright (`task-573` + network-failure script), saving 10 evidence screenshots under `docs/evidence/audit/`.
4. **Frontend ESLint pass (`npm run lint`):** Next.js `npm run lint` prompted interactively (`? How would you like to configure ESLint?`) because `.eslintrc.json` is absent.
5. **Interactive pointer polygon drawing via TerraDraw canvas click-drag:** Verified TerraDraw initialization and `Use demo area` / `Clear` / `Select/Edit` toolbar modes, while manual freehand canvas polygon drawing was not scripted.

---

## 6. Top 5 Fixes to Do First (In Order)

1. **Create the missing PRD documentation files (`F-01`):** Add `docs/architecture.md`, `docs/api-contracts.md`, and `docs/processing-method.md` (and commit `.eslintrc.json` so `npm run lint` runs non-interactively).
2. **Fix broken Analysis/Results link & network-failure Retry states (`F-04`, `F-05`):** Allow `/analysis?job=<id>` without `before`/`after` params and render visible Retry alerts for `jobError` (polling failure), `validationError`, and Results `statusError`.
3. **Fix Mobile `390px` Navbar Overflow (`F-03`):** Make `frontend/components/Navbar.tsx` responsive at `390px` so horizontal scroll (`747px -> 390px`) is eliminated.
4. **Sync Explore Header Controls & Map Error Retry (`F-06`):** Sync `AoiDrawMap` when `initialAoi` changes so header `"Use demo area"` / `"Clear"` match the canvas, and add map style error Alert + Retry.
5. **Remove Dead Validation Duplicate, Complete Compatibility/Health Tests, & Harden Error Envelopes (`F-07`, `F-08`, `F-09`):** Eliminate unused `processing/validation.py`, add tests for all 11 `V-*` rules and 503 health check, add FastAPI validation/HTTP error-envelope handlers and body-size limit, and address `FR-01` Dashboard study-area summary (`F-02`).

---

## Appendix: Audit Evidence Summary

- **Step 1 (Inventory):** Root matches PRD layout with additions (`backend/app/processing/raster_data.py`, `backend/app/services/{validator,job_manager}.py`, root prompt file `TerraWatch AI — Antigravity Master Prompt & PRD.md`) and missing items (`docs/{architecture,api-contracts,processing-method}.md`, `frontend/components/{observations,analysis,results}/`).
- **Step 2 (Commands):**
  - `make setup`: exit `0`.
  - `make fixtures` x2 + `shasum -a 256 data/synthetic/*`: `HASH_IDENTICAL` (`diff -u` empty across all 10 files).
  - `make test`: pytest `50 passed, 5 warnings in 0.76s`; Vitest `6 passed, 13 passed in 885ms`.
  - `make build`: Next.js `14.2.18` compiled `9/9` routes cleanly.
  - `make dev` + `curl /api/health`: HTTP `200`, `FRONTEND_HTTP:200`.
- **Step 3 (Rule Compliance):** 0 hits for auth/ORM/Redis/Celery/LLMs/extra map providers/flood thresholds/invented NISAR URLs or HDF5 paths; `openapi.json` matches `app.openapi()` (`OPENAPI_MATCHES: True`) and `api-types.ts` matches `openapi-typescript` output (`API_TYPES_IDENTICAL`).
- **Step 5 & 7 (Honesty & Security):** `git check-ignore -v .env` matched; `CORS` returns `Access-Control-Allow-Origin: http://localhost:3000` only for allowed origins; git history & built `app/` bundle secret scans returned 0 hits; job `job_8f1914c0f569` returned HTTP `200` on status & results after restarting `uvicorn`.
- **Audit Screenshots (`docs/evidence/audit/`):** `01_dashboard.png`, `02_explore_demo.png`, `03_observations_selected.png`, `04_analysis_incompatible.png`, `05_analysis_completed.png`, `06_results_desktop_1280.png`, `07_results_820.png`, `07_results_390.png`, `08_netfail_dashboard.png`, `09_netfail_analysis_poll.png`.
