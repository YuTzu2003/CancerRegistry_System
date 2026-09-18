import importlib.util
from pathlib import Path

import pandas as pd

from modules.blueprint.indicators.analysis import _year_mask
from modules.blueprint.indicators.rule import parse_date


VALIDATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "modules"
    / "blueprint"
    / "clean"
    / "rules"
    / "validate.py"
)
VALIDATE_SPEC = importlib.util.spec_from_file_location("clean_validate_rules", VALIDATE_PATH)
VALIDATE_MODULE = importlib.util.module_from_spec(VALIDATE_SPEC)
VALIDATE_SPEC.loader.exec_module(VALIDATE_MODULE)
compare_cancer_date = VALIDATE_MODULE.compare_cancer_date
validate_cell = VALIDATE_MODULE.validate_cell


DATE_RULE = {
    "length": 8,
    "digit": True,
    "is_date": "%Y%m%d",
}


def test_date_validation_accepts_unknown_day_or_month():
    assert validate_cell("20230399", DATE_RULE)
    assert validate_cell("20239999", DATE_RULE)
    assert validate_cell("20239915", DATE_RULE)
    assert not validate_cell("20231399", DATE_RULE)


def test_date_comparison_uses_available_precision():
    assert compare_cancer_date("20239999", "20241231") is True
    assert compare_cancer_date("20249999", "20230101") is False
    assert compare_cancer_date("20240399", "20240301") is True
    assert compare_cancer_date("20240499", "20240331") is False


def test_indicator_year_filter_accepts_partial_registry_dates():
    frame = pd.DataFrame(
        {
            "最初診斷日期": [
                "2023/99/99",
                "2024/03/99",
                "2017/99/99",
                "99999999",
            ]
        }
    )

    mask, error = _year_mask(frame, 2023, 2024)

    assert error == ""
    assert mask.tolist() == [True, True, False, False]


def test_indicator_day_calculation_treats_unknown_day_as_first_day():
    assert parse_date("20240399").isoformat() == "2024-03-01"
    assert parse_date("2024/03/99").isoformat() == "2024-03-01"
    assert parse_date("20249999") is None
