# Provenance: measured, simulated, derived

This file states the rule the system enforces in code, and lists where each
category lives.

## The rule

Results from different provenance categories are never averaged, and a headline
number is never quoted without its category.

```bash
python -m ammonitor report
```

prints three disjoint lists. If a number is not in `process_evidence`, it is not
evidence about the manufacturing process.

## Categories

### `measured` — 9 stages

Reads a measured public dataset.

| stage | data |
|---|---|
| `1_acoustic:run_eplf_v12` | EPFL acoustic, `data/epfl_acoustic/Deciphering AE` |
| `1_acoustic:run_acoustic_baseline_v2` | same |
| `1_acoustic:run_acoustic_ablation` | same |
| `2_laser_ultrasound:prepare_lu_v3` | Cranfield LUT, `data/laser_ultrasound` |
| `2_laser_ultrasound:run_lu_v2` | same |
| `3_fusion:run_sensitivity_full` | `data/laser_ultrasound/X_lu.npy` |
| `4_phase_pointcloud:run_phase_unwrap_v4` | `data/phase_unwrap` |
| `4_phase_pointcloud:run_unwrap_baseline` | same |
| `run_epfl_cross_subset` | EPFL D1–D4 |

A `measured` tag means the *input* is measured. These stages still draw random
numbers internally — for cross-validation folds and bootstrap — which does not make
their results simulated.

### `simulated` — 7 stages

Generates its own data. Results are statements about the method, never about the
process.

| stage | why |
|---|---|
| `3_fusion:run_fusion_baseline` | synthesises sensor streams to compare fusion rules |
| `3_fusion:run_fusion_combinations` | same, across modality subsets |
| `3_fusion:run_fusion_sim` | Kalman framework validated on generated trajectories |
| `4_phase_pointcloud:run_pointcloud_v4` | point cloud generated, not captured |
| `5_control:offline_diagnosis` | diagnostic logic exercised on generated states |
| `5_control:run_closed_loop_v3` | closed loop over generated trajectories |
| `5_control:run_control_baseline_v4` | control baseline, generated trajectories |

These are the modules most likely to be quoted out of context, which is why the tag
is generated from the source rather than asserted in prose: `tools/scan_stages.py`
reads each file's docstring and name, and the classification is reproducible.

### `derived` — 12 stages

Statistics and figures computed on the output of the other two. Neither evidence
about the process nor about a method; evidence about the other stages.

## The decision layer and provenance

`ammonitor.decision` is not a stage and carries no provenance tag, because it is not
a measurement and not a simulation: it is a statement about sensing. It applies
equally to a measured chain and to a simulated one, which is why it is kept in a
separate package (`src/dbound/`) with its own tests.

## What would falsify the provenance tags

* A `simulated` stage that turns out to read a measured file. The scanner checks
  the declared `data/...` paths, so this would show up as a path in `data_paths`
  that points at a measured dataset.
* A `measured` stage whose data directory is absent. `ammonitor list` marks it with
  `!` and `ammonitor run` refuses to execute it.
* A script added to `CODE/` but missing from the registry. A test fails.
