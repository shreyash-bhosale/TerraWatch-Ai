# NISAR Metadata Mapping Template (Phase B)

**Status:** **BLOCKED** — Template only; columns intentionally left blank until official NISAR dataset schemas are released on Fri 13 Nov 2026.

> **Strict Phase A Rule (R2):** Do not fill in assumed NISAR attribute keys, container paths, or endpoints before inspecting official documentation.

| TerraWatch `Observation` Field | Required? | Expected Type / Format | Official NISAR Source Field / Attribute | Transformation / Calibration Notes | Verification Status |
| --- | --- | --- | --- | --- | --- |
| `id` | Yes | `string` | *(TBD)* | *(TBD)* | BLOCKED |
| `provider` | Yes | `string` | *(TBD)* | *(TBD)* | BLOCKED |
| `synthetic` | Yes | `boolean` (`false` for real data) | *(TBD)* | *(TBD)* | BLOCKED |
| `acquisition_date` | Yes | `string` (ISO 8601 UTC) | *(TBD)* | *(TBD)* | BLOCKED |
| `geometry` | Yes | GeoJSON Polygon (`EPSG:4326`) | *(TBD)* | *(TBD)* | BLOCKED |
| `asset_location` | Yes | `string` (local path or URI) | *(TBD)* | *(TBD)* | BLOCKED |
| `asset_format` | Yes | `string` | *(TBD)* | *(TBD)* | BLOCKED |
| `product_name` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `polarization` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `frequency_band` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `orbit_direction` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `processing_level` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `measurement_units` | No | `string \| null` (`dB`, etc.) | *(TBD)* | *(TBD)* | BLOCKED |
| `resolution` | No | `float \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `crs` | No | `string \| null` | *(TBD)* | *(TBD)* | BLOCKED |
| `source_metadata` | No | `object \| null` (raw unmodified) | *(TBD)* | *(TBD)* | BLOCKED |

