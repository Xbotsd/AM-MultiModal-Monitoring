# Changelog

All notable changes to this repository. Versions follow the deposited Zenodo
records; the concept DOI `10.5281/zenodo.24128937` always resolves to the latest.

## [1.1.3] — 2026-11-12

### Fixed
- `run_pointcloud_real` declared its inputs as the template `data/hm/{name}.ASC`, so the
  readiness check marked the stage as missing data even when the four maps were in
  place. The four paths are now declared explicitly and the stage builds them without a
  path template.
- `ammonitor list` now shows no `!` on a complete data tree; `ammonitor chain measured`
  runs 12/12 stages against all six public datasets and reproduces every committed
  result file byte for byte.

## [1.1.2] — 2026-11-11

### Changed
- The two repositories are now presented as **twins**: dbound is the decision half,
  created to answer the question the monitoring chain cannot, not an upstream
  dependency that happened to be reused. `docs/TWIN_LIBRARIES.md` replaces
  `docs/RELATION_TO_DBOUND.md` with the module, result, paper, version and citation
  mapping; the README and architecture layer carry the same framing.
- Vendored copy recorded at dbound `v0.1.1` (commit `9924285`; the `src/dbound` tree is
  identical to `81d99a2`, so no code changes).
- Cross-citation updated: `.zenodo.json` and `CITATION.cff` point at the dbound v0.1.1
  version DOI `10.5281/zenodo.24136698`.

## [1.1.1] — 2026-11-11

### Added
- `6_visualization:run_design_rule` — generates `results/design_rule.json`, the
  largest admissible voxel table (Table 1), from the bound itself.
- `results/acoustic_holdout.json` — the hold-out metrics behind Table 4, written by
  `1_acoustic:run_eplf_v12`.
- Ten legacy statistics/complexity results moved from `data/**` (gitignored) to
  `results/`, and their producing scripts now write there too.
- `CITATION.cff`, this changelog, and the test that every committed result file is
  present and parses.
- Documentation of the prerequisite project: `docs/RELATION_TO_DBOUND.md` plus a
  README section, an architecture layer, and a `requires` relation in `.zenodo.json`.

### Changed
- Registry: 35 → **36 stages** (14 measured / 9 simulated / 13 derived).
- Tests: 20 → **21**.
- Manuscript figures regenerate from the same result files.

## [1.1.0] — 2026-11-11

### Added
- Seven measured stages that reproduce the paper's tables: acoustic spectral bound,
  Peregrine fusion, Peregrine graded decision, fringe unwrapping, WLI height maps,
  XCT clutter/ablation/detector comparison, laser-ultrasound echo detection.
- `6_visualization:run_ndte_figures` — all six manuscript figures from result files.
- `results/` artefacts for every measured analysis; `data/README.md` covers six
  public datasets with DOI, licence and layout.

### Changed
- Registry: 28 → 35 stages (14/9/12); `CODE/make_refs.py` (0 bytes) removed.
- `src/dbound` synced to upstream `81d99a2` (adds `__main__` and the `bound`
  subcommand); `pandas`, `scikit-learn` and `tifffile` are required.
- Tests: 18 → 20.

## [1.0.0] — 2026-11-09

Initial deposit: measurement chain, stage registry, provenance report, decision
layer, 18 tests, English and Chinese guides.
