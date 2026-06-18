"""Code-first SDK front end — decorate handlers, then ``synth()``.

The lightest of the three consumption models: a Data Scientist annotates plain
handler functions (:func:`function`, :func:`scheduled`, :data:`api`) and calls
:func:`synth` from a two-line ``app.py``. All three front ends converge on the
same :func:`~paved_cdk.service.build_service`, so intent maps to identical
governed resources.
"""

from .decorators import api, function, scheduled
from .synth import synth

__all__ = ["synth", "function", "scheduled", "api"]
