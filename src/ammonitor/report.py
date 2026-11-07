"""Reporting: what the system contains, and what may be claimed from it.

The reporter will not merge provenance categories.  A single "system accuracy"
that averages a measured acoustic result with a simulated fusion result is exactly
the kind of number this module exists to prevent.
"""

from __future__ import annotations

from . import registry


def stage_table() -> str:
    rows = ["| provenance | stage | summary |", "|---|---|---|"]
    for s in sorted(registry.load(), key=lambda r: (r.provenance, r.stage)):
        rows.append(f"| `{s.provenance}` | `{s.stage}` | {s.summary or '—'} |")
    return "\n".join(rows)


def provenance_summary() -> dict:
    out: dict[str, int] = {}
    for s in registry.load():
        out[s.provenance] = out.get(s.provenance, 0) + 1
    return out


def claimable() -> dict:
    """Which stages may be cited as evidence about the process itself."""
    return {
        "process_evidence": [s.stage for s in registry.by_provenance("measured")],
        "method_evidence": [s.stage for s in registry.by_provenance("simulated")],
        "not_evidence": [s.stage for s in registry.by_provenance("derived")],
    }


def markdown() -> str:
    counts = provenance_summary()
    lines = ["# System report", "",
             "## Provenance of stages", "",
             "| category | stages | may be cited as |",
             "|---|---|---|",
             f"| measured | {counts.get('measured', 0)} | evidence about the process |",
             f"| simulated | {counts.get('simulated', 0)} | evidence about the method only |",
             f"| derived | {counts.get('derived', 0)} | neither; statistics and figures |",
             "",
             "The decision layer (`ammonitor.decision`) applies to both measured and",
             "simulated stages, because it is a statement about sensing, not about a",
             "particular model.", "",
             stage_table()]
    return "\n".join(lines)
