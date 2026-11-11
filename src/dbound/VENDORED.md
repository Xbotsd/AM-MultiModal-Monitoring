# Vendored copy

`src/dbound/` is a copy of the package at
[github.com/Xbotsd/detectability-bound](https://github.com/Xbotsd/detectability-bound),
vendored so that a single clone of this repository gives both the monitoring system
and the decision layer.

| | |
|---|---|
| upstream | https://github.com/Xbotsd/detectability-bound |
| vendored at commit | `81d99a2` |
| version | 0.1.0 |
| licence | MIT (see the upstream `LICENSE`) |

The copy includes the `dbound` console entry point and the `bound` subcommand
(`python -m dbound bound --a 100 --L 40`), so the decision layer can be exercised
without the monitoring system around it.

The relationship between the two projects — what each owns, which modules and result
files cross the boundary, and the version/DOI pairing — is documented in
[`docs/RELATION_TO_DBOUND.md`](../../docs/RELATION_TO_DBOUND.md).

## Why a copy and not a dependency

A git dependency would require network access at install time and would pin the
system to whatever state upstream happens to be in. A copy makes `pip install -e .`
work offline and keeps the artefact reproducible. The cost is that the two can drift.

## How to sync

```bash
# from a checkout of the upstream repository
git -C ../detectability-bound archive --format=tar HEAD src/dbound | tar -x -C /tmp/dbound
rm -rf src/dbound && cp -r /tmp/dbound/src/dbound src/dbound
git add src/dbound && git commit -m "chore: sync vendored dbound to <commit>"
```

Then update the commit hash in this file and run `pytest -q`.

## What depends on it

Only `ammonitor.decision` and the `bound` subcommand of `ammonitor.cli`. The stage
registry, the pipeline runner and the reporter do not import `dbound`, so the
monitoring system keeps working if the vendored copy is removed.
