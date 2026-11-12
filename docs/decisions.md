# Decisions Log

Format: Date | Decision | Reason

- 2026-11-12 | Git initialized with master branch | Standard source control setup for monorepo.
- 2026-11-12 | Python backend virtual environment located at `.venv` | Isolates backend dependencies from host Python 3.13 system packages.
- 2026-11-12 | Next.js with App Router, TypeScript, Tailwind CSS, shadcn/ui for frontend | Conforms with PRD Speed Accelerators (Section 2) and Frontend Specification (Section 10).
- 2026-11-12 | ResultsMap scales power-of-two PNGs to non-POT crisp canvas data URLs | Workaround for MapLibre GL v4 WebGL incomplete-texture bug when ImageSource dimensions are power-of-two (64x64) without mipmaps.
- 2026-11-12 | E2E browser verification run via Playwright driving Chrome instead of chrome-devtools MCP | Chrome remote-debugging DevToolsActivePort not active in host Chrome profile; Playwright executes full real Chrome E2E workflow across 1280px, 820px, and 390px viewports.
- 2026-11-12 | `app.processing.validation.validate_compatibility` is the single compatibility rule source of truth; V-VALID skips unreadable/corrupt TIFFs during sync validation | Keeps validation DRY across API and pipeline while preserving async `failed` job handling for corrupt rasters.
- 2026-11-12 | Standardized HTTP 403/404/413/422 validation, unknown routes, and path-traversal errors under `INVALID_REQUEST` envelope | Keeps all non-2xx API responses compliant with the Section 6 error envelope without exposing internal paths.
- 2026-11-12 | Dashboard derives recent analyses from client-side stored job IDs hydrated via `GET /api/analysis/{job_id}` | Preserves the strict 8-endpoint API contract without adding a ninth list endpoint while showing live server status.
- 2026-11-12 | Pinned `eslint@8.57.1` and `eslint-config-next@14.2.18` with `.eslintrc.json` extending `next/core-web-vitals` | Enables non-interactive `npm run lint` matching Next.js 14.2.18 while pinning exact package versions per Rule R9.
- 2026-11-12 | `backend/Dockerfile` uses `python:3.13-slim` and installs `libexpat1` | Matches pinned `backend/requirements.txt` (`contourpy==1.4.0` requires `>=3.12`) and provides `libexpat.so.1` needed by `rasterio` on Debian slim.
- 2026-11-12 | Transform GeoJSON AOIs into each raster's native CRS via `rasterio.warp.transform_geom` before pixel window calculation | Supports projected GeoTIFFs (e.g. `EPSG:32643`) without resampling source pixels or assuming every asset uses `EPSG:4326`.
- 2026-11-12 | Use single-hue `gray` colormap for `before.png`/`after.png` and reserve diverging `coolwarm` for `difference.png`, matching the Results legend gradient | Avoids false perceptual breakpoints on monotone SAR backscatter layers while highlighting positive/negative dB changes on the difference layer.
- 2026-11-12 | Extract focused subcomponents under `frontend/components/{analysis,results}/` and remove duplicate root prompt copy | Improves page maintainability without over-fragmenting smaller pages and eliminates duplicate PRD documentation.

