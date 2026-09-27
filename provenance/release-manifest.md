# Release manifest

## Public artifact classes

- Narrative and equations are independently authored for this repository.
- Result tables contain sanitized aggregate metrics only.
- Particle-population CSVs contain minimal time, configuration, and population
  fields.
- The population plotting script consumes only repository-local public data.
- No simulation source, patch, executable, input deck, checkpoint, raw log,
  scheduler script, or private filesystem reference is included.

## Figure status

`particle_retention_measured.png` and `particle_count_measured.png` are
reproducible from the public CSVs and plotting script.

The two files with `_interim` in their names are user-approved comparison
figures retained for project presentation. They are qualitative context, not
release-qualified quantitative evidence.

## Review state

Version `0.1.0` is a local review candidate. Automated checks cover public
data, local links, expected files, and common private-identifier leakage.
Citation and copyright metadata identify Harshal Raut as the sole contributor.
The author approved inclusion of the two interim comparison figures and
authorized local Git initialization. MFiX-Exa source and private modifications
remain outside the repository.
