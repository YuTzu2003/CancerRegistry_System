from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from modules.blueprint.dashboard.definition.cancer_grouping import classify_cancer_group
from modules.blueprint.dashboard.definition.cancer_group_rules import CANCER_GROUP_RULES
from modules.blueprint.indicators.cancer_indicator import (
    BREAST_CANCER_RULES,
    CERVICAL_CANCER_RULES,
    COLON_RECTUM_CANCER_RULES,
    ESOPHAGEAL_CANCER_RULES,
    GASTRIC_CANCER_RULES,
    LIVER_CANCER_RULES,
    LUNG_CANCER_RULES,
    ORAL_CANCER_RULES,
    OWNED_CANCER_RULES,
    PANCREATIC_CANCER_RULES,
)
from modules.blueprint.indicators.exclusion_rules import _clean_code, _find_column

@dataclass(frozen=True)
class CancerSpec:
    rules: dict
    selector: str = "site_histology"
    site_codes: frozenset[str] = frozenset()
    site_prefixes: tuple[str, ...] = ()
    histology_include: frozenset[str] = frozenset()
    histology_exclude: frozenset[str] = frozenset()
    histology_exclude_ranges: tuple[tuple[int, int], ...] = ()
    require_case_class: bool = False
    group_key: str = ""

SOLID_TUMOR_EXCLUDED_HISTOLOGY = frozenset({"9140"})
SOLID_TUMOR_EXCLUDED_RANGES = ((9590, 9993),)

# Add a cancer type here with its rule declaration and case-selection criteria.
CANCER_SPECS: dict[str, CancerSpec] = {
    "Oral_Cavity": CancerSpec(ORAL_CANCER_RULES, selector="group", group_key="Oral_Cavity"),
    "Esophagus": CancerSpec(ESOPHAGEAL_CANCER_RULES, selector="group", group_key="Esophagus"),
    "Stomach": CancerSpec(
        GASTRIC_CANCER_RULES,
        site_codes=frozenset({"C160", "C161", "C162", "C163", "C164", "C165", "C166", "C168", "C169"}),
        histology_include=frozenset({"8140", "8144", "8145", "8148", "8210", "8211", "8255", "8260", "8263", "8480", "8481", "8490", "8550", "8576"}),
    ),
    "Pancreas": CancerSpec(
        PANCREATIC_CANCER_RULES,
        site_codes=frozenset({"C250", "C251", "C252", "C253", "C254", "C257", "C258", "C259"}),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Colon_Rectum": CancerSpec(
        COLON_RECTUM_CANCER_RULES,
        site_prefixes=("C18", "C19", "C20"),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
    ),
    "Liver": CancerSpec(
        LIVER_CANCER_RULES,
        site_codes=frozenset({"C220"}),
        histology_include=frozenset({"8170", "8171", "8172", "8173", "8174", "8175"}),
    ),
    "Breast": CancerSpec(
        BREAST_CANCER_RULES,
        site_prefixes=("C50",),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Lung": CancerSpec(
        LUNG_CANCER_RULES,
        site_prefixes=("C34",),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Cervix_Uteri": CancerSpec(
        CERVICAL_CANCER_RULES,
        site_prefixes=("C53",),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Corpus_Uteri": CancerSpec(
        OWNED_CANCER_RULES["Corpus_Uteri"],
        site_codes=frozenset({"C540", "C541", "C543", "C548", "C549"}),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Ovary": CancerSpec(
        OWNED_CANCER_RULES["Ovary"],
        site_codes=frozenset({"C569"}),
        histology_exclude=SOLID_TUMOR_EXCLUDED_HISTOLOGY,
        histology_exclude_ranges=SOLID_TUMOR_EXCLUDED_RANGES,
        require_case_class=True,
    ),
    "Prostate": CancerSpec(
        OWNED_CANCER_RULES["Prostate"],
        site_codes=frozenset({"C619"}),
        histology_include=frozenset({"8140", "8141", "8201", "8255", "8500", "8550", "8551", "8552"}),
    ),
    "Bladder": CancerSpec(
        OWNED_CANCER_RULES["Bladder"],
        site_codes=frozenset({"C679"}),
        histology_include=frozenset({"8020", "8031", "8082", "8120", "8122", "8130", "8131"}),
        require_case_class=True,
    ),
}


def get_indicator_rules(cancer_key: str) -> dict:
    spec = CANCER_SPECS.get(str(cancer_key or ""))
    return spec.rules if spec else {}


def _site(value) -> str:
    return _clean_code(value).upper().replace(".", "")

def _histology(value) -> str:
    code = _clean_code(value)
    return code.zfill(4) if code.isdigit() and len(code) < 4 else code

def _group_mask(frame: pd.DataFrame, spec: CancerSpec) -> pd.Series:
    site_column = _find_column(frame.columns, "2.6", ("原發部位", "site"))
    histology_column = _find_column(frame.columns, "2.8", ("組織型態", "hist"))
    behavior_column = _find_column(frame.columns, "2.9", ("性態碼", "behavior"))
    if not site_column or not histology_column:
        return pd.Series(False, index=frame.index)

    def matches(row) -> bool:
        cancer = classify_cancer_group(
            row.get(site_column, ""),
            row.get(histology_column, ""),
            CANCER_GROUP_RULES,
            behavior=row.get(behavior_column, "") if behavior_column else None,
        )
        if not cancer:
            return False
        keys = {cancer.get("group_key"), cancer.get("subgroup_key"), *cancer.get("ancestor_subgroup_keys", [])}
        return spec.group_key in keys

    return frame.apply(matches, axis=1).fillna(False)

def cancer_case_mask(frame: pd.DataFrame, cancer_key: str) -> pd.Series:
    """Return cases eligible for the cancer type before shared exclusions."""
    spec = CANCER_SPECS.get(str(cancer_key or ""))
    if spec is None:
        return pd.Series(False, index=frame.index)
    if spec.selector == "group":
        return _group_mask(frame, spec)

    site_column = _find_column(frame.columns, "2.6", ("原發部位", "site"))
    histology_column = _find_column(frame.columns, "2.8", ("組織型態", "hist"))
    case_class_column = _find_column(frame.columns, "2.3", ("個案分類", "class"))
    if not site_column or not histology_column or (spec.require_case_class and not case_class_column):
        return pd.Series(False, index=frame.index)

    sites = frame[site_column].map(_site)
    histology = frame[histology_column].map(_histology)
    mask = sites.isin(spec.site_codes)
    if spec.site_prefixes:
        mask |= sites.str.startswith(spec.site_prefixes)
    if spec.require_case_class:
        mask &= frame[case_class_column].map(_clean_code).isin({"1", "2"})
    if spec.histology_include:
        return (mask & histology.isin(spec.histology_include)).fillna(False)

    if spec.histology_exclude:
        mask &= ~histology.isin(spec.histology_exclude)
    if spec.histology_exclude_ranges:
        histology_number = pd.to_numeric(histology, errors="coerce")
        for start, end in spec.histology_exclude_ranges:
            mask &= ~histology_number.between(start, end, inclusive="both")
    return mask.fillna(False)