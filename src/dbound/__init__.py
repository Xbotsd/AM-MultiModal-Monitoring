"""dbound — detectability bound for volumetric flaw inspection.

Public API
----------
psf        point spread function, sphere rendering, blur
bound      E(x), d', POD bound, inverse design rule
detectors  matched-filter templates and reference detectors
realdata   DICOM loading, noise / PSF / clutter estimation, manifests.

The package separates two things that are easy to confuse:

* the *geometry* of detectability, which is analytic (``bound.E``) and universal;
* the *level*, which on real data must be measured (``realdata.kappa``).

Every empirical number produced by this package comes from the public XCT stack
identified in ``data/manifest.json``.  The only synthetic content is the exact
truth used to check the algebra of Propositions 1 and 2; it is never used as
study data.
"""

__version__ = "0.1.0"

from . import bound, detectors, psf, realdata  # noqa: F401

__all__ = ["bound", "detectors", "psf", "realdata", "__version__"]

