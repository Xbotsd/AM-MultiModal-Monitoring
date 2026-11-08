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

## How the tag is decided

`tools/scan_stages.py` assigns a default per module — the module is the reliable
signal, because several scripts both read and write under `data/` — and then
applies per-stage overrides for the exceptions.

```python
MODULE_PROVENANCE = {
    "1_acoustic": "measured",          # EPFL set, read from disk
    "2_laser_ultrasound": "measured",  # Cranfield set, read from disk
    "3_fusion": "simulated",           # generates sensor streams
    "4_phase_pointcloud": "simulated", # generates the phase field and the cloud
    "5_control": "simulated",          # generates trajectories
    "6_visualization": "derived",
}
```

A name or docstring containing `sim` / `仿真` / `模拟` forces `simulated`
regardless of module. `OVERRIDES` in the scanner handles the two cases where the
module default is wrong.

**This replaced a path heuristic that was wrong.** The first version tagged any
script touching `data/phase_unwrap` as measured; the phase-unwrap scripts in fact
*generate* the deformation field (`np.random.seed(42)`, "生成真实形变场") and write
it there. They are now simulated, which is why the counts below are 7 / 9 / 12 and
not 9 / 7 / 12.

## Categories

### `measured` — 7 stages

Reads a measured public dataset, or analyses one that was read elsewhere.

| stage | data |
|---|---|
| `1_acoustic:run_eplf_v12` | EPFL acoustic, `data/epfl_acoustic/Deciphering AE` |
| `1_acoustic:run_acoustic_baseline_v2` | same |
| `1_acoustic:run_acoustic_ablation` | same |
| `2_laser_ultrasound:prepare_lu_v3` | Cranfield LUT, `data/laser_ultrasound` |
| `2_laser_ultrasound:run_lu_v2` | same |
| `3_fusion:run_sensitivity_full` | `data/laser_ultrasound/X_lu.npy` |
| `run_epfl_cross_subset` | EPFL D1–D4 |

A `measured` tag means the *input* is measured. These stages still draw random
numbers internally — for cross-validation folds and bootstrap — which does not make
their results simulated.

### `simulated` — 9 stages

Generates its own data. Results are statements about the method, never about the
process.

| stage | why |
|---|---|
| `3_fusion:run_fusion_baseline` | synthesises sensor streams to compare fusion rules |
| `3_fusion:run_fusion_combinations` | same, across modality subsets |
| `3_fusion:run_fusion_sim` | Kalman framework validated on generated trajectories |
| `4_phase_pointcloud:run_phase_unwrap_v4` | generates the deformation field and the noise, writes a known truth |
| `4_phase_pointcloud:run_unwrap_baseline` | baseline on the same generated field |
| `4_phase_pointcloud:run_pointcloud_v4` | point cloud generated, not captured |
| `5_control:offline_diagnosis` | diagnostic logic exercised on generated states |
| `5_control:run_closed_loop_v3` | closed loop over generated trajectories |
| `5_control:run_control_baseline_v4` | control baseline, generated trajectories |

These are the modules most likely to be quoted out of context, which is why the tag
is generated from the source rather than asserted in prose.

### `derived` — 12 stages

Statistics and figures computed on the output of the other two. Neither evidence
about the process nor about a method; evidence about the other stages.

## The decision layer and provenance

`ammonitor.decision` is not a stage and carries no provenance tag, because it is not
a measurement and not a simulation: it is a statement about sensing. It applies
equally to a measured chain and to a simulated one, which is why it is kept in a
separate package (`src/dbound/`) with its own tests.

## What would falsify the tags

* A `simulated` stage that starts reading a measured capture. The scanner reads the
  module and the declared paths, so the tag would change on the next rebuild — and
  the CI job that re-runs `tools/scan_stages.py` and diffs `stages.json` would fail
  until the change is committed.
* A `measured` stage whose data directory is absent. `ammonitor list` marks it with
  `!` and `ammonitor run` refuses to execute it.
* A script added to `CODE/` but missing from the registry. A test fails.
