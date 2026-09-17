from __future__ import annotations
from typing import Any


def _solid_histology_exclusion_rule() -> dict[str, Any]:
    """排除工作表共同指定的 9140 與 9590-9993 組織型態。"""
    return {
        "op": "not",
        "rule": {
            "op": "any",
            "rules": [
                {"op": "equals", "field": "histology", "value": 9140},
                {"op": "between", "field": "histology", "min": 9590, "max": 9993},
            ],
        },
    }


# 癌別層級基礎收案規則。必須先符合此處條件，才執行個別指標分母與分子。
CANCER_BASE_RULES: dict[str, dict[str, Any]] = {
    "Oral_Cavity": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_prefix_in", "field": "site", "values": ["C00", "C02", "C03", "C04", "C05", "C06"]},
            {
                "op": "not",
                "rule": {"op": "code_in", "field": "site", "values": ["C024", "C051", "C052"]},
            },
            _solid_histology_exclusion_rule(),
        ],
    },
    "Esophagus": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_prefix_in", "field": "site", "values": ["C15"]},
            _solid_histology_exclusion_rule(),
        ],
    },
    "Pancreas": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {
                "op": "code_in",
                "field": "site",
                "values": ["C250", "C251", "C252", "C253", "C254", "C257", "C258", "C259"],
            },
            _solid_histology_exclusion_rule(),
        ],
    },
    "Cervix_Uteri": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_prefix_in", "field": "site", "values": ["C53"]},
            _solid_histology_exclusion_rule(),
        ],
    },
    "Lung": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_prefix_in", "field": "site", "values": ["C34"]},
            _solid_histology_exclusion_rule(),
        ],
    },
    "Breast": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_prefix_in", "field": "site", "values": ["C50"]},
            _solid_histology_exclusion_rule(),
        ],
    },
    "Corpus_Uteri": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {
                "op": "code_in",
                "field": "site",
                "values": ["C540", "C541", "C543", "C548", "C549"],
            },
            _solid_histology_exclusion_rule(),
        ],
    },
    "Ovary": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_in", "field": "site", "values": ["C569"]},
            _solid_histology_exclusion_rule(),
        ],
    },
    "Prostate": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_in", "field": "site", "values": ["C619"]},
            {
                "op": "text_in",
                "field": "histology",
                "values": ["8140", "8141", "8201", "8255", "8500", "8550", "8551", "8552"],
            },
            {"op": "text_equals", "field": "behavior", "value": "3"},
        ],
    },
    "Bladder": {
        "op": "all",
        "rules": [
            {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            {"op": "code_in", "field": "site", "values": ["C679"]},
            {
                "op": "text_in",
                "field": "histology",
                "values": ["8020", "8031", "8082", "8120", "8122", "8130", "8131"],
            },
        ],
    },
}

# 口腔癌指標
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

# 食道癌指標
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


# 胰臟癌指標
PANCREATIC_ADENOCARCINOMA_HISTOLOGIES = [
    "8020", "8035", "8140", "8141", "8144", "8148", "8255",
    "8310", "8323", "8440", "8441", "8453", "8470", "8480",
    "8481", "8490", "8500", "8503", "8552", "8560", "8510",
]

