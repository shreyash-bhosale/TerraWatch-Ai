# TerraWatch AI — Independent Read-Only Re-Audit Report (`F-01` to `F-09` & PRD Section 15)

**Re-Audit Date:** 2026-11-12  
**Audit Mode:** Strictly read-only (no source files modified; report written to `docs/reaudit-report.md`)  
**Scope:** Verification of MAJOR findings `F-01` through `F-09` from `docs/audit-report.md`, regression check, and `PRD.md` Section 15 Definition of Done at `HEAD` (`8606440`).

---

## 1. Executive Summary

- **8 of 9 findings (`F-01`, `F-02`, `F-03`, `F-04`, `F-06`, `F-07`, `F-08`, `F-09`) are `VERIFIED FIXED`.**
- **1 finding (`F-05`) is `STILL OPEN` (Partial):** `/analysis` polling network error (`jobError`) + `Retry` + preserved last status and `validationError` + `Retry` are **VERIFIED FIXED**, **but** `/results?job=<id>` `statusError` (`frontend/app/results/page.tsx:36-48, 111-133`) still lacks a `Retry` button (`resultsStatusErrorHasRetry: false`, observed in live Chrome check).
- **Regressions Observed:** **None** in functional workflow, scientific outputs, lint, unit/integration tests, production build, or 3-viewport Playwright E2E. *(One contract doc change noted: `PRD.md:132` added `INVALID_REQUEST` to Section 6 error codes in `ed02ffe` per remediation Group 2 guidance.)*

### Command Verification Runs (Executed Live on Clean Working Tree at `8606440`)

| Command | Result | Exact Summary |
| --- | --- | --- |
| `make test` (pytest) | **PASS** | `69 passed, 7 warnings in 0.84s` |
| `make test` (Vitest) | **PASS** | `Test Files  8 passed (8)` / `Tests  19 passed (19)` |
| `cd frontend && npm run lint` | **PASS** | `✔ No ESLint warnings or errors` |
| `make build` | **PASS** | `Next.js 14.2.18` compiled cleanly (`9/9` static routes) |
| `cd frontend && npm run test:e2e` | **PASS** | `3 passed (9.6s)` across `desktop (1280x800)`, `tablet (820x1024)`, `mobile (390x844)` |
| `GET /api/health` (live) | **PASS** | HTTP `200`, `{"status":"ok","version":"0.1.0","provider":"mock","synthetic_mode":true,"checks":{"data_dir":true,"fixtures":true}}` |
| OpenAPI & `api-types.ts` sync | **PASS** | `OPENAPI_MATCH: True`, `API_TYPES_MATCH: True` |
| Fixtures idempotency | **PASS** | `FIXTURES_IDEMPOTENT: True COUNT: 10` |
| `.next` secret scan + NISAR refs | **PASS** | `0` secret matches in `frontend/.next/static/chunks/app/`; `0` invented NISAR URLs/HDF5 paths |

---

## 2. Re-Audit Status of Findings `F-01` to `F-09`

