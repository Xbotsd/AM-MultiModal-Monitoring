"""Running stages, with the data check and the provenance record kept honest.

A stage is executed in a subprocess with the repository root as working
directory, because every script in ``CODE/`` chdirs there itself and reads
``data/...``.  Changing that would rewrite research code that produced published
figures; wrapping it does not.

The runner refuses to start a stage whose declared input data are absent, so a
missing dataset fails loudly instead of producing a silently empty result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from . import registry


@dataclass
class StageResult:
    stage: str
    provenance: str
    returncode: int
    seconds: float
    missing_data: list[str]
    tail: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def as_dict(self) -> dict:
        return asdict(self)


def run(stage: str, allow_missing_data: bool = False, timeout: int | None = None,
        root: Path | None = None) -> StageResult:
    s = registry.get(stage)
    root = root or registry._ROOT
    missing = registry.missing_data(s, root)
    if missing and not allow_missing_data:
        return StageResult(s.stage, s.provenance, 2, 0.0, missing,
                           "refused: input data absent (use --allow-missing-data)")
    t0 = time.time()
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run([sys.executable, s.script], cwd=str(root),
                          capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace", env=env)
    dt = time.time() - t0
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-8:])
    return StageResult(s.stage, s.provenance, proc.returncode, dt, missing, tail)


def chain(stages: list[str], stop_on_failure: bool = True,
          out: Path | None = None, **kw) -> list[StageResult]:
    results: list[StageResult] = []
    for name in stages:
        r = run(name, **kw)
        results.append(r)
        if not r.ok and stop_on_failure:
            break
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([r.as_dict() for r in results], indent=1),
                       encoding="utf-8")
    return results


def measured_chain() -> list[str]:
    """A chain made only of stages that read measured data.

    This is the subset whose results say something about the process rather than
    about the method.
    """
    order = ["1_acoustic", "2_laser_ultrasound", "4_phase_pointcloud", "7_measured_real"]
    out = []
    for s in registry.load():
        if s.provenance != "measured":
            continue
        if any(s.stage.startswith(p) for p in order):
            out.append(s.stage)
    return out