PANCREATIC_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "胰臟癌病人首次治療前有組織學或細胞學診斷的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "valid_date", "field": "microscopic_confirmation_date"},
                {"op": "text_not_in", "field": "palliative_care", "values": ["7"]},
                {"op": "valid_date", "field": "first_treatment_date"},
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "microscopic_confirmation_date",
            "end_field": "first_treatment_date",
        },
    },
    4: {
        "name": "胰臟癌病人確診後30天內開始治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "case_classification", "value": "1"},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "valid_date", "field": "microscopic_confirmation_date"},
                {"op": "text_not_in", "field": "palliative_care", "values": ["7"]},
                {"op": "valid_date", "field": "first_treatment_date"},
            ],
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "diagnosis_date",
            "end_field": "first_treatment_date",
            "min_days": 0,
            "max_days": 30,
        },
    },
    5: {
        "name": "胰臟癌治癒性手術完全切除且邊緣無侵犯的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_not_in", "field": "margin_distance", "values": ["988", "991", "999"]},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "text_equals", "field": "surgical_margin", "value": "0"},
                {"op": "between", "field": "margin_distance", "min": 10, "max": 980},
            ],
        },
    },
    6: {
        "name": "胰臟癌治癒性手術淋巴結病理檢查12顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_not_in", "field": "margin_distance", "values": ["988", "991", "999"]},
                {"op": "text_not_in", "field": "surgical_margin", "values": ["3", "A", "B"]},
            ],
        },
        "numerator": {
            "op": "greater_than_or_equal",
            "field": "lymph_nodes_examined",
            "value": 12,
        },
    },
    7: {
        "name": "胰臟癌前置切除手術後接受輔助型化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_in", "field": "surgical_margin", "values": ["0", "2", "5", "C", "D", "E"]},
                {
                    "op": "not",
                    "rule": {"op": "first_char_in", "field": "clinical_stage", "values": ["4"]},
                },
                {
                    "op": "not",
                    "rule": {
                        "op": "date_after",
                        "start_field": "chemotherapy_date",
                        "end_field": "surgery_date",
                    },
                },
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "surgery_date",
            "end_field": "chemotherapy_date",
        },
    },
    8: {
        "name": "臨床第三期胰臟癌手術前接受前導化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "text_not_in", "field": "palliative_care", "values": ["7"]},
                {"op": "first_char_in", "field": "clinical_stage", "values": ["3"]},
                {"op": "first_char_in", "field": "clinical_t", "values": ["4"]},
                {"op": "first_char_in", "field": "clinical_n", "values": ["0", "1", "2", "3"]},
                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "valid_date", "field": "surgery_date"},
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "chemotherapy_date",
            "end_field": "surgery_date",
        },
    },
    9: {
        "name": "臨床第三或第四期胰臟癌接受全身性化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "histology", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "text_equals", "field": "behavior", "value": "3"},
                {"op": "first_char_in", "field": "clinical_stage", "values": ["3", "4"]},
            ],
        },
        "numerator": {"op": "valid_date", "field": "chemotherapy_date"},
    },
}


# 子宮頸癌指標
CERVICAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "CIN3或子宮頸原位癌以子宮頸錐狀手術為完整治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "text_equals", "field": "behavior", "value": "2"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 20, "max": 29},
                {"op": "not_in", "field": "surgery_code", "values": [25]},
            ],
        },
    },
    2: {
        "name": "FIGO期別IA2以上手術病人骨盆腔淋巴結摘除12顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {
                    "op": "text_in",
                    "field": "figo_stage",
                    "values": [
                        "1A2", "1B", "1B1", "1B2", "1B3", "2", "2A", "2A1",
                        "2A2", "2B", "3", "3A", "3B", "3C1", "3C2", "4A", "4B",
                    ],
                },
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {
                    "op": "dates_equal",
                    "left_field": "first_treatment_date",
                    "right_field": "surgery_date",
                },
            ],
        },
        "numerator": {
            "op": "between",
            "field": "lymph_nodes_examined",
            "min": 12,
            "max": 90,
        },
    },
    3: {
        "name": "子宮頸癌首次接受放射治療於63天內完成的比率",
        "type": "positive",
        "denominator": {
            "op": "dates_equal",
            "left_field": "first_treatment_date",
            "right_field": "radiation_date",
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "radiation_date",
            "end_field": "radiation_end_date",
            "min_days": 0,
            "max_days": 63,
        },
    },
    4: {
        "name": "子宮頸癌首次接受放射治療包含近接放射治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_not_in", "field": "figo_stage", "values": ["4B"]},
                {
                    "op": "dates_equal",
                    "left_field": "first_treatment_date",
                    "right_field": "radiation_date",
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "radiation_machine",
            "values": ["4", "5", "6", "7"],
        },
    },
    5: {
        "name": "指定FIGO期別子宮頸癌首次接受放療時合併化療的比率",
        "type": "unspecified",
        "denominator": {
            "op": "all",
            "rules": [
                {
                    "op": "text_in",
                    "field": "figo_stage",
                    "values": ["1B2", "1B3", "2A2", "2B", "3", "3A", "3B", "3C1", "3C2", "4A"],
                },
                {
                    "op": "dates_equal",
                    "left_field": "first_treatment_date",
                    "right_field": "radiation_date",
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "regional_systemic_sequence",
            "values": ["2", "3", "6", "7"],
        },
    },
}


# 肺癌指標
LUNG_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "臨床第IB至II期非小細胞肺癌手術淋巴結取樣至少3個位置的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "clinical_stage", "values": ["1B", "2A", "2B"]},
                {"op": "text_equals", "field": "is_nsclc", "value": "TRUE"},
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {"op": "text_not_in", "field": "mediastinal_nodes_sampled", "values": ["988"]},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "mediastinal_nodes_sampled",
            "min": 3,
            "max": 8,
        },
    },
    2: {
        "name": "臨床第IIIA期非小細胞肺癌手術淋巴結取樣至少3個位置的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_equals", "field": "clinical_stage", "value": "3A"},
                {"op": "text_equals", "field": "is_nsclc", "value": "TRUE"},
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {"op": "text_not_in", "field": "mediastinal_nodes_sampled", "values": ["988"]},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "mediastinal_nodes_sampled",
            "min": 3,
            "max": 8,
        },
    },
}


