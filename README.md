# AM-MultiModal-Monitoring

**An integrated in-situ monitoring system for metal additive manufacturing: measurement, fusion, control — and a closed-form bound on what any detector could possibly see.**

This repository is the code base for the LPBF/DED monitoring work, extended with a
decision layer that the original system did not have. The two halves answer
different questions and are kept apart on purpose:

| half | question | where |
|---|---|---|
| **measurement chain** | given these sensors, what process state is this? | `CODE/`, driven by `ammonitor` |
| **decision layer** | given this sensing chain, what could *any* detector achieve, and what would it cost? | `src/dbound/`, wrapped by `ammonitor.decision` |

The classifier stages report accuracy. The decision layer reports the ceiling that
accuracy is measured against. A 97% score means nothing if the flaws it misses sit
below the resolution limit; the bound says where that limit is.

## Twin library: the decision half

This repository has a twin. The decision layer is the standalone package
[**detectability-bound**](https://github.com/Xbotsd/detectability-bound), created in
the same effort **to solve this repository's problem**: a monitoring system that
reports accuracy cannot say whether the defects it misses were visible at all, so the
decision half was built to supply that statement. It is released as Zenodo v0.1.1
(doi:[10.5281/zenodo.24136698](https://doi.org/10.5281/zenodo.24136698), concept
`10.5281/zenodo.24080212`). This repository consumes it: a copy is vendored at
`src/dbound/` (code identical to upstream `81d99a2`, released as `v0.1.1`) and wrapped
by `ammonitor.decision`.

| | dbound — decision half | this repository — measurement half |
|---|---|---|
| question | what can **any** detector achieve, and at what cost? | what does **this** sensing chain measure? |
| content | bound and asymptotes, PSF/energy model, detector set, XCT estimators, design rule | measurement chain, stage registry, provenance partition, six public datasets |
| artefacts | its own manuscript, results and DOI | the integrated manuscript, 36 stages, figures, this DOI |
| relationship | defines the ceiling | produces the measurements the ceiling constrains |

The code dependency runs one way: dbound knows nothing about the monitoring chain, and
this repository never edits the vendored copy except to sync it. The provenance is
sibling, not parent and child — same author, same architecture, cross-cited. The
code-level binding is `src/ammonitor/decision.py` (energy → `bound.energy_at`, POD →
`ndtr(d′ − z)`, inversion → `required_voxel`), and a test asserts that the wrapper and
the package agree. The full mapping — module by module, result by result, versions and
sync policy — is in [`docs/TWIN_LIBRARIES.md`](docs/TWIN_LIBRARIES.md).

## Start here

| if you want to… | read |
|---|---|
| understand what the system is and where each number comes from | [`docs/使用说明.md`](docs/使用说明.md) (中文) |
| see how the two twin libraries fit together | [`docs/TWIN_LIBRARIES.md`](docs/TWIN_LIBRARIES.md) |
| install it, place data, run stages, use the decision layer | [`docs/GUIDE.md`](docs/GUIDE.md) |
| know what may be cited as process evidence | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) |
| understand the layering and data contracts | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| get the datasets | [`data/README.md`](data/README.md) |

Sixty seconds:

```bash
pip install -e .
python -m ammonitor list        # 36 stages; a leading ! means data absent
python -m ammonitor report      # what may be claimed, by provenance
pytest -q                       # 21 passed
```

## Architecture

```
                ┌──────────────────────────────────────────────────────┐
   sensors      │  acoustic emission · laser ultrasound · phase/point  │
                └───────────────┬──────────────────────────────────────┘
                                │
                ┌───────────────▼───────────────┐
   measurement  │  feature extraction           │   CODE/1_acoustic
                │  classification               │   CODE/2_laser_ultrasound
                │  fusion (Kalman)              │   CODE/3_fusion
                │  phase unwrap / point cloud   │   CODE/4_phase_pointcloud
                │  closed-loop control          │   CODE/5_control
                └───────────────┬───────────────┘
                                │  stage registry, provenance-tagged
                ┌───────────────▼───────────────┐
   decision     │  d' = ΔI√E / σ                │   src/dbound
                │  POD ≤ Φ(d' − z_{1−α})        │   ammonitor.decision
                │  inverse: L_max, energy_needed│
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
   report       │  what may be claimed, by     │   ammonitor.report
                │  provenance category         │
                └───────────────────────────────┘
```

## The decision layer in one paragraph

For a known signal in additive noise, the matched filter maximises the deflection
`d' = ‖s‖/σ`, and no detector — including any trained one — can exceed
`POD = Φ(d' − z_{1−α})` (Neyman–Pearson plus Cauchy–Schwarz). What differs by
modality is only where `‖s‖²` comes from. For a volumetric flaw of diameter `a` imaged
with point-spread width `L`, `‖s‖² = E(a/L)` and

```
d' ∝ (a/L)³     below the voxel size        d' ∝ (a/L)^{3/2}   above it
```

so **one halving of the voxel size is worth 64 repeat scans** in the first regime
and 8 in the second. For a transient event — an acoustic burst, a laser-ultrasound
echo — `‖s‖²` is simply the squared norm of the expected waveform, so what matters
is how many samples the event occupies rather than how fine the grid is.

## Quick start

```bash
pip install -e .
python -m ammonitor list          # 36 stages with provenance and data status
python -m ammonitor report        # what may be claimed, by category
python -m ammonitor bound --a 100 --L 40 --dI-over-sigma 5
pytest -q                         # 21 tests
```

`ammonitor list` marks stages whose declared input data are absent with `!`. Nothing
runs silently on missing data.

## Worked examples

**Volumetric, from the command line** — a 100 µm flaw imaged at 40 µm, contrast
five times the noise:

```
d' = 9.50      POD bound = 1.000      largest admissible voxel for POD 0.9: 66.1 µm
```

**Transient, on the measured EPFL acoustic set** (31 401 waveforms × 5 000 samples,
three classes). Taking each class mean as the expected waveform and the within-class
residual as the noise the detector faces:

| class | n | d' | POD at α = 0.01 |
|---|---|---|---|
| 1 | 300 | 4.0 | 0.956 |
| 2 | 300 | 4.1 | 0.959 |
| 0 | 300 | 4.2 | 0.970 |

Reproduce with `python tools/ae_detectability.py --data-root <path> --set D1`.
A deflection of four is a POD of 0.96 and no more: class means are only marginally
separable, which is why the measurement chain needs features rather than templates.

## Provenance is a first-class property

Every stage is tagged by what it runs on, and the reporter will not merge the
categories:

| category | stages | may be cited as |
|---|---|---|
| `measured` | 14 | evidence about the process |
| `simulated` | 9 | evidence about the method only |
| `derived` | 13 | neither; statistics and figures |

The simulated fusion, unwrapping, point-cloud and closed-loop control modules are
simulation studies — they carry `np.random` seeds and no measured capture — and are
labelled as such. The measured counterparts that produced the paper's fusion,
unwrapping, height-map, graded-decision and clutter numbers are separate stages in
`CODE/7_measured_real/`. Averaging a simulated result with a measured one into a
single "system accuracy" is precisely the mistake `ammonitor report` exists to
prevent. See `docs/PROVENANCE.md`.

## Repository layout

```
CODE/                     the analysis scripts (unchanged where they produced figures)
CODE/7_measured_real/     the real-data re-analyses of the fusion, unwrapping,
                          height-map, graded-decision and clutter results
src/ammonitor/            orchestration: registry, pipeline, decision, report, CLI
src/dbound/               the detectability bound: E(x), d', inversion, real-data kappa
tests/                    registry integrity, provenance/data coverage, decision math
tools/                    stage scanner (generates stages.json), acoustic demo
docs/                     architecture and provenance
data/                     datasets are not committed; see data/README.md
```

`src/ammonitor/stages.json` is **generated from the source** by
`tools/scan_stages.py`, and a test asserts that every `.py` under `CODE/` appears in
it. A script cannot be added without the system noticing.

## Datasets

| dataset | modality | size | source |
|---|---|---|---|
| EPFL acoustic emission | AE, 3 classes, 31 401 × 5 000 | 4.5 GB | [Zenodo 10449883](https://zenodo.org/records/10449883) |
| Cranfield laser ultrasound | LUT, FMC array | 45 MB | [doi:10.17862/cranfield.rd.15190191](https://doi.org/10.17862/cranfield.rd.15190191) |
| ORNL Peregrine coupons | 4 process channels + tensile test | 11 MB | [Zenodo 23727492](https://zenodo.org/records/23727492) |
| Fringe projection | phase-stepped fringes + PUMA truth | 41 MB | [Zenodo 22125908](https://zenodo.org/records/22125908) |
| WLI height maps | 4 DED tracks, 480 × ~20 000 px | 1.0 GB | [Zenodo 21285367](https://zenodo.org/records/21285367) |
| XCT AlSi10Mg | 212 slices, 37 µm voxels | 127 MB | [Zenodo 17602110](https://zenodo.org/records/17602110) |

None is committed. Place them under `data/` as described in `data/README.md`; the
registry tells you which stages need which.

## What this repository adds

1. **A decision layer** that states the sensing chain's ceiling and its cost, applied
   to both the volumetric and the transient modality with one bound.
2. **A machine-generated stage registry** with a provenance tag per stage, so the
   system cannot quietly mix measured and simulated evidence.
3. **An explicit claim partition** (`ammonitor report`): what is process evidence,
   what is method evidence, what is neither.

The analysis scripts in `CODE/` are unchanged where they produced published figures;
that is deliberate. The real-data re-analyses added for v1.1.0 sit beside them in
`CODE/7_measured_real/` and write the result files the paper's tables are generated
from.

## Measured analyses added since v1.0.0

Four of the paper's tables are computed from public captures that the v1.0.0 package
mentioned only in prose. They are now stages, each with its dataset DOI in the
docstring and its output in `results/`:

| result | stage | reproduces |
|---|---|---|
| fusion | `7_measured_real:run_fusion_real` | RMSE 38.20 / 37.43 / 36.03 MPa; 302.30 and 512.67 build-held-out |
| unwrapping | `7_measured_real:run_unwrap_real` | 0.532 mm over 6.2 mm; no refinement improves it |
| height maps | `7_measured_real:run_pointcloud_real` | 2.9–5.0 µm robust deviation; no 10 µm window |
| graded decision | `7_measured_real:run_decision_real` | AUC 0.751; 0.54–0.93 per build; enrichment 2.25 |
| clutter κ | `7_measured_real:run_xct_clutter` | 24–125 across 1–16 voxels; 0.530/0.117/0.023 detector PODs |
| spectral bound | `1_acoustic:run_ae_spectral` | 88.9 % ± 0.3 %; d′ 2.83–3.12 at 64 bands |
| laser-ultrasound echo | `7_measured_real:run_lu_echo` | d′ 16.4 / 6.0; κ 0.99 / 0.98; POD 0.838 / 0.427 |
| design rule | `6_visualization:run_design_rule` | Table 1 reproduced to the digit |

The six manuscript figures are drawn from these files by
`6_visualization:run_ndte_figures`, which reads the registry live so the system figure
cannot quote counts the registry no longer has.

## Citation and licence

Code: MIT. Datasets keep their own licences. If you use this system, cite the
underlying paper and the dataset records above.

