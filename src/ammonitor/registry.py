"""The stage registry: what the system can run, on what, and from where.

``stages.json`` is generated from the source by ``tools/scan_stages.py``, so a
script cannot be added to ``CODE/`` without appearing here.  The provenance tag is
the important field:

``measured``   reads a measured public dataset (EPFL acoustic, Cranfield laser
               ultrasound, phase / point-cloud captures)
``simulated``  generates its own data; results are about the method, not the
               process
``derived``    statistics or figures computed on other stages' output
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_STAGES = _HERE / "stages.json"

PROVENANCE = ("measured", "simulated", "derived")


@dataclass(frozen=True)
class Stage:
    stage: str
    script: str
    module: str
    summary: str
    data_paths: tuple[str, ...]
    uses_rng: bool
    provenance: str
    python: str

    @property
    def path(self) -> Path:
        return _ROOT / self.script


def load() -> list[Stage]:
    payload = json.loads(_STAGES.read_text(encoding="utf-8"))
    return [Stage(stage=s["stage"], script=s["script"], module=s["module"],
                  summary=s["summary"], data_paths=tuple(s["data_paths"]),
                  uses_rng=s["uses_rng"], provenance=s["provenance"],
                  python=s["python"]) for s in payload["stages"]]


def by_provenance(kind: str) -> list[Stage]:
    if kind not in PROVENANCE:
        raise ValueError(f"provenance must be one of {PROVENANCE}")
    return [s for s in load() if s.provenance == kind]


def get(stage: str) -> Stage:
    for s in load():
        if s.stage == stage or s.script.endswith(stage + ".py"):
            return s
    raise KeyError(f"no stage {stage!r}; run `ammonitor list`")


def modules() -> dict[str, list[Stage]]:
    out: dict[str, list[Stage]] = {}
    for s in load():
        out.setdefault(s.module, []).append(s)
    return out


def missing_data(stage: Stage, root: Path | None = None) -> list[str]:
    """Data paths a stage declares but that are absent from the working tree."""
    root = root or _ROOT
    return [p for p in stage.data_paths if not (root / p).exists()]
