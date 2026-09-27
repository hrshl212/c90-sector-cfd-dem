# Public data

The `sanitized/` directory contains only the fields needed to reproduce the
measured particle-population figures.

## `particle_retention_timeseries.csv`

| Column | Type | Meaning |
|---|---|---|
| `time_s` | finite float | Native sample time in seconds |
| `configuration` | enum | `c90_full_cylinder_equivalent` or `full360` |
| `retained_percent` | finite float | `100 × N(t) / N(0)` for that configuration |

## `particle_count_timeseries.csv`

| Column | Type | Meaning |
|---|---|---|
| `time_s` | finite float | Native sample time in seconds |
| `configuration` | enum | `c90_full_cylinder_equivalent` or `full360` |
| `particle_count` | integer | Native full-cylinder count or C90 sector count multiplied by four |

Rows are grouped by configuration and strictly increasing in time within each
group. The two files use identical time keys. Each series contains measured
samples only and ends within the shared measured interval.
