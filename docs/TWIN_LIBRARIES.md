# Two libraries, one question

`detectability-bound` (dbound) and this repository are twins. They were built in the
same effort, answer two halves of one question, and are released under separate DOIs:

> **What can this sensing chain see — and what could *any* detector see on it?**

This repository answers the first half by measuring; dbound answers the second by
deriving a ceiling. dbound was created **to solve this repository's problem**: a
monitoring system that reports accuracy cannot say whether the defects it misses were
visible at all, so the decision half was built to supply that missing statement.

## 1. Two halves

| | `detectability-bound` | `AM-MultiModal-Monitoring` |
|---|---|---|
| role | decision half: theory and reference implementation | measurement half: system and application |
| question | what can **any** detector achieve, and what does it cost? | what does **this** chain actually measure? |
| scope | modality-agnostic: volumetric flaws and transient events | acoustic emission, laser ultrasound, phase/point cloud, fusion, control; six public datasets |
| artefacts | `bound`, `psf`, `detectors`, `realdata`, `experiments`, CLI; its own paper, results and Zenodo record | 36 registered stages, provenance partition, measured re-analyses, six figures, this Zenodo record |
| does not do | know about stages, provenance, monitoring data | derive or modify the bound; own the XCT estimator |

## 2. What "twin" means for the code

The code dependency runs one way — this repository vendors a pinned copy of dbound
and never edits it — but the provenance is sibling, not parent/child:

```
detectability-bound (v0.1.1, commit 9924285)
        │  vendored copy at src/dbound/ (code identical to 81d99a2)
        ▼
src/dbound/ ──► src/ammonitor/decision.py ──► ammonitor CLI, stages, figures
        │
        └──► CODE/7_measured_real/run_xct_clutter.py (XCT measurement)
```

Vendoring rather than a pip dependency keeps one clone installable offline and the
copy pinned; the cost is drift, handled by `src/dbound/VENDORED.md` and by a test
that asserts the wrapper and the package agree. The sync procedure is one-way:
dbound moves, this repository refreshes the copy.

## 3. Code mapping

| `dbound` module | what it provides | how this repository uses it |
|---|---|---|
| `bound.py` | `energy_at`, `energy_curve`, `pod_bound`, `required_voxel`, `z_from_p`, `repeats_to_match_resolution` | `ammonitor.decision` wraps each; `run_ndte_figures` draws Figs. 1–2 from `energy_curve`; `run_design_rule` builds Table 1 |
| `psf.py` | Gaussian kernel, sphere rendering, blur, PSF from autocorrelation / edge spread | inside the XCT estimators; defines `E(a/L)` numerically |
| `detectors.py` | matched filter, searched matched filter, peak detector, template construction, signal energy | inside the XCT clutter and detector-comparison measurements |
| `realdata.py` | DICOM loading, material mask, σ estimators, κ, measured POD curves | called by `experiments` on the XCT stack |
| `experiments.py` | `measure_group`, `cross_group`, `ablate`, `compare_detectors`, `check_algebra` | `CODE/7_measured_real/run_xct_clutter.py` calls all four |
| `cli.py` / `__main__.py` | `python -m dbound bound|measure|ablate|compare|all` | vendored, so the decision layer can be exercised alone |

The wrapper is deliberately thin: `ammonitor.decision` adds units, argument names and
the CLI surface, not new mathematics.
`tests/test_system.py::test_volumetric_energy_matches_the_bound_module` asserts
`decision.volumetric_energy(a, L) == bound.energy_at(a / L)`.

## 4. Result mapping

| `dbound` result | this repository's result | used by |
|---|---|---|
| `measure_vol_gd.json` (σ, PSF, κ table, measured POD) | `results/xct_clutter.json` → `primary` | Table 6, Fig. 5 |
| `cross_group.json` (κ on three reconstructions) | `results/xct_clutter.json` → `cross_group` | Table 7, Fig. 5 |
| `ablation.json` (templates, noise estimators, padding, α) | `results/xct_clutter.json` → `ablation` | Fig. 6b,c |
| `comparison.json` (oracle / searched / peak on real metal) | `results/xct_clutter.json` → `comparison` | Fig. 6a |
| `verify_algebra.json` (Propositions 1–2 and bound tightness) | not duplicated — run `python -m dbound verify` | Section 4.4 |
| `design_rule.json` (Table 1) | `results/design_rule.json`, regenerated from the bound | Table 1 |

The transient and application results have no counterpart in dbound:
`results/ae_spectral.json`, `lu_echo.json`, `fusion_real.json`, `decision_real.json`,
`unwrap_real.json`, `pointcloud_real.json` are this repository's own. That is the
division of labour: dbound prices the chain; this repository measures it.

## 5. Paper mapping

The integrated manuscript (`NDTE_manuscript.*`) uses both halves:

| part of the paper | source artefact |
|---|---|
| §2 derivation, asymptotes, transient and fusion forms | dbound theory |
| §4.4 bound verification, §4.5 clutter correction, §4.6 detector comparison | dbound + `results/xct_clutter.json` |
| §3 system, registry, provenance, claim partition | this repository |
| §4.1–4.3, §4.7–4.9 measured chain, transient channels, geometric and decision modules | this repository's measured stages |
| Table 9 claim ledger | this repository's registry, with the dbound-derived rows labelled |

dbound also has its own manuscript: the decision half demonstrated on its own. The
integrated paper joins the two halves; neither replaces the other.

## 6. Versions and identifiers

| | `detectability-bound` | this repository |
|---|---|---|
| version used here | `0.1.1` | `1.1.2` |
| version DOI | `10.5281/zenodo.24136698` | concept `10.5281/zenodo.24128937` |
| concept DOI | `10.5281/zenodo.24080212` | `10.5281/zenodo.24128937` |
| vendored commit | `9924285` (code identical to `81d99a2`) | — |

When dbound moves, refresh the copy with the procedure in
`src/dbound/VENDORED.md`, update the commit there, and run `pytest -q`.

## 7. Citation

Cite both when using the integrated system: this repository's concept DOI for the
system, `10.5281/zenodo.24136698` for the bound. Cite only dbound when using the
bound on its own.
