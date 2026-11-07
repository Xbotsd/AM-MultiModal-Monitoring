"""ammonitor — integrated multi-modal in-situ monitoring for metal additive manufacturing.

The system has two halves that are usually kept apart:

* a **measurement chain** — acoustic emission, laser ultrasound, phase/point-cloud,
  fusion and control — which classifies process state from sensor data;
* a **decision layer** — a closed-form bound on what any detector could possibly
  achieve given the sensing chain, and the inverse rule that says what sensing
  configuration a target detection probability requires.

The second half is the addition: it does not compete with the classifiers, it
states their ceiling and their cost.

Provenance is a first-class property.  Every stage declares whether it runs on
measured data, on a simulation, or on results derived from the other two, and the
reporter refuses to aggregate across categories silently.  See
``docs/PROVENANCE.md``.
"""

__version__ = "1.0.0"

from . import decision, pipeline, registry, report  # noqa: F401

__all__ = ["decision", "pipeline", "registry", "report", "__version__"]
