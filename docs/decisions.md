# Decisions Log

Format: Date | Decision | Reason

- 2026-11-12 | Git initialized with master branch | Standard source control setup for monorepo.
- 2026-11-12 | Python backend virtual environment located at `.venv` | Isolates backend dependencies from host Python 3.13 system packages.
- 2026-11-12 | Next.js with App Router, TypeScript, Tailwind CSS, shadcn/ui for frontend | Conforms with PRD Speed Accelerators (Section 2) and Frontend Specification (Section 10).
- 2026-11-12 | ResultsMap scales power-of-two PNGs to non-POT crisp canvas data URLs | Workaround for MapLibre GL v4 WebGL incomplete-texture bug when ImageSource dimensions are power-of-two (64x64) without mipmaps.
- 2026-11-12 | E2E browser verification run via Playwright driving Chrome instead of chrome-devtools MCP | Chrome remote-debugging DevToolsActivePort not active in host Chrome profile; Playwright executes full real Chrome E2E workflow across 1280px, 820px, and 390px viewports.

