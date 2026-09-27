# Public scripts

`plot_particle_population.py` is an independent plotting utility that consumes
only the sanitized CSV files in this repository. It writes normalized
retention and raw-count figures.

```bash
python3 scripts/plot_particle_population.py \
  --retention-csv data/sanitized/particle_retention_timeseries.csv \
  --count-csv data/sanitized/particle_count_timeseries.csv \
  --output-dir build/figures
```

`check_release.py` validates required files, CSV invariants, local Markdown
links, and the absence of common private-workspace identifiers.
