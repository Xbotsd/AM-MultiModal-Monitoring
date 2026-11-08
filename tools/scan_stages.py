"""Scan CODE/ and emit a machine-checked stage registry.

Every analysis script in this repository is a research artefact with its own
hard-coded paths.  Rather than rewrite them, the system treats them as stages and
records, for each one, what it reads, what it writes, and — critically — whether
it runs on measured data or on a simulation.  The registry is generated from the
source, so a script cannot be added without the system noticing.

    python tools/scan_stages.py            # writes src/ammonitor/stages.json
"""

from __future__ import annotations

import ast
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODE = ROOT / "CODE"
OUT = ROOT / "src" / "ammonitor" / "stages.json"

DATA_RE = re.compile(r"""["'](data/[^"']+)["']""")
SIM_HINTS = ("sim", "closed_loop", "control_baseline", "offline_diagnosis")
DERIVED_HINTS = ("run_stat", "run_complexity", "run_confusion", "run_feature",
                 "run_figure", "run_roc", "run_tsne", "run_visualization",
                 "make_refs")

MODULES = {
    "1_acoustic": "acoustic emission classification",
    "2_laser_ultrasound": "laser-ultrasound classification",
    "3_fusion": "multi-modal fusion",
    "4_phase_pointcloud": "phase unwrapping and point cloud",
    "5_control": "closed-loop control and edge diagnosis",
    "6_visualization": "statistics and figures",
}

# Default provenance per module.  Path heuristics are not enough: several scripts
# both read and write under data/, and the phase-unwrap stages *generate* the
# deformation field they analyse while writing it into data/phase_unwrap.  The
# module is the reliable signal; the overrides below handle the exceptions.
MODULE_PROVENANCE = {
    "1_acoustic": "measured",          # EPFL acoustic set, read from disk
    "2_laser_ultrasound": "measured",  # Cranfield LUT, read from disk
    "3_fusion": "simulated",           # generates sensor streams
    "4_phase_pointcloud": "simulated", # generates the phase field and the cloud
    "5_control": "simulated",          # generates trajectories
    "6_visualization": "derived",      # statistics and figures on other stages
}

OVERRIDES = {
    # reads X_lu.npy, which is derived from the measured Cranfield data
    "3_fusion:run_sensitivity_full": "measured",
    "run_epfl_cross_subset": "measured",
    "make_refs": "derived",
}


def _read(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def docstring(path: pathlib.Path) -> str:
    try:
        tree = ast.parse(_read(path))
    except SyntaxError:
        return ""
    d = ast.get_docstring(tree) or ""
    return d.strip().splitlines()[0] if d.strip() else ""


def scan(path: pathlib.Path) -> dict:
    text = _read(path)
    rel = path.relative_to(ROOT).as_posix()
    module_dir = rel.split("/")[1] if rel.count("/") >= 2 else "root"
    name = path.stem

    data_paths = sorted(set(DATA_RE.findall(text)))
    reads = [p for p in data_paths]
    writes_rng = "np.random" in text or "random.seed" in text

    summary = docstring(path)
    stage_id = rel.removeprefix("CODE/").removesuffix(".py").replace("/", ":")
    if stage_id in OVERRIDES:
        provenance = OVERRIDES[stage_id]
    elif any(h in name for h in SIM_HINTS) or any(
            k in summary.lower() for k in ("sim", "仿真", "模拟")):
        provenance = "simulated"
    elif any(h in name for h in DERIVED_HINTS):
        provenance = "derived"
    else:
        provenance = MODULE_PROVENANCE.get(module_dir, "unknown")
    if provenance == "unknown" and writes_rng and not data_paths:
        provenance = "simulated"

    return {
        "stage": stage_id,
        "script": rel,
        "module": MODULES.get(module_dir, module_dir),
        "summary": summary,
        "data_paths": reads,
        "uses_rng": writes_rng,
        "provenance": provenance,
        "python": "python",
    }


def main() -> None:
    entries = [scan(p) for p in sorted(CODE.rglob("*.py"))
               if p.name != "__init__.py"]
    # the registry itself and tooling are not stages
    entries = [e for e in entries if not e["script"].startswith("CODE/tools/")]
    payload = {
        "generated_by": "tools/scan_stages.py",
        "n_stages": len(entries),
        "modules": MODULES,
        "stages": entries,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["provenance"]] = counts.get(e["provenance"], 0) + 1
    print(f"{len(entries)} stages -> {OUT.relative_to(ROOT)}")
    print("provenance:", counts)


if __name__ == "__main__":
    main()


