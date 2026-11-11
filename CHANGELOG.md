# Changelog

All notable changes to this repository. Versions follow the deposited Zenodo
records; the concept DOI `10.5281/zenodo.24128937` always resolves to the latest.

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
