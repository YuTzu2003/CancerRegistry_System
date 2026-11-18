"""Shared applicability rules for specialised cancer staging systems.

The stage calculation itself remains the authority for whether a record has a
valid stage.  These helpers only answer which cancer-picker selections may
request each specialised system (FIGO, BCLC, etc.).
"""

from __future__ import annotations

from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES


# Keep these keys at the most specific clinically applicable level.  Parent and
# child selections are resolved from CANCER_GROUP_RULES below instead of being
# copied into every caller.
STAGE_SYSTEM_CANCER_KEYS = {
    "FIGO": {"Cervix_Uteri", "Corpus_Uteri", "Ovary"},
    "MAC": {"Colon", "Rectum"},
    "BCLC": {"Liver"},
    "SCLC": {
        "Trachea", "Lung_and_Bronchus", "Small_cell_carcinoma",
        "Adenocarcinoma", "Squamous_cell_carcinoma",
    },
    "DSS": {"Plasma_cell_neoplasms"},
    "DRE": {"Prostate"},
    "Breast Cancer Prognostic Stage": {"Breast"},
    "Binet": {"CLL"},
}


def _parent_keys():
    """Return every picker key's direct parents, including its cancer group."""
    parents = {}
    for group in CANCER_GROUP_RULES:
        group_key = group["key"]
        for subgroup in group.get("subgroups", []):
            subgroup_key = subgroup["key"]
            parents.setdefault(subgroup_key, set()).add(group_key)
            for child_key in subgroup.get("child_keys", []):
                parents.setdefault(child_key, set()).add(subgroup_key)
    return parents


_PARENT_KEYS = _parent_keys()


def ancestor_cancer_keys(cancer_key):
    """Return all parent picker keys for ``cancer_key`` (nearest first)."""
    pending = list(_PARENT_KEYS.get(str(cancer_key or "").strip(), set()))
    ancestors, seen = [], set()
    while pending:
        key = pending.pop(0)
        if key in seen:
            continue
        seen.add(key)
        ancestors.append(key)
        pending.extend(_PARENT_KEYS.get(key, set()))
    return ancestors


def cancer_key_applies_to_stage_system(system, cancer_key):
    """Whether one picker key can contain records for ``system``.

    It accepts both a specialised system's direct key and a parent selection,
    such as ``Colon_and_Rectum_Anus`` for MAC or ``Breast`` for breast
    prognostic stage.  It also supports a selected child of an eligible group,
    such as ``Cervix_invasive`` for FIGO.
    """
    key = str(cancer_key or "").strip()
    eligible = STAGE_SYSTEM_CANCER_KEYS.get(system)
    if not eligible or not key or key == "All_Cancers":
        return True
    if key in eligible or bool(set(ancestor_cancer_keys(key)) & eligible):
        return True
    # A user may choose a parent group while the specialised system is assigned
    # to one of its child subgroups.
    return any(key in ancestor_cancer_keys(eligible_key) for eligible_key in eligible)


def stage_system_applies_to_selection(system, cancer_keys):
    """Whether any selected picker key can contain records for ``system``."""
    keys = [str(key).strip() for key in (cancer_keys or []) if str(key or "").strip()]
    return not keys or any(cancer_key_applies_to_stage_system(system, key) for key in keys)
