"""Display metadata for configured cancer-indicator rules.

The executable numerator and denominator logic lives in ``cancer_indicator``;
the explanatory text shown in the UI lives in the database.
"""

import logging
import re

from modules.blueprint.indicators.cancer_indicator import INDICATOR_RULES

# Optional in-code fallback used when the database is temporarily unavailable.
INDICATOR_DEFINITIONS = {}

LOGGER = logging.getLogger(__name__)


def _normalize_cancer_key(value):
    """Make database keys such as ``Cervix Uteri`` match ``Cervix_Uteri``."""
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _database_metadata(cancer_key):
    # Imported lazily to avoid the services package loading indicators ->
    # analysis -> this module while services itself is still initializing.
    from modules.services.db import get_conn

    connection = None
    try:
        connection = get_conn()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT cancer_group_key,
                   indicator_no,
                   selection_reason,
                   numerator_definition,
                   denominator_definition
            FROM dbo.indicator_definition_metadata
            """
        )
        wanted_key = _normalize_cancer_key(cancer_key)
        return {
            int(row[1]): {
                "selection_reason": str(row[2] or ""),
                "numerator_definition": str(row[3] or ""),
                "denominator_definition": str(row[4] or ""),
            }
            for row in cursor.fetchall()
            if _normalize_cancer_key(row[0]) == wanted_key and row[1] is not None
        }
    except Exception:
        LOGGER.exception("Unable to load indicator definitions for %s", cancer_key)
        return {}
    finally:
        if connection is not None:
            connection.close()


def get_indicator_definitions(cancer_key):
    key = str(cancer_key or "")
    fallback_metadata = {
        int(item["id"]): item
        for item in INDICATOR_DEFINITIONS.get(key, [])
        if item.get("id") is not None
    }
    configured_metadata = {**fallback_metadata, **_database_metadata(key)}
    return [
        {
            "id": indicator_number,
            "direction": rule["type"],
            "name": rule["name"],
            "selection_reason": configured_metadata.get(indicator_number, {}).get("selection_reason", ""),
            "numerator_definition": configured_metadata.get(indicator_number, {}).get("numerator_definition", ""),
            "denominator_definition": configured_metadata.get(indicator_number, {}).get("denominator_definition", ""),
        }
        for indicator_number, rule in INDICATOR_RULES.get(key, {}).items()
    ]
