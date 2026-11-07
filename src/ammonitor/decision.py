"""Decision layer: what any detector could achieve, and what it would cost.

The classifier stages in ``CODE/`` answer "how well does this model do".  This
module answers the prior question: given the sensing chain, what is the ceiling?
Both are needed.  A 97% accuracy means nothing if the flaws it misses are below
the resolution limit, and a design rule means nothing without knowing which
detector class it applies to.

One bound covers both modalities in this system.  For a known signal ``s`` in
additive noise of standard deviation ``sigma``, the matched-filter deflection is

    d' = sqrt( ||s||^2 ) / sigma

and no detector can exceed POD = Phi( d' - z_{1-alpha} ).  What changes between
modalities is only how ``||s||^2`` is produced:

* **volumetric** (X-ray CT, point cloud): the flaw is blurred by the point spread
  function, so the energy is ``E(a/L)`` and grows as the cube of the flaw size
  below the voxel size, as the 3/2 power above it;
* **transient** (acoustic emission, laser ultrasound): the flaw is an event, so
  the energy is simply the squared norm of the expected waveform, and it grows
  with the number of samples the event occupies.

The consequence for the monitoring system is the interesting one: in the
volumetric case resolution dominates dose, whereas in the transient case the
bandwidth and the integration window dominate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from dbound import bound as _bound


def _ndtr(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def z_from_p(p: float) -> float:
    return _bound.z_from_p(p)


def dprime(dI: float, sigma: float, energy: float, n_looks: int = 1) -> float:
    """Deflection for a known signal of squared norm ``energy``."""
    return float((dI / sigma) * math.sqrt(energy * n_looks))


def pod(dI: float, sigma: float, energy: float, alpha: float = 0.01,
        n_looks: int = 1) -> float:
    """Upper bound on the probability of detection."""
    return _ndtr(dprime(dI, sigma, energy, n_looks) - z_from_p(1.0 - alpha))


# --------------------------------------------------------------------------
# signal energy, per modality
# --------------------------------------------------------------------------

def volumetric_energy(a: float, L: float) -> float:
    """||blur(sphere)||^2 for a flaw of diameter ``a`` and PSF width ``L``."""
    return _bound.energy_at(max(a / L, _bound.X_MIN))


def transient_energy(waveform: np.ndarray) -> float:
    """Squared norm of an expected event waveform.

    This is what the acoustic and laser-ultrasound channels contribute: the
    matched filter sees the whole transient, so a longer or higher-amplitude
    event buys energy, exactly as a larger flaw does in the volumetric case.
    """
    w = np.asarray(waveform, dtype=float)
    return float((w * w).sum())


@dataclass
class Requirement:
    voxel_max: float          # volumetric: largest admissible voxel size
    x_star: float             # a/L at which the target is met
    energy_needed: float      # transient: smallest admissible signal energy


def requirement(a: float, dI: float, sigma: float, pod_target: float = 0.9,
                alpha: float = 0.01, n_looks: int = 1) -> Requirement:
    """Invert the bound: the voxel size and the energy a target POD demands."""
    z_req = z_from_p(pod_target) + z_from_p(1.0 - alpha)
    energy_needed = (z_req * sigma / (dI * math.sqrt(n_looks))) ** 2
    req = _bound.required_voxel(a, dI, sigma, pod_target, alpha, n_looks)
    return Requirement(req.voxel_max, req.x_star, float(energy_needed))


def required_sampling(min_energy: float, sigma: float, dI: float,
                      pod_target: float = 0.9, alpha: float = 0.01,
                      sample_energy: float = 1.0) -> float:
    """Transient case: how many samples of a unit template are needed.

    ``sample_energy`` is the squared norm contributed by one sample of the
    expected waveform, so the answer is the number of samples the event must
    occupy.
    """
    z_req = z_from_p(pod_target) + z_from_p(1.0 - alpha)
    need = (z_req * sigma / dI) ** 2
    return float(need / max(sample_energy, 1e-30))


def knee() -> list[tuple[float, float]]:
    """The d' exponent against a/L, for the report figure."""
    xs, es = _bound.energy_curve()
    return [(float(x), 0.5 * _bound.local_dprime_exponent(float(x))) for x in xs]


def repeats_equivalence(ratio: float) -> float:
    """Volumetric: repeat looks that equal shrinking the voxel by ``ratio``."""
    return _bound.repeats_to_match_resolution(ratio)
