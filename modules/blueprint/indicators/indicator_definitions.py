"""Configured cancer-indicator definitions.

Cancer-specific definitions are intentionally added only after their numerator
and denominator rules have been confirmed.
"""

INDICATOR_DEFINITIONS = {}


def get_indicator_definitions(cancer_key):
    return INDICATOR_DEFINITIONS.get(str(cancer_key or ""), [])