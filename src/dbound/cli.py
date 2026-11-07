"""Command line entry point: ``python -m dbound <command>``."""

from __future__ import annotations

import argparse
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