| ID | Status | Evidence & Verification Details |
| --- | --- | --- |
| **F-01** | **VERIFIED FIXED** | `docs/architecture.md` (113 lines, Mermaid diagrams match codebase), `docs/api-contracts.md` (86 lines matching `openapi.json`), and `docs/processing-method.md` (66 lines matching `backend/app/processing/`) exist and accurately describe the implementation. `frontend/.eslintrc.json` (`{"extends": "next/core-web-vitals"}`) and pinned `eslint@8.57.1` / `eslint-config-next@14.2.18` allow `cd frontend && npm run lint` to pass non-interactively (`✔ No ESLint warnings or errors`). |
| **F-02** | **VERIFIED FIXED** | `frontend/app/dashboard/page.tsx:211-394` implements the `Study Area Summary` card (empty state `"No study area selected."` verified; populated state `"5 vertices"` / `48.02 km²` verified) and hydrates `Recent Analyses` saved job IDs via live `GET /api/analysis/{job_id}` calls (`jobApiCallCount: 1`, live `COMPLETED` badge). Jobs API failure shows `"Unable to Refresh Recent Jobs"` Alert with `Retry` (`jobsErrorAlertVisible: true`, `jobsErrorRetryVisible: true`) and recovers on retry. Using client-side `localStorage` job IDs + `GET /api/analysis/{job_id}` rather than a 9th list endpoint is logged in `docs/decisions.md:12` per R10. |
| **F-03** | **VERIFIED FIXED** | `frontend/components/Navbar.tsx:31-106` collapses desktop nav links on `< md` (`768px`) into a keyboard-operable menu button (`aria-expanded`, `Enter` open, `Escape` close). Live Chrome at `390x844` confirmed zero horizontal document overflow across all five routes (`/dashboard`, `/explore`, `/observations`, `/analysis`, `/results` all measured `scrollWidth: 390, clientWidth: 390, overflow: false`) and keyboard navigation (`menuOpenedKeyboard: true`, `menuClosedEscape: true`). Vitest `navbar.test.tsx` (1/1) and Playwright mobile (`390x844`) pass. |
| **F-04** | **VERIFIED FIXED** | `frontend/app/analysis/page.tsx:156-175` checks `if (!activeJobId && (!beforeId || !afterId))` before showing `"No Observations Selected"` and reads `jobStatus?.before_id` / `jobStatus?.after_id`. Live Chrome verified `/analysis?job=job_c031162b9545` loads `Job job_c031162b9545`, `syn_before`, `syn_after`, and `COMPLETED` (`jobOnlyLoaded: true`, `jobOnlyNoObsHidden: true`), while bare `/analysis` shows `"No Observations Selected"` (`bareAnalysisShowsNoObs: true`). Vitest `analysis.test.tsx` and Playwright E2E pass. |
| **F-05** | **STILL OPEN** *(Partial)* | **Fixed parts:** In `frontend/app/analysis/page.tsx:120-141, 278-300, 451-462`, `validationError` shows `"Validation Service Error"` + `Retry` (`valRetryVisible: true` -> recovers to `Pair is Compatible`) and polling `jobError` pauses polling, keeps `RUNNING` / `Reading` visible (`lastStateStillShown: true`), renders `"Polling Connection Error"` + `Retry` (`pollRetryVisible: true`), and resumes cleanly to `COMPLETED` on click. **Open gap:** In `frontend/app/results/page.tsx:36-48, 111-133`, `statusError` (failure of `GET /api/analysis/{job_id}` on Results page) still renders only `"Return to Dashboard"` with **no `Retry` button** (`resultsStatusErrorVisible: true`, `resultsStatusErrorHasRetry: false`, `resultsStatusErrorReturnDash: true`; `refetch` is wired only on `resultsError` at lines 54 and 194, not on the status query). |
| **F-06** | **VERIFIED FIXED** | (1) `frontend/components/map/AoiDrawMap.tsx:145-156, 268-299` listens for `style.load` and synchronizes `initialAoi` via `useEffect`. In live Chrome on `/explore`, clicking the **header** `"Use demo area"` button draws `custom-aoi-source` (`hasSource: true`, `hasFillLayer: true`, `hasOutlineLayer: true`, `attrMatchesSource: true`, `firstCoord: [73.8, 18.496]`) on the MapLibre canvas, and clicking the **header** `"Clear"` button removes it (`sourceExistsAfterClear: false`, `attrAfterClear: null`). (2) Blocking `tile.openstreetmap.org/**` in live Chrome renders `"Map Style Load Failed"` Alert + `Retry` on both `AoiDrawMap` (`exploreStyleErrVisible: true`, `exploreStyleRetryVisible: true`) and `ResultsMap` (`resultsStyleErrVisible: true`, `resultsStyleRetryVisible: true`). Vitest `map_components.test.tsx` (2/2) and Playwright E2E pass. |
| **F-07** | **VERIFIED FIXED** | `backend/tests/processing/test_validation.py:13-217` covers all 11 compatibility rules individually (`V-SAME-ID`, `V-ORDER` equal dates, `V-UNITS`, `V-POL` mismatch + missing warning, `V-BAND`, `V-ORBIT` mismatch + missing warning, `V-LEVEL`, `V-CRS`, `V-GRID`, `V-AOI`, `V-VALID` `< 1%`) plus `test_identical_dimensions_alone_do_not_pass_validation`. `backend/tests/api/test_health.py:22-44` verifies `GET /api/health` returns `503` when `DATA_DIR` is unwritable/missing or fixtures are absent. All 69 backend pytest tests pass. |
| **F-08** | **VERIFIED FIXED** | `backend/app/processing/validation.py:99-453` is the sole `validate_compatibility` implementation, called by `backend/app/api/analysis.py:23,109,199`, `backend/app/services/job_manager.py:20,121`, and `backend/app/processing/pipeline.py:14,111`. Duplicate `validate_compatibility` was deleted from `backend/app/services/validator.py` (enforced by `test_validation_single_source_of_truth`). `_evaluate_valid_pixel_fraction` (`validation.py:46-96`) performs real AOI-window slicing + nodata masking and fails when `< 1%` valid pixels remain (`test_v_valid_under_one_percent_fails`). *(Decision to defer unreadable/corrupt TIFF exceptions during sync validation to the async job worker is logged in `docs/decisions.md:10`.)* |
| **F-09** | **VERIFIED FIXED** | `backend/app/main.py:29-114` registers `enforce_max_body_size` HTTP middleware (`MAX_BODY_BYTES = 1_048_576`, returning `413 INVALID_REQUEST`), `RequestValidationError` (`422 INVALID_REQUEST` with field errors in `details`), `StarletteHTTPException` (`ErrorEnvelope`), and unhandled `Exception` (`500 INTERNAL_ERROR`, no stack trace). `NotImplementedError` maps to `503 PROVIDER_NOT_AVAILABLE` across `/api/observations*`, `/api/analysis/validate`, and `/api/analysis` (`observations.py`, `analysis.py:51-55, 75-79, 98-102, 140-144, 164-168, 187-191`). Traversal handlers return `403 INVALID_REQUEST` without exposing internal paths. Proven by `backend/tests/api/test_api_hardening.py` (7/7 tests passing). *(Note: `PRD.md:132` was updated in `ed02ffe` to include `INVALID_REQUEST` in Section 6 error codes, logged in `docs/decisions.md:11`.)* |

