"""Registry, decision layer and provenance reporting."""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ammonitor import decision, pipeline, registry, report  # noqa: E402


# ---------------------------------------------------------------- registry

def test_every_code_script_is_registered():
    on_disk = {p.relative_to(ROOT).as_posix()
               for p in (ROOT / "CODE").rglob("*.py") if p.name != "__init__.py"}
    registered = {s.script for s in registry.load()}
    assert on_disk == registered, on_disk.symmetric_difference(registered)


def test_registered_scripts_exist():
    for s in registry.load():
        assert s.path.exists(), s.script


def test_provenance_values_are_known():
    for s in registry.load():
        assert s.provenance in registry.PROVENANCE, s.stage


def test_acoustic_core_stages_are_measured():
    """The EPFL acoustic chain must be tagged as process evidence."""
    for s in registry.load():
        if s.stage.startswith("1_acoustic:run_eplf"):
            assert s.provenance == "measured"
        if s.stage.startswith("3_fusion:run_fusion_sim"):
            assert s.provenance == "simulated"


def test_phase_unwrap_is_simulated_not_measured():
    """The phase stages generate the field they analyse; a path heuristic once
    mis-tagged them as measured because they also write into data/."""
    for s in registry.load():
        if s.stage.startswith("4_phase_pointcloud:"):
            assert s.provenance == "simulated", s.stage


def test_provenance_counts_are_the_documented_ones():
    counts = report.provenance_summary()
    assert counts == {"measured": 14, "simulated": 9, "derived": 13}, counts


def test_committed_results_are_present_and_parse():
    """Every result file the figure stage and the manuscript depend on exists.

    The measured stages write into ``results/`` and those files are committed, so a
    clone can read the numbers without the datasets. A missing or unparsable file is
    a broken evidence chain, not a cosmetic issue.
    """
    required = [
        "ae_d1.json", "ae_spectral.json", "acoustic_holdout.json",
        "acoustic_ablation.json", "cv_acoustic.json", "cross_subset_epfl.json",
        "roc_auc.json", "cv_laser_ultrasound.json", "complexity_analysis.json",
        "sensitivity_full.json", "design_rule.json", "decision_real.json",
        "fusion_real.json", "lu_echo.json", "pointcloud_real.json", "unwrap_real.json",
        "xct_clutter.json",
    ]
    for name in required:
        path = ROOT / "results" / name
        assert path.exists(), f"missing result file: {name}"
        json.loads(path.read_text(encoding="utf-8"))


def test_data_readme_covers_every_measured_stage():
    """A measured stage that reads ``data/<dataset>`` must have that dataset
    documented, with its DOI and placement, in ``data/README.md``.

    This is the guard against the drift that mattered most: analysis scripts were
    run on public captures that the repository never mentioned, so the results
    could not be reproduced from the artefact.
    """
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    used = set()
    for s in registry.load():
        if s.provenance != "measured":
            continue
        for path in s.data_paths:
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] == "data":
                used.add("/".join(parts[:2]))
    missing = sorted(p for p in used if p not in readme)
    assert not missing, f"datasets read by measured stages but undocumented: {missing}"


def test_data_readme_covers_all_six_public_sources():
    """The manuscript cites six public sources; the data guide must name each DOI."""
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    for doi in ("10449883", "15190191", "23727492", "22125908", "21285367", "17602110"):
        assert doi in readme, doi


def test_missing_data_detection(tmp_path):
    s = registry.get("1_acoustic:run_eplf_v12")
    assert registry.missing_data(s, root=tmp_path)      # nothing exists there


# ---------------------------------------------------------------- decision

def test_pod_is_monotone_in_energy():
    prev = -1.0
    for e in (0.1, 1.0, 10.0, 100.0):
        v = decision.pod(1.0, 1.0, e, alpha=0.01)
        assert 0.0 <= v <= 1.0 and v >= prev
        prev = v


def test_volumetric_energy_matches_the_bound_module():
    from dbound import bound as bd
    for a, L in ((2.0, 1.0), (10.0, 1.0)):
        assert decision.volumetric_energy(a, L) == pytest.approx(
            bd.energy_at(a / L))


def test_transient_energy_is_the_squared_norm():
    w = np.array([1.0, -2.0, 3.0])
    assert decision.transient_energy(w) == pytest.approx(14.0)


def test_requirement_inverts_the_bound():
    a, d_i, sigma = 100.0, 1.0, 0.25
    req = decision.requirement(a, d_i, sigma, pod_target=0.9, alpha=0.01)
    assert req.voxel_max > 0
    x = a / req.voxel_max
    assert decision.pod(d_i, sigma, decision.volumetric_energy(a, a / x),
                        0.01) == pytest.approx(0.9, abs=0.02)


def test_repeat_equivalence():
    assert decision.repeats_equivalence(2.0) == pytest.approx(64.0)


def test_required_sampling_scales_with_noise():
    lo = decision.required_sampling(1.0, 1.0, 1.0)
    hi = decision.required_sampling(1.0, 2.0, 1.0)
    assert hi > lo


# ---------------------------------------------------------------- pipeline

def test_runner_refuses_when_data_are_absent(tmp_path):
    res = pipeline.run("1_acoustic:run_eplf_v12", root=tmp_path)
    assert res.returncode == 2
    assert res.missing_data


def test_measured_chain_is_non_empty_and_measured():
    names = pipeline.measured_chain()
    assert names
    for n in names:
        assert registry.get(n).provenance == "measured"


# ---------------------------------------------------------------- report

def test_report_states_all_three_categories():
    md = report.markdown()
    for word in ("measured", "simulated", "derived"):
        assert word in md


def test_claims_are_partitioned():
    c = report.claimable()
    assert set(c) == {"process_evidence", "method_evidence", "not_evidence"}
    total = sum(len(v) for v in c.values())
    assert total == len(registry.load())


def test_registry_json_is_regenerable():
    payload = json.loads((ROOT / "src" / "ammonitor" / "stages.json")
                         .read_text(encoding="utf-8"))
    assert payload["n_stages"] == len(registry.load())
