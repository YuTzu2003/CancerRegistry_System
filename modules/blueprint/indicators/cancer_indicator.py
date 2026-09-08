"""
口腔癌品質指標
規則設定：欄位名稱可以依實際資料庫或 Excel 欄名調整
"""

from __future__ import annotations

from typing import Any

ORAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "口腔癌病人手術後6週內開始輔助治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "valid_date", "field": "surgery_date"},
                # 依目前表格的新增條件：放射治療開始日期不得為 00000000。
                {"op": "valid_date", "field": "radiation_date"},
                {
                    "op": "any",
                    "rules": [
                        {
                            "op": "date_after",
                            "start_field": "surgery_date",
                            "end_field": "radiation_date",
                        },
                        {
                            "op": "date_after",
                            "start_field": "surgery_date",
                            "end_field": "chemotherapy_date",
                        },
                    ],
                },
            ],
        },
        "numerator": {
            "op": "earliest_after_within",
            "reference_field": "surgery_date",
            "candidate_fields": ["radiation_date", "chemotherapy_date"],
            "min_days": 1,
            "max_days": 42,
        },
    },
    2: {
        "name": "口腔癌病人手術後30天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "equals", "field": "palliative_care", "value": 0},
                {"op": "valid_date", "field": "surgery_date"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "surgery_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 30,
                },
            ],
        },
    },
    3: {
        "name": "口腔癌病人接受放射治療（不含化療）後90天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "greater_than", "field": "radiation_dose", "value": 0},
                {"op": "equals", "field": "chemotherapy_code", "value": 0},
                {"op": "equals", "field": "palliative_care", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "radiation_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 90,
                },
            ],
        },
    },
    4: {
        "name": "口腔癌病人同步化學及放射治療後90天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "greater_than", "field": "radiation_dose", "value": 0},
                {"op": "greater_than", "field": "chemotherapy_code", "value": 0},
                {
                    "op": "not_in",
                    "field": "chemotherapy_code",
                    "values": [82, 83, 85, 86, 87, 88, 99],
                },
                {"op": "valid_date", "field": "chemotherapy_date"},
                {"op": "equals", "field": "palliative_care", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "earliest_date_interval",
                    "start_fields": ["radiation_date", "chemotherapy_date"],
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 90,
                },
            ],
        },
    },
    5: {
        "name": "第一個口腔癌淋巴結病理檢查15顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "sequence_number", "value": 1},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "lymph_nodes_examined",
            "min": 15,
            "max": 90,
        },
    },
    6: {
        "name": "口腔癌根除性手術病理切緣小於4mm的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "histology", "min": 8050, "max": 8086},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "not_in", "field": "margin_distance", "values": [991, 999]},
            ],
        },
        "numerator": {
            "op": "any",
            "rules": [
                {"op": "between", "field": "margin_distance", "min": 0, "max": 39},
                {"op": "equals", "field": "margin_distance", "value": 987},
            ],
        },
    },
}

"""食道癌品質指標
注意：surgical_margin 等欄位包含英文字母，因此使用文字型運算子
"""

from __future__ import annotations

from typing import Any

ESOPHAGEAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "食道癌手術切除標本切除端無殘餘侵襲性癌細胞（R0切除）的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                # 2E、2M 無法轉成整數，本來就不會符合 between；保留此規則以對應規格。
                {"op": "text_not_in", "field": "surgery_code", "values": ["2E", "2M"]},
                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "surgical_margin",
            "values": ["0", "C", "D", "E"],
        },
    },
    2: {
        "name": "食道切除標本淋巴結病理檢查15顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {
                    "op": "text_not_in",
                    "field": "surgical_margin",
                    "values": ["2", "3", "4", "A", "B"],
                },
            ],
        },
        "numerator": {
            "op": "between",
            "field": "lymph_nodes_examined",
            "min": 15,
            "max": 90,
        },
    },
    3: {
        "name": "接受食道切除手術後30天內死亡的比率",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "equals", "field": "palliative_care", "value": 0},
                {"op": "valid_date", "field": "surgery_date"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "survival_status", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "surgery_date",
                    "end_field": "last_contact_date",
                    "min_days": 0,
                    "max_days": 30,
                },
            ],
        },
    },
    4: {
        "name": "指定臨床分期接受食道切除手術前引導性化學及放射治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_equals", "field": "sequence_number", "value": "01"},
                {
                    "op": "any",
                    "rules": [
                        # A：cT4N0M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "clinical_t", "values": ["4"]},
                                {"op": "first_char_in", "field": "clinical_n", "values": ["0"]},
                                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                            ],
                        },
                        # B：cTanyN1-3M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "clinical_n", "values": ["1", "2", "3"]},
                                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                            ],
                        },
                    ],
                },
            ],
        },
        # 分子：放射治療與化學治療日期皆有效，且皆早於手術日期。
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "valid_date", "field": "surgery_date"},
                {"op": "valid_date", "field": "radiation_date"},
                {"op": "valid_date", "field": "chemotherapy_date"},
                {
                    "op": "date_after",
                    "start_field": "radiation_date",
                    "end_field": "surgery_date",
                },
                {
                    "op": "date_after",
                    "start_field": "chemotherapy_date",
                    "end_field": "surgery_date",
                },
            ],
        },
    },
}