"""Package version utilities.

This module exists so multiple modules (including app.py) can read the version
without import cycles.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

# Used only when running from source without installed package metadata.
__fallback_version__ = "0.1.2"

try:
    __version__ = _pkg_version("h4ckath0n")
except PackageNotFoundError:
    __version__ = __fallback_version__

__all__ = ["__version__", "__fallback_version__"]
