"""Command line entry point: ``python -m dbound <command>``."""

from __future__ import annotations

import argparse
import math
import json
import pathlib
import sys

from . import bound, experiments, realdata


def _dump(obj, path: pathlib.Path | None = None) -> None:
    text = json.dumps(obj, indent=1)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    else:
        print(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dbound", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("verify", help="check Propositions 1-2 and bound tightness")

    for name in ("measure", "ablate", "compare", "manifest"):
        q = sub.add_parser(name)
        q.add_argument("folder")
        if name == "ablate":
            q.add_argument("--a", type=float, default=8.0)
        if name == "compare":
            q.add_argument("--a", type=float, default=4.0)
            q.add_argument("--ratio", type=float, default=8.0)
        q.add_argument("--out", default=None)

    r = sub.add_parser("all", help="run everything on the local data trees")
    r.add_argument("--data-root", default="data")
    r.add_argument("--out", default="results")

    b = sub.add_parser("bound", help="one bound from the command line, no data")
    b.add_argument("--a", type=float, required=True, help="flaw diameter")
    b.add_argument("--L", type=float, required=True, help="voxel or PSF width")
    b.add_argument("--dI-over-sigma", type=float, default=5.0)
    b.add_argument("--alpha", type=float, default=0.01)
    b.add_argument("--pod-target", type=float, default=0.9)

    a = p.parse_args(argv)

    if a.cmd == "verify":
        _dump(experiments.check_algebra())
    elif a.cmd == "manifest":
        files = realdata.manifest(a.folder)
        dest = pathlib.Path(a.out) if a.out else None
        _dump({"folder": a.folder, "files": files}, dest)
    elif a.cmd == "measure":
        out = experiments.measure_group(a.folder)
        _dump(out, pathlib.Path(a.out) if a.out else None)
    elif a.cmd == "ablate":
        out = experiments.ablate(a.folder, a=float(a.a))
        _dump(out, pathlib.Path(a.out) if a.out else None)
    elif a.cmd == "compare":
        out = experiments.compare_detectors(a.folder, a=float(a.a),
                                            ratio=float(a.ratio))
        _dump(out, pathlib.Path(a.out) if a.out else None)
    elif a.cmd == "all":
        experiments.run_all(a.data_root, a.out)
        print(f"results written to {a.out}")
    elif a.cmd == "bound":
        x = a.a / a.L
        e = bound.energy_at(max(x, bound.X_MIN))
        req = bound.required_voxel(a.a, a.dI_over_sigma, 1.0, a.pod_target, a.alpha)
        _dump({
            "a": a.a, "L": a.L, "x": x,
            "dprime": a.dI_over_sigma * math.sqrt(e),
            "pod_bound": bound.pod_bound(a.dI_over_sigma, 1.0, x, a.alpha),
            "voxel_max_for_target": req.voxel_max,
            "energy_needed_for_target": (bound.z_from_p(a.pod_target)
                                         + bound.z_from_p(1.0 - a.alpha)) ** 2
                                        / a.dI_over_sigma ** 2,
            "repeats_equal_halving_voxel": bound.repeats_to_match_resolution(2.0),
        })
    return 0


if __name__ == "__main__":
    sys.exit(main())