# 乳癌指標
BREAST_CANCER_RULES: dict[int, dict[str, Any]] = {
    2: {
        "name": "臨床第一、二期乳癌手術病人施行哨兵淋巴結取樣術的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "first_char_in", "field": "clinical_stage", "values": ["1", "2"]},
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {"op": "text_in", "field": "pathological_n", "values": ["0", "0A", "0B", "0C", "0D"]},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "equals", "field": "positive_lymph_nodes", "value": 0},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "regional_lymph_node_surgery_scope",
            "values": ["2", "6", "7"],
        },
    },
    3: {
        "name": "乳房全切除且淋巴結陽性4顆以上病人接受放射治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "positive_lymph_nodes", "min": 4, "max": 90},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 72},
                {"op": "first_char_in", "field": "merged_stage", "values": ["0", "1", "2", "3"]},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "radiation_status", "values": ["00", "04", "09", "10"]},
                {"op": "greater_than_or_equal", "field": "radiation_dose", "value": 4000},
            ],
        },
    },
    4: {
        "name": "HER2陽性且淋巴轉移之乳癌手術病人接受anti-HER2治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {
                    "op": "any",
                    "rules": [
                        {
                            "op": "text_in",
                            "field": "her2",
                            "values": ["103", "201", "301", "401", "501", "901"],
                        },
                        {
                            "op": "all",
                            "rules": [
                                {"op": "date_year_between", "field": "diagnosis_date", "min": 2023, "max": 2023},
                                {"op": "text_in", "field": "her2", "values": ["511", "521", "591"]},
                            ],
                        },
                        {
                            "op": "all",
                            "rules": [
                                {"op": "date_year_between", "field": "diagnosis_date", "min": 2024, "max": 2024},
                                {"op": "text_in", "field": "her2", "values": ["530", "531", "532"]},
                            ],
                        },
                    ],
                },
                {"op": "between", "field": "positive_lymph_nodes", "min": 1, "max": 97},
                {"op": "text_in", "field": "case_classification", "values": ["1", "2"]},
                {"op": "between", "field": "surgery_code", "min": 10, "max": 90},
                {
                    "op": "not",
                    "rule": {"op": "first_char_in", "field": "merged_stage", "values": ["4"]},
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "targeted_therapy_code",
            "values": ["01", "20", "21", "31"],
        },
    },
}


# 癌別收案條件
INDICATOR_RULES: dict[str, dict[int, dict[str, Any]]] = {
    "Oral_Cavity": ORAL_CANCER_RULES,
    "Esophagus": ESOPHAGEAL_CANCER_RULES,
    "Pancreas": PANCREATIC_CANCER_RULES,
    "Cervix_Uteri": CERVICAL_CANCER_RULES,
    "Lung": LUNG_CANCER_RULES,
    "Breast": BREAST_CANCER_RULES,
}
