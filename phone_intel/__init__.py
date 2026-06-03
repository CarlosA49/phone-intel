"""phone_intel — legitimate phone-number intelligence.

Real, number-derived data only (country, region of registration, carrier,
line type, timezone, validity). No owner identification, no live person
tracking — by design.
"""
from .core import lookup, Intel

__version__ = "3.0.0"
__all__ = ["lookup", "Intel", "__version__"]
