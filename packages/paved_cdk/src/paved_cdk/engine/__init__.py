"""Declarative consumption variant - a YAML manifest in, a ServiceSpec out.

The :func:`paved_cdk.engine.manifest.load` reader turns a ``service.yaml`` (plus
auto-discovered ``notebooks/*.ipynb``) into a :class:`paved_cdk.service.ServiceSpec`,
and :func:`paved_cdk.engine.synth.main` is the ``paved-cdk-synth`` console script
that a consumer's ``cdk.json`` points at - so a declarative consumer ships no Python.
"""
