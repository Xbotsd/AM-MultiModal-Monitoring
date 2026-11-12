# Architecture

## Why the analysis scripts were not rewritten

`CODE/` contains the scripts that produced the figures in the paper. Each one
`chdir`s to the repository root, reads `data/...`, and prints results. Rewriting them
into a tidy package would have changed what was run, which is exactly what a
reproduction artefact must not do.

Version 1.1.0 adds `CODE/7_measured_real/`: the real-data re-analyses of the fusion,
unwrapping, height-map, graded-decision and clutter results that earlier existed only
outside the repository. They follow the same convention — a docstring that names the
dataset and its DOI, `data/...` paths, a JSON result in `results/` — and they are
registered and tagged like every other stage.

Instead the system wraps them:

* `tools/scan_stages.py` reads `CODE/**/*.py`, extracts the docstring, the
  `data/...` paths each script touches, and whether it draws random numbers, and
  writes `src/ammonitor/stages.json`;
* `ammonitor.registry` loads that file and answers "what exists, what does it need,
  what is its provenance";
* `ammonitor.pipeline` runs a stage in a subprocess with the repository root as
  working directory, refusing to start if a declared input is missing.

A test asserts that the set of scripts on disk equals the set in the registry, so the
registry cannot drift.

## Layers

### 0. The twin decision layer (`dbound`, vendored)

The decision layer is not native to this code base. It is the standalone
[`detectability-bound`](https://github.com/Xbotsd/detectability-bound) package
(Zenodo v0.1.1, doi:10.5281/zenodo.24136698, concept `10.5281/zenodo.24080212`),
created in the same effort to answer the question the monitoring chain cannot: on
this chain, what could any detector see? It is vendored at `src/dbound/` (code
identical to upstream `81d99a2`) so that a clone installs offline. The code
dependency runs one way — this repository calls the package and never edits it except
to sync — but the two are twins in provenance, not parent and child. The
module-by-module and result-by-result mapping is in
[`TWIN_LIBRARIES.md`](TWIN_LIBRARIES.md).

### 1. Sensing and measurement (`CODE/`)

| module | contents | provenance |
|---|---|---|
| `1_acoustic` | EPFL AE classification, baselines, ablation, spectral bound, statistics | measured |
| `2_laser_ultrasound` | Cranfield LUT, label generation from geometry | measured |
| `3_fusion` | Kalman fusion, combinations, sensitivity | simulated (except `run_sensitivity_full`) |
| `4_phase_pointcloud` | phase unwrapping, point-cloud defect detection | simulated |
| `5_control` | closed loop, edge diagnosis, control baselines | simulated |
| `6_visualization` | ROC/AUC, confusion, t-SNE, figures | derived |
| `7_measured_real` | fusion, unwrapping, height maps, graded decision, XCT clutter | measured |

### 2. Decision (`src/dbound/`, `ammonitor.decision`)

One bound, two modalities. The signal energy is the only thing that changes:

```
volumetric:  E = || blur(sphere(a/L)) ||²          →  d' ∝ (a/L)³  then  (a/L)^{3/2}
transient:   E = || expected waveform ||²          →  d' ∝ sqrt(samples)
```

Inversion gives the design rule: the largest admissible voxel size for a target POD,
or the smallest signal energy, or — in the transient case — how many samples the
event must occupy.

`src/dbound/realdata.py` adds the correction that real imaging demands: the noise a
matched filter sees is not the voxel noise but the clutter, and the ratio
`κ = 23…125` is measured on public XCT data rather than assumed.

### 3. Report (`ammonitor.report`)

Partitions the stages into process evidence, method evidence and neither, and prints
a markdown report. The partition is derived from the registry, not maintained by
hand.

## Data contracts

* Stages read from `data/<dataset>/...` relative to the repository root.
* No stage writes into another stage's input directory.
* Missing inputs are an error (`returncode 2`), never an empty result.
* Datasets are not committed; `data/README.md` says where to get them and how to lay
  them out.

## Extending the system

1. Drop the script into the appropriate `CODE/<module>/` directory.
2. Run `python tools/scan_stages.py` to regenerate the registry.
3. `python -m ammonitor list` — the new stage appears with its provenance and a `!`
   if its data are missing.
4. `pytest -q` — the registry integrity test covers the new entry automatically.

