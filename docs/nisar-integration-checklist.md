# NISAR Integration Checklist (Phase B Readiness)

**Status:** **BLOCKED** — Awaiting official NASA Space Apps 2026 "Dancing with the SARs" resources (release: Fri 13 Nov 2026).

> **Strict Phase A Rule (R2):** This document contains **questions only**, not guessed answers. Do not populate target paths, endpoints, authentication mechanisms, or product specifications until official challenge documentation is published.

---

## 1. Official Data & Product Discovery Questions

1. **Product Levels & Formats:** What official product levels and container/raster formats are provided in the challenge resources?
2. **Access & Authentication:** How is data accessed, downloaded, or queried, and what authentication mechanism (if any) is required?
3. **Polarizations & Frequency Bands:** Which polarizations and frequency bands are present in the provided datasets?
4. **Radiometric Units & Scale:** Are backscatter pixel values provided in linear power, amplitude, or decibels (dB)?
5. **Calibration & Radiometric Corrections:** What calibration, terrain flattening, or scaling factor notes apply before differencing?
6. **Spatial Metadata (Footprints & CRS):** How are observation footprints, bounding geometries, coordinate reference systems (CRS), and pixel transforms expressed?
7. **Study Area Coverage:** Which study area has at least two usable, comparable acquisitions suitable for the demonstration?
8. **Resource Scale & Performance:** What are the typical file sizes, spatial resolutions, and expected processing times within the AOI window?
9. **Product-Specific Compatibility Rules:** What product-specific compatibility rules (e.g., pass direction, look side, incidence angle tolerance, mode matching) should be added to Section 8.3?

---

## 2. Study-Area Selection Criteria (Pre-Release Framework)

Once official datasets are available in Phase B, select the final study area using the following objective criteria:
- **Temporal Pair Availability:** At least two acquisitions covering the exact same AOI within the target event window.
- **Parameter Consistency:** Matching polarization, frequency band, processing level, and compatible orbit/geometry parameters so Section 8.3 rules pass cleanly.
- **AOI Size Budget:** Bounded within `MAX_AOI_AREA_KM2` to keep window reads, differencing, and PNG rendering responsive inside container memory limits.
- **Physical Interpretability:** Known documented surface change context from official challenge materials without fabricating thresholded classifications.

---

## 3. Provider Implementation Notes (Phase B Boundary)

- **Provider Isolation:** Implement real catalog search and asset retrieval strictly inside `backend/app/providers/nisar_provider.py` following `BaseProvider`.
- **Reader Isolation:** If official datasets use a non-GeoTIFF container, implement a dedicated reader under `backend/app/processing/readers/` conforming to `BaseReader.read(path, window) -> RasterData`.
- **Unit Conversion:** If official pixel values are linear power or amplitude rather than dB, insert an explicit conversion step only after verifying the official calibration equation.
- **Registry Activation:** Register `"nisar"` in `backend/app/providers/registry.py` only after end-to-end verification tests pass against official sample files.