---

## 3. Regressions Check

- **Functional & Test Regressions:** None detected. All 69 pytest tests, 19 Vitest tests across 8 files, `next lint`, `next build` (9/9 routes), and 3 Playwright E2E viewports (`1280x800`, `820x1024`, `390x844`) pass after commit `8606440`.
- **Minor Observation on Fixed UI (non-blocking):** On `/explore`, when `AoiDrawMap` displays the `"Map Style Load Failed"` Alert (`z-20`, `AoiDrawMap.tsx:412`), it partially overlaps the top floating `DRAW AOI` toolbar (`z-10`). On `/dashboard` at `390px`, the Recent Analyses `Table` stays inside its card via `overflow-auto` so page `scrollWidth === 390`, requiring horizontal scroll inside the table wrapper to inspect columns past `Status`.

---

## 4. PRD Section 15 — Definition of Done Re-Evaluation

| Section 15 Item | Status | Re-Audit Evidence |
| --- | --- | --- |
| `make setup`, `make dev`, `make test`, `make build` all succeed | **PARTIAL** *(Re-audit safety)* | Live backend + production frontend started cleanly (`/api/health` 200, `/dashboard` 200), `make test` (69 backend + 19 frontend) and `make build` (9/9 routes) passed in this re-audit. `make setup` was **not** re-run in this read-only re-audit to avoid mutating dependencies/lockfiles (previously exit `0` in initial audit). |
| Five pages work; map loads; AOI select/clear/invalid handled | **VERIFIED** | Verified across all 3 Playwright E2E viewports (`3 passed (9.6s)`) + live Chrome header `Use demo area`/`Clear` sync + MapLibre style-error Retry + `390px` zero-overflow nav. |
| Mock and local providers work; switching needs only an env change | **VERIFIED** | Live `PROVIDER=mock` verified (`GET /api/health`, `/api/observations*`, E2E); `PROVIDER` switching (`mock` \| `local` \| `nisar`) and `LocalProvider` path safety verified by `test_providers.py` and `test_api_hardening.py`. |
| Compatibility rules tested individually; incompatible pairs cannot run | **VERIFIED** | All 11 rules `V-SAME-ID`..`V-VALID` + warning cases + identical-dimensions rejection tested individually in `backend/tests/processing/test_validation.py` (`14/14` pass) and `backend/tests/api/test_validation.py` (`7/7` pass); API rejects incompatible jobs with `422 INCOMPATIBLE_OBSERVATIONS`. |
| Synthetic stats equal `expected_stats.json`; nodata handled; GeoTIFF re-reads correctly | **VERIFIED** | Re-read live job `job_c031162b9545` outputs: `difference.tif` shape `(64, 64)`, `EPSG:4326`, `nodata=-9999.0`, `32` nodata px, `400` px at `-7.0`, `3664` px at `0.0`; `statistics.json` `valid_pixel_count=4064, invalid_pixel_count=32, total_pixel_count=4096, mean=-0.6889764070510864, median=0.0, min=-7.0, max=0.0, std=2.0852208137512207`; `difference.png` RGBA `(64, 64, 4)` with `32` transparent (`alpha=0`) pixels. |
| Job status is real; failed-job path tested | **PARTIAL** *(because of `F-05`)* | Atomic `data/jobs/<id>.json` (`os.replace`), corrupt-raster failure tests, and `/analysis` polling error Retry (`lastStateStillShown: true`, `pollRetryVisible: true`) pass; only `/results` `statusError` lacks a `Retry` button (`frontend/app/results/page.tsx:111-133`). |
| Results map, legend, stats, limitations, synthetic banner visible | **VERIFIED** | Verified on live job `job_c031162b9545` (`Difference`/`Before`/`After` layers, symmetric `[-7.00, 7.00] dB` scale from `metadata.color_scales`, `4,064` valid / `32` nodata stats, `4` limitations lines, `"DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS"` banner & badge). |
| Playwright E2E passes | **VERIFIED** | `cd frontend && npm run test:e2e` -> `3 passed (9.6s)` (`desktop 1280x800`, `tablet 820x1024`, `mobile 390x844`). |
| Deployed workflow verified; no secrets exposed | **PARTIAL** | `.env` git-ignored (`.gitignore:2:.env`), `0` secret hits in `frontend/.next/static/chunks/app/`; Docker image build and remote deployed URL remain **NOT VERIFIED** locally (no Docker daemon / deployed URL). |
| README and the four docs files complete; NISAR stub documented and BLOCKED | **VERIFIED** | `README.md`, `docs/architecture.md`, `docs/api-contracts.md`, `docs/processing-method.md`, `docs/nisar-integration-checklist.md`, `docs/nisar-metadata-mapping.md`, `docs/progress.md`, and `docs/decisions.md` exist; `backend/app/providers/nisar_provider.py` raises `NotImplementedError("BLOCKED: awaiting official NISAR resources")` and is unregistered (`test_providers.py`, `test_api_hardening.py`); `0` invented NISAR URLs/HDF5 paths. |
| No dead buttons, fake metrics, unused dependencies or dead code | **PARTIAL** *(Minor `F-11` untouched)* | Zero dead buttons, zero fake percentages (`\d+%` asserted absent in E2E), dead duplicate validator removed (`F-08`). Intentionally untouched Minor item `F-11`: unused `sonner` (`1.5.0`) in `frontend/package.json` and unused `DEMO_BBOX` import in `AoiDrawMap.tsx:7`. |

---

## 5. Remaining Actionable Gap (From Re-Audit Scope)

1. **`F-05` (`frontend/app/results/page.tsx:36-48, 111-133`):** Destructure `refetch: refetchStatus` on the `analysis-status-for-results` query and add a `Retry` `<Button onClick={() => refetchStatus()}>` inside the `statusError` Alert alongside `"Return to Dashboard"`.

