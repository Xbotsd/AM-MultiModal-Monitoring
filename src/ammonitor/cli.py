"""Command line: ``python -m ammonitor <command>``.

    list                      every stage, with provenance and data needs
    info <stage>              one stage in detail
    run <stage>               run it (refuses if declared data are absent)
    chain measured            run the chain whose results are process evidence
    report                    the provenance report, as markdown
    bound --a 100 --L 50 ...  the decision layer on the command line
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import decision, pipeline, registry, report


def _print_stages() -> None:
    for s in sorted(registry.load(), key=lambda r: (r.provenance, r.stage)):
        flag = "!" if registry.missing_data(s) else " "
        print(f"{flag} {s.provenance:10s} {s.stage:46s} {s.summary}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ammonitor", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    i = sub.add_parser("info")
    i.add_argument("stage")
    r = sub.add_parser("run")
    r.add_argument("stage")
    r.add_argument("--allow-missing-data", action="store_true")
    c = sub.add_parser("chain")
    c.add_argument("which", choices=["measured"])
    c.add_argument("--out", default=None)
    sub.add_parser("report")

    b = sub.add_parser("bound", help="decision layer")
    b.add_argument("--a", type=float, required=True, help="flaw diameter, um")
    b.add_argument("--L", type=float, required=True, help="voxel/PSF width, um")
    b.add_argument("--dI-over-sigma", type=float, default=5.0)
    b.add_argument("--sigma", type=float, default=1.0)
    b.add_argument("--alpha", type=float, default=0.01)
    b.add_argument("--pod-target", type=float, default=0.9)

    a = p.parse_args(argv)

    if a.cmd == "list":
        _print_stages()
    elif a.cmd == "info":
        s = registry.get(a.stage)
        print(json.dumps({**s.__dict__, "data_paths": list(s.data_paths),
                          "missing_data": registry.missing_data(s)}, indent=1))
    elif a.cmd == "run":
        res = pipeline.run(a.stage, allow_missing_data=a.allow_missing_data)
        print(json.dumps(res.as_dict(), indent=1))
        return 0 if res.ok else 1
    elif a.cmd == "chain":
        stages = pipeline.measured_chain()
        res = pipeline.chain(stages, out=Path(a.out) if a.out else None)
        print(f"{sum(r.ok for r in res)}/{len(res)} stages succeeded")
        return 0 if all(r.ok for r in res) else 1
    elif a.cmd == "report":
        print(report.markdown())
    elif a.cmd == "bound":
        d_i = a.dI_over_sigma * a.sigma
        e = decision.volumetric_energy(a.a, a.L)
        pod = decision.pod(d_i, a.sigma, e, a.alpha)
        req = decision.requirement(a.a, d_i, a.sigma, a.pod_target, a.alpha)
        out = {"a_um": a.a, "L_um": a.L, "x": a.a / a.L,
               "energy": e, "d_prime": decision.dprime(d_i, a.sigma, e),
               "pod_bound": pod,
               "voxel_max_um": req.voxel_max,
               "energy_needed_for_target": req.energy_needed,
               "repeats_equal_halving_voxel": decision.repeats_equivalence(2.0)}
        print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
