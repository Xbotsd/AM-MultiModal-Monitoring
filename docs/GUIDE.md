# User guide

How to install the system, give it data, run it, and read the result without
misreading it.

Contents
1. [What the system is](#1-what-the-system-is)
2. [Install](#2-install)
3. [Put the data in place](#3-put-the-data-in-place)
4. [Find and run stages](#4-find-and-run-stages)
5. [Use the decision layer](#5-use-the-decision-layer)
6. [Read the provenance](#6-read-the-provenance)
7. [Add a stage](#7-add-a-stage)
8. [FAQ](#8-faq)

---

## 1. What the system is

Two things that are usually kept apart:

* the **measurement chain** — acoustic emission, laser ultrasound, phase and point
  cloud, fusion, control. It answers *"what process state is this?"*
* the **decision layer** — a closed-form bound on what any detector could achieve
  given the sensing chain. It answers *"what could anything possibly see, and what
  would it cost to see more?"*

Both are needed. Accuracy alone does not tell you whether the flaws being missed were
detectable in the first place; a bound alone does not tell you what the process is
doing.

The analysis scripts in `CODE/` are unchanged — they produced the published figures.
The system wraps them with a **stage registry** instead of rewriting them.

---

## 2. Install

```bash
git clone https://github.com/Xbotsd/AM-MultiModal-Monitoring.git
cd AM-MultiModal-Monitoring

python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

pip install -e .
pytest -q                       # 20 passed
```

Core dependencies: `numpy`, `scipy`, `matplotlib`, `PyWavelets`, `pydicom`,
`pandas`, `scikit-learn`, `tifffile`. The last three carry the measured re-analyses
in `CODE/7_measured_real/`; the legacy classification scripts need `scikit-learn`
too, so it is no longer an optional extra.

If you do not want to install, `PYTHONPATH=src python -m ammonitor ...` works.

---

## 3. Put the data in place

The datasets are not committed: the acoustic set alone is 4.5 GB, and the six public
sources together are several gigabytes. See `data/README.md` for the records,
licences and the exact layout of each. Summary:

```
data/
├── epfl_acoustic/Deciphering AE/    # D1–D4 waveforms + labels
├── laser_ultrasound/                # .mat capture and derived features
├── peregrine/                       # coupon features + tensile test
├── fringe/3D_sample_data/           # captured fringes + PUMA reference
├── hm/                              # WLI height maps (Heightmap_*.ASC)
├── xct/vol_gd/                      # 212 DICOM slices
└── phase_unwrap/, pointcloud/, ...  # written by the stages themselves
```

Then ask the system what it can see:

```bash
python -m ammonitor list
```

A leading `!` means a stage declares an input path that does not exist. Nothing runs
with missing data — `ammonitor run` returns exit code 2 instead of producing an empty
result that could be mistaken for a null finding.

---

## 4. Find and run stages

```bash
python -m ammonitor list                     # 35 stages, provenance + data status
python -m ammonitor info 1_acoustic:run_eplf_v12
python -m ammonitor run  1_acoustic:run_eplf_v12
```

`info` prints the stage record: the script path, the docstring summary, every
`data/...` path it touches, whether it draws random numbers, and its provenance.

Run the subset whose results are evidence about the process:

```bash
python -m ammonitor chain measured --out results/chain.json
```

That chain is derived from the registry, not hard-coded: it is exactly the stages
tagged `measured` in the acoustic, laser-ultrasound and measured-analysis groups. It
now includes the five real-data re-analyses in `7_measured_real`, so expect it to run
for several minutes rather than seconds.

### How a stage executes

In a subprocess, with the repository root as working directory, because every script
in `CODE/` `chdir`s there itself and reads `data/...`. Changing that would change what
was run, which a reproduction artefact must not do.

---

## 5. Use the decision layer

### From the shell

```bash
python -m ammonitor bound --a 100 --L 40 --dI-over-sigma 5
```

```json
{"a_um": 100.0, "L_um": 40.0, "x": 2.5, "energy": 3.608,
 "d_prime": 9.50, "pod_bound": 1.0, "voxel_max_um": 66.12,
 "energy_needed_for_target": 0.5207, "repeats_equal_halving_voxel": 64.0}
```

A 100 µm flaw at 40 µm voxels with contrast five times the noise has a deflection of
9.5: detected with probability essentially one. If 90% were enough, 66 µm voxels
would do. Anything coarser and the flaw is outside the bound.

### From Python, volumetric

```python
from ammonitor import decision
e = decision.volumetric_energy(a=100.0, L=40.0)
print(decision.pod(dI=5.0, sigma=1.0, energy=e, alpha=0.01))
req = decision.requirement(100.0, 5.0, 1.0, pod_target=0.9)
print(req.voxel_max, req.energy_needed)
```

### From Python, transient

For an acoustic or laser-ultrasound event the signal energy is just the squared norm
of the expected waveform:

```python
import numpy as np
from ammonitor import decision

template = np.load("template.npy")          # expected burst, 5 000 samples
e = decision.transient_energy(template)
print(decision.pod(1.0, sigma=0.8, energy=e, alpha=0.01))
print(decision.required_sampling(e, sigma=0.8, dI=1.0))
```

The same inequality covers both cases; only `‖s‖²` changes. That is the point of
putting the decision layer in the system rather than in one paper.

A measured example is in `tools/ae_detectability.py`:

```bash
python tools/ae_detectability.py --data-root <path to data> --set D1
```

It takes each class mean of the EPFL set as the expected waveform and the within-class
residual as the noise. Result: `d' ≈ 4.0–4.2`, POD ≈ 0.96 at α = 0.01 — a deflection
of four is a POD of 0.96 and no more, which is why the measurement chain needs
features rather than templates.

---

## 6. Read the provenance

```bash
python -m ammonitor report
```

prints three disjoint lists:

| category | stages | may be cited as |
|---|---|---|
| `measured` | 14 | evidence about the process |
| `simulated` | 9 | evidence about the method only |
| `derived` | 12 | neither; statistics and figures |

The simulated fusion, unwrapping, point-cloud and closed-loop control modules draw
their own trajectories and read no measured capture. Their measured counterparts —
the ones that produced the paper's fusion, unwrapping, height-map, graded-decision
and clutter numbers — are separate stages in `7_measured_real` and are tagged
`measured`. Averaging a simulated result with a measured one into a single "system
accuracy" is exactly what the reporter exists to prevent.

If a number is not under `process_evidence` in `ammonitor report`, do not quote it as
a fact about the manufacturing process.

---

## 7. Add a stage

1. Put the script in the right `CODE/<module>/` directory.
2. Regenerate the registry:

   ```bash
   python tools/scan_stages.py
   ```

   It reads each file's docstring, the `data/...` paths it mentions, and whether it
   draws random numbers, and assigns a provenance tag.

3. Check the classification:

   ```bash
   python -m ammonitor list
   ```

   If the automatic tag is wrong, fix the *source* (the docstring or the path), not
   the JSON — the JSON is generated.

4. `pytest -q`. A test asserts that the scripts on disk and the registry agree, so a
   new stage is covered automatically.

---

## 8. FAQ

**Every stage shows `!`.**
You are in a clone without the datasets. That is the expected state of a fresh
clone — see section 3.

**`run` returns exit code 2.**
The stage declares an input that is absent. Either place the data or pass
`--allow-missing-data` if you know the stage tolerates it (most do not).

**Why do some fusion stages say `simulated` while others say `measured`?**
The simulated ones generate their own sensor streams; they answer "which fusion rule
is better under this model". The measured ones in `7_measured_real` read the Peregrine
coupon table and a tensile test; they answer "what did fusion gain on real coupons".
Both are tagged by scanning the source, not by assertion, so a stage that starts
reading a measured file changes tag on the next registry rebuild.

**Can I trust the accuracies in the paper?**
The stages tagged `measured` run on the six public datasets listed in `data/README.md`;
their numbers are process evidence. The simulated stages are method evidence. The
report keeps them apart so the question has an answer.

**`python -m ammonitor` says "No module named ammonitor".**
`pip install -e .`, or prefix with `PYTHONPATH=src`.

**Does the system need the decision layer to work?**
No. `ammonitor list/run/chain/report` work on the registry alone. The decision layer
(`src/dbound/`) is independent and has its own tests; it is vendored here so a single
clone gives both.

