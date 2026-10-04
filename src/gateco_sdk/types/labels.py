"""Label vocabularies (1.13.0; cold-run findings #10, #12, #13).

The server accepts exactly these values for ``classification`` and ``sensitivity``
and answers 422 to anything else. Until 1.13.0 the SDK typed both as ``str``, so
the vocabulary was discoverable only in the web docs. ``Literal`` types give
editors completion and type checkers an error before the request is sent.

Classification orders data by who may see it; sensitivity by the harm of a leak.
Policy conditions compare them with ``lte``/``gte`` in the order listed here
(``public < internal < confidential < restricted``, ``low < medium < high < critical``).
"""

from __future__ import annotations

from typing import Literal, get_args

Classification = Literal["public", "internal", "confidential", "restricted"]
"""Who may see a resource, least to most restricted."""

Sensitivity = Literal["low", "medium", "high", "critical"]
"""Harm if the resource leaks, least to most severe."""

CLASSIFICATIONS: tuple[str, ...] = get_args(Classification)
SENSITIVITIES: tuple[str, ...] = get_args(Sensitivity)

__all__ = ["CLASSIFICATIONS", "SENSITIVITIES", "Classification", "Sensitivity"]
