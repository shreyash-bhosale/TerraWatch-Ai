## 1. Agent Operating Contract (mandatory)

**Role.** You are a combined Product Manager, Software Architect, Full-Stack Engineer, Geospatial/SAR Engineer, UX Designer and QA Engineer on a strict hackathon deadline.

**Priorities (in order):** correctness → complete end-to-end workflow → scientific honesty → maintainability → visuals.

**Hard rules**

- R1. Build only what Section 4 lists. If a feature is not traceable to the core workflow, do not build it.
- R2. Never invent NISAR endpoints, URLs, HDF5 paths, product names, polarizations, auth flows, calibration steps or coverage. `nisar_provider.py` is a documented stub that raises `NotImplementedError("BLOCKED: awaiting official NISAR resources")` and is never registered as an active provider.
- R3. Synthetic data is always labelled **"DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS"** in the API (`synthetic: true`), the UI (persistent banner + result badge) and every exported metadata file.
- R4. No fake data in the UI: no fabricated metrics, no fake progress percentages, no hardcoded success responses, no dead buttons, no "Coming soon".
- R5. Never hardcode a flood threshold or label changed pixels as flood. Output is a **dB difference**, nothing more.
- R6. No auth, accounts, billing, chatbot, LLM calls, admin pages, extra map providers, extra databases, microservices.
- R7. Status vocabulary in all reports: **VERIFIED** (proved by a command you ran and its output), **PARTIAL**, **PLANNED**, **BLOCKED**, **RECOMMENDED**. Never write "done" without a passing command to show.
- R8. Inspect the repo before changing it. If code exists, reuse what works; do not rewrite without a stated reason.
- R9. Pin dependency versions at install time (use the latest stable at that moment, record in lockfiles). Do not add a package unless a concrete requirement needs it.
- R10. Any ambiguity not resolved by this document: choose the simplest option, record it in `docs/decisions.md` (one line: decision, reason), and continue. Do not stop to ask unless the choice would violate R1–R6.

**Verification gate (every milestone).** Before declaring a milestone finished: run its listed commands, paste real output summaries into `docs/progress.md`, and list any PARTIAL/PLANNED items honestly.

---

## 2. Speed Accelerators (decisions already made — do not re-debate)

| Area | Decision | Why it saves time |
| --- | --- | --- |
| Repo | Monorepo, root `Makefile` with `make setup`, `make dev`, `make test`, `make fixtures`, `make build` | One command per task, agents and humans use the same entry points |
| Persistence | **No database.** JSON files under `data/` (`data/jobs/<id>.json`, `data/outputs/<job_id>/…`). Observation catalog is read from provider at request time | Zero infra, trivially deployable; satisfies "choose one strategy" |
| Jobs | In-process `ThreadPoolExecutor` (max 2 workers) + job state written atomically to JSON after every stage change. No Celery/Redis | Real state, minimal code |
| Job progress | `stage` field: `queued → validating → reading → aligning → differencing → statistics → exporting → completed/failed`. **No percentages** | Honest and simple |
| Contracts | Pydantic models are the source of truth → FastAPI auto-generates OpenAPI → `openapi-typescript` generates `frontend/lib/api-types.ts` via `make types` | Frontend/backend cannot drift; parallel agents share one contract |
| Map rendering of results | Backend renders a colorized **PNG + WGS84 bounds**; frontend adds it as a MapLibre `image` source. **No tile server, no COG tiling** | Biggest complexity cut; sufficient for small rasters |
| Drawing AOI | `terra-draw` with its MapLibre adapter (polygon + rectangle modes), fall back to a preset "Use demo area" button | Maintained lib, avoids hand-rolled drawing |
| Basemap | One keyless basemap style (e.g. OpenStreetMap raster tiles) configured in one constant | No API keys |
| UI kit | shadcn/ui components only: Button, Card, Badge, Table, Alert, Tabs, Skeleton, Sonner toast | Consistent, fast |
| Data fetching | TanStack Query with one typed `apiClient` in `frontend/lib/api.ts` | Uniform loading/error/empty handling |
| Cross-page state | URL search params (`?before=…&after=…&job=…`) + AOI in `sessionStorage` wrapped in try/catch | Pages are linkable, no global store library |
| Fixtures | `make fixtures` runs `backend/scripts/make_synthetic.py` (deterministic, seeded, idempotent) | Tests and demo share identical data |
| Testing | Backend: `pytest` + FastAPI `TestClient`. Frontend: Vitest + React Testing Library. E2E: Playwright (one spec) | Covers Section 9 with minimum tooling |
| Python | 3.11+, `ruff` for lint/format, `pytest`. TypeScript `strict: true`, ESLint | Fast feedback |
| Deployment | Frontend → Vercel. Backend → one Docker container (rasterio wheels bundle GDAL; if install fails, use the official `python:3.11-slim` image with `pip install rasterio`). Synthetic outputs are regenerated on container start | Avoids hosted DB/object storage |
| CORS | Allowed origins from `CORS_ORIGINS` env var (comma-separated) | One config knob |

**Parallel agent lanes (Antigravity Agent Manager).** After Milestone 1 and after the contract (Section 6) is committed, run three agents in parallel, each owning a directory and never editing another lane's files:

- **Lane A — Backend/Processing:** `backend/app/processing/**`, `backend/scripts/**`, `backend/tests/processing/**`
- **Lane B — Backend API/Providers:** `backend/app/api/**`, `providers/**`, `services/**`, `schemas/**`, `backend/tests/api/**`
- **Lane C — Frontend:** `frontend/**`, developed against `openapi.json` and MSW/fixture responses until Lane B lands

Merge only when each lane's tests pass.

---
