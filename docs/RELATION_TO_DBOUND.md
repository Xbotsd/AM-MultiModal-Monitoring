# How this repository relates to `detectability-bound`

This repository has a prerequisite: the standalone
[`detectability-bound`](https://github.com/Xbotsd/detectability-bound) package
(`dbound`). The two are separate artefacts with separate DOIs, and neither is
complete without the other for the purpose of the integrated paper. This file states
the relationship precisely, so that a reader can tell which claim comes from which
artefact.

## 1. What each project is

| | `detectability-bound` (prerequisite) | `AM-MultiModal-Monitoring` (this repository) |
|---|---|---|
| role | theory, demo and reference implementation of the bound | the monitoring system that the bound is applied to |
| question | what can **any** detector achieve on a given sensing chain, and what would it cost to do better? | what does **this** chain actually measure, and which of those numbers are process evidence? |
| scope | modality-agnostic: volumetric flaws and transient events | acoustic emission, laser ultrasound, phase/point cloud, fusion, control, six public datasets |
| artefacts | `bound`, `psf`, `detectors`, `realdata`, `experiments`, CLI; its own manuscript, results and Zenodo record | 35 registered stages, provenance partition, measured re-analyses, six figures, this Zenodo record |
| does **not** do | know about stages, provenance, monitoring data or a measurement chain | derive or modify the bound, or own the XCT estimator |

In one sentence: **dbound defines the ceiling; this repository produces the
measurements that the ceiling constrains, and says which of them are evidence.**

## 2. Dependency direction

`dbound` is upstream. This repository consumes it and never the reverse:

```
detectability-bound (upstream, Zenodo v0.1.0)
        │  vendored copy at src/dbound/ (commit 81d99a2)
        ▼
src/dbound/ ──► src/ammonitor/decision.py ──► ammonitor CLI, stages, figures
        │
        └──► CODE/7_measured_real/run_xct_clutter.py (XCT measurement)
```

The copy is vendored rather than declared as a pip dependency so that one clone
installs offline and stays pinned. The cost is drift, which is handled by
`src/dbound/VENDORED.md` (upstream commit, version, sync procedure) and by a test
that asserts the wrapper and the package agree. No other file under `src/dbound/`
is edited here.

## 3. Code mapping

| `dbound` module | what it provides | how this repository uses it |
|---|---|---|
| `bound.py` | `energy_at`, `energy_curve`, `pod_bound`, `required_voxel`, `z_from_p`, `repeats_to_match_resolution` | `ammonitor.decision` wraps each; `run_ndte_figures` draws Figs. 1–2 from `energy_curve` |
| `psf.py` | Gaussian kernel, sphere rendering, blur, PSF from autocorrelation / edge spread | inside the XCT estimators; defines `E(a/L)` numerically |
| `detectors.py` | matched filter, searched matched filter, peak detector, template construction, signal energy | inside the XCT clutter and detector-comparison measurements |
| `realdata.py` | DICOM loading, material mask, σ estimators, κ, measured POD curves | called by `experiments` on the XCT stack |
| `experiments.py` | `measure_group`, `cross_group`, `ablate`, `compare_detectors`, `check_algebra` | `CODE/7_measured_real/run_xct_clutter.py` calls all four |
| `cli.py` / `__main__.py` | `python -m dbound bound|measure|ablate|compare|all` | vendored, so the decision layer can be exercised without the monitoring system |

The wrapper is deliberately thin: `ammonitor.decision` adds units, argument names
and the CLI surface, not new mathematics. `tests/test_system.py` asserts
`decision.volumetric_energy(a, L) == bound.energy_at(a / L)`.

## 4. Result mapping

| `dbound` result | this repository's result | used by |
|---|---|---|
| `measure_vol_gd.json` (σ, PSF, κ table, measured POD) | `results/xct_clutter.json` → `primary` | Table 6, Fig. 5 |
| `cross_group.json` (κ on three reconstructions) | `results/xct_clutter.json` → `cross_group` | Table 7, Fig. 5 |
| `ablation.json` (templates, noise estimators, padding, α) | `results/xct_clutter.json` → `ablation` | Fig. 6b,c |
| `comparison.json` (oracle / searched / peak on real metal) | `results/xct_clutter.json` → `comparison` | Fig. 6a |
| `verify_algebra.json` (Propositions 1–2 and bound tightness) | not duplicated — run `python -m dbound verify` | Section 4.4 |
| `design_rule.json` (Table 1) | not yet duplicated — see the maintenance audit | Table 1 |

The transient and application results have no counterpart upstream:
`results/ae_spectral.json`, `lu_echo.json`, `fusion_real.json`, `decision_real.json`,
`unwrap_real.json`, `pointcloud_real.json` are produced by this repository's stages.
That is the division of labour: dbound measures what the imaging chain costs in
general; this repository measures what each monitoring channel delivers in practice.

## 5. Paper mapping

The integrated manuscript (`NDTE_manuscript.*`) uses both halves:

| part of the paper | source artefact |
|---|---|
| §2 derivation, asymptotes, transient and fusion forms | `dbound` theory |
| §4.4 bound verification, §4.5 clutter correction, §4.6 detector comparison | `dbound` + `results/xct_clutter.json` |
| §3 system, registry, provenance, claim partition | this repository |
| §4.1–4.3, §4.7–4.9 measured chain, transient channels, geometric and decision modules | this repository's measured stages |
| Table 9 claim ledger | this repository's registry, with the dbound-derived rows labelled |

`dbound` also has its own manuscript: that is the prerequisite demonstration of the
bound on its own. The integrated paper extends it with the monitoring system and the
six datasets; it does not replace it.

## 6. Versions and identifiers

| | `detectability-bound` | this repository |
|---|---|---|
| version used here | `0.1.0` | `1.1.0` |
| version DOI | `10.5281/zenodo.24080213` | `10.5281/zenodo.24135622` |
| concept DOI (always latest) | `10.5281/zenodo.24080212` | `10.5281/zenodo.24128937` |
| vendored commit | `81d99a2` | — |

When dbound moves, the copy is refreshed with the procedure in
`src/dbound/VENDORED.md`, the commit in that file is updated, and `pytest -q` is run.
The two version numbers need not match; the pair above is the one the integrated
paper reports.

## 7. Citation

Cite both when using the integrated system: the concept DOI of this repository for
the system, and the version DOI of `detectability-bound` for the bound. Cite only
`detectability-bound` when using the bound on its own.
