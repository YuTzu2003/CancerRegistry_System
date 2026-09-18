"""
各癌別品質指標規則定義 (Cancer Indicator Rules)

本檔案集中定義各癌別之分子 (numerator) 與分母 (denominator) 規則邏輯，
包含：
1. 口腔癌 (Oral Cavity)
2. 卵巢癌 (Ovary)
3. 膀胱癌 (Bladder)
4. 攝護腺癌 (Prostate)
5. 子宮體癌 (Corpus Uteri)
"""

from __future__ import annotations

from typing import Any

# ===========================================================================
# 1. 口腔癌品質指標規則庫 (Oral Cavity)
# ===========================================================================
ORAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "口腔癌病人手術後 6 週內開始輔助治療（放射治療或化學放射治療)的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "valid_date", "field": "surgery_date"},
                # 放射治療開始日期不得為 00000000。
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
        "name": "口腔癌病人手術後30天內死亡的比率。",
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
        "name": "口腔癌病人開始接受放射治療(不含化療)後90天內死亡的比率。",
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
        "name": "口腔癌病人開始接受同步化學治療及放射治療後 90 天內死亡的比率。",
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
    #看到這-----
    5: {
        "name": "第一個口腔癌淋巴結病理檢查 15 顆(含)以上的比率。",
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
        "name": "病理切片證實為口腔鱗狀細胞癌並施行口腔根除性手術，其病理切緣(pathological margins)小於 4mm 的比例",
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


# ===========================================================================
# 2. 已建置癌別基礎定義 (Owned Cancer Declarations)
# ===========================================================================
OWNED_CANCER_RULES: dict[str, dict[int, dict[str, Any]]] = {
    "Ovary": {
        2: {"name": "卵巢癌手術病人殘存腫瘤狀態及大小有詳細記載的比率。", "type": "positive"},
        3: {"name": "卵巢癌手術病人無殘存腫瘤大小的比率。", "type": "positive"},
    },
    "Prostate": {
        1: {"name": "新診斷攝護腺癌病人治療前有肛診檢查的比率。", "type": "positive"},
        2: {"name": "新診斷攝護腺腺癌病人確診前三個月內有 PSA 值的比率。", "type": "positive"},
        3: {"name": "局限性低風險病人採主動監測、觀察等待或觀察治療的比率。", "type": "observation"},
        4: {"name": "局部侵犯型病人接受根治性體外放療且合併荷爾蒙治療的比率。", "type": "observation"},
        5: {"name": "局部侵犯型病人接受攝護腺根除術治療的比率。", "type": "observation"},
    },
    "Bladder": {
        1: {"name": "膀胱癌經尿道腫瘤切除術標本有固有肌肉層描述的比率。", "type": "positive"},
        2: {"name": "接受膀胱切除術病人完成病理期別的比率。", "type": "positive"},
        3: {"name": "接受膀胱根除性手術病人淋巴結至少檢查十顆的比率。", "type": "positive"},
    },
    "Corpus_Uteri": {
        2: {"name": "第一型子宮內膜癌早期期別病人接受完整分期手術的比率。", "type": "positive"},
        3: {"name": "第一型子宮內膜癌指定 FIGO 期別病人術後接受輔助治療的比率。", "type": "positive"},
        4: {"name": "第一型子宮內膜癌 FIGO III 至 IVA 期病人術後接受輔助治療的比率。", "type": "positive"},
        5: {"name": "子宮內膜癌病人於術後六十天內開始輔助治療的比率。", "type": "positive"},
        6: {"name": "第二型子宮內膜癌病人接受完整分期手術的比率。", "type": "positive"},
        7: {"name": "第二型子宮內膜癌病人術後接受輔助治療的比率。", "type": "positive"},
    },
}

# ---------------------------------------------------------------------------
# 組織型態群組、臨床試驗欄位與局部侵犯型判定共用條件
# ---------------------------------------------------------------------------
TYPE_I_HISTOLOGIES = [8380, 8382, 8383, 8480, 8560, 8570, 8140]
TYPE_II_HISTOLOGIES = [8441, 8310, 8041, 8045, 8246, 8013, 8020, 8323, 8070, 8071, 8072, 8076]
CLINICAL_TRIAL_FIELDS = [
    "clinical_trial_432", "clinical_trial_433", "clinical_trial_435", "clinical_trial_436",
    "clinical_trial_438", "clinical_trial_439", "clinical_trial_4313", "clinical_trial_4314",
]
LOCALLY_ADVANCED_PROSTATE = {"op": "all", "rules": [
    {"op": "text_in_without_prefix", "field": "clinical_t", "prefix": "T", "values": ["3", "3A", "3B", "4"]},
    {"op": "text_in_without_prefix", "field": "clinical_n", "prefix": "N", "values": ["0", "1"]},
    {"op": "text_in_without_prefix", "field": "clinical_m", "prefix": "M", "values": ["0"]},
    {"op": "text_in_without_prefix", "field": "pathological_m", "prefix": "M", "values": ["B"]},
    {"op": "equals", "field": "palliative_care", "value": 0},
    {"op": "all_fields_not_in", "fields": CLINICAL_TRIAL_FIELDS, "values": ["20", "21", "30", "31"]},
    {"op": "equals", "field": "other_treatment", "value": 0},
]}

# ---------------------------------------------------------------------------
# 3. 卵巢癌 (Ovary) 分子分母規則裝配
# ---------------------------------------------------------------------------
for _number in (2, 3):
    OWNED_CANCER_RULES["Ovary"][_number].update({
        "denominator": {"op": "all", "rules": [
            {"op": "stage_first_char_in", "field": "pathological_stage", "values": ["2", "3", "4"]},
            {"op": "between", "field": "surgery_code", "min": 25, "max": 90},
            {"op": "present", "field": "ssf3"},
            {"op": "not_in", "field": "ssf3", "values": [988]},
        ]},
        "numerator": (
            {"op": "text_in", "field": "ssf3", "values": ["000", "010", "020", "030", "040"]}
            if _number == 2 else {"op": "equals", "field": "ssf3", "value": 0}
        ),
    })

# ---------------------------------------------------------------------------
# 4. 膀胱癌 (Bladder) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Bladder"].update({
    1: {**OWNED_CANCER_RULES["Bladder"][1], "denominator": {"op": "all", "rules": [
        {"op": "between", "field": "surgery_code", "min": 20, "max": 27},
        {"op": "present", "field": "ssf3"}, {"op": "not_in", "field": "ssf3", "values": [988]},
    ]}, "numerator": {"op": "equals", "field": "ssf3", "value": 10}},
    2: {**OWNED_CANCER_RULES["Bladder"][2], "denominator": {"op": "between", "field": "surgery_code", "min": 50, "max": 80},
        "numerator": {"op": "any", "rules": [{"op": "stage_in", "field": "pathological_stage", "values": ["BBB"]}, {"op": "stage_matches", "field": "pathological_stage", "pattern": r"[0-4](?:A|B|C|IS)?"}]}},
    3: {**OWNED_CANCER_RULES["Bladder"][3], "denominator": {"op": "between", "field": "surgery_code", "min": 60, "max": 74},
        "numerator": {"op": "between", "field": "lymph_nodes_examined", "min": 10, "max": 90}},
})

# ---------------------------------------------------------------------------
# 5. 攝護腺癌 (Prostate) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Prostate"].update({
    1: {**OWNED_CANCER_RULES["Prostate"][1], "denominator": {"op": "text_not_in", "field": "other_clinical_stage", "values": ["X", "TX"]}, "numerator": {"op": "text_not_equals", "field": "other_clinical_stage", "value": "8888"}},
    2: {**OWNED_CANCER_RULES["Prostate"][2], "denominator": {"op": "all", "rules": []}, "numerator": {"op": "between", "field": "ssf1", "min": 1, "max": 998}},
    3: {**OWNED_CANCER_RULES["Prostate"][3], "denominator": {"op": "all", "rules": [
        {"op": "text_in_without_prefix", "field": "clinical_t", "prefix": "T", "values": ["1", "1A", "1B", "1C", "2A"]},
        {"op": "text_in_without_prefix", "field": "clinical_n", "prefix": "N", "values": ["0"]}, {"op": "text_in_without_prefix", "field": "clinical_m", "prefix": "M", "values": ["0"]},
        {"op": "between", "field": "ssf1", "min": 1, "max": 99}, {"op": "between", "field": "ssf3", "min": 2, "max": 6}, {"op": "equals", "field": "palliative_care", "value": 0},
        {"op": "all_fields_not_in", "fields": CLINICAL_TRIAL_FIELDS, "values": ["20", "21", "30", "31"]}, {"op": "equals", "field": "other_treatment", "value": 0},
    ]}, "numerator": {"op": "all", "rules": [{"op": "equals", "field": "treatment_status", "value": 4}, {"op": "valid_date", "field": "first_course_date"}]}},
    4: {**OWNED_CANCER_RULES["Prostate"][4], "denominator": {"op": "all", "rules": [LOCALLY_ADVANCED_PROSTATE, {"op": "in", "field": "radiation_summary", "values": [1, 3]}, {"op": "present", "field": "radiation_instrument"}, {"op": "not_in", "field": "radiation_instrument", "values": [4, 5, 8, 9, 20, 21, 24, 25, 36, 37, 40, 41, 52, 56, 64, 65, 80, 81, 96, 97, 112]}, {"op": "present", "field": "surgery_code"}, {"op": "not_in", "field": "surgery_code", "values": [14, 16, 17, 24, 26, 27, 30, 50, 70, 80]}]}, "numerator": {"op": "all", "rules": [{"op": "bed_at_least", "courses": [{"dose_field": "radiation_dose", "fractions_field": "radiation_fractions"}, {"dose_field": "other_radiation_dose", "fractions_field": "other_radiation_fractions"}], "value": 150}, {"op": "equals", "field": "hormone_therapy", "value": 1}]}},
    5: {**OWNED_CANCER_RULES["Prostate"][5], "denominator": {"op": "all", "rules": [LOCALLY_ADVANCED_PROSTATE, {"op": "present", "field": "surgery_code"}, {"op": "not_in", "field": "surgery_code", "values": [14, 16, 17, 24, 26, 27, 30]}]}, "numerator": {"op": "between", "field": "surgery_code", "min": 31, "max": 80}},
})

# ---------------------------------------------------------------------------
# 6. 子宮體癌 (Corpus Uteri) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Corpus_Uteri"].update({
    2: {**OWNED_CANCER_RULES["Corpus_Uteri"][2], "denominator": {"op": "all", "rules": [{"op": "in", "field": "histology", "values": TYPE_I_HISTOLOGIES}, {"op": "stage_in", "field": "clinical_stage", "values": ["1", "1A", "1B", "1C", "2"]}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}, {"op": "not", "rule": {"op": "all", "rules": [{"op": "stage_in", "field": "clinical_stage", "values": ["1A"]}, {"op": "text_in", "field": "clinical_grade", "values": ["1", "L"]}]}}]}, "numerator": {"op": "all", "rules": [{"op": "between", "field": "surgery_code", "min": 50, "max": 79}, {"op": "between", "field": "regional_lymph_surgery", "min": 3, "max": 7}]}},
    3: {**OWNED_CANCER_RULES["Corpus_Uteri"][3], "denominator": {"op": "all", "rules": [{"op": "in", "field": "histology", "values": TYPE_I_HISTOLOGIES}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "date_year_between", "field": "diagnosis_date", "min": 1, "max": 2023}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "preferred_stage_in", "preferred_field": "other_pathological_stage", "fallback_field": "pathological_stage", "invalid_values": ["", "0000", "8888", "9999"], "values": ["1B"]}, {"op": "text_in", "field": "pathological_grade", "values": ["3", "H", "C"]}]}, {"op": "preferred_stage_in", "preferred_field": "other_pathological_stage", "fallback_field": "pathological_stage", "invalid_values": ["", "0000", "8888", "9999"], "values": ["2"]}]}, {"op": "not_in", "field": "surgery_code", "values": [60, 61, 62, 63, 64]}]}, {"op": "all", "rules": [{"op": "date_year_between", "field": "diagnosis_date", "min": 2024, "max": 9999}, {"op": "preferred_stage_in", "preferred_field": "other_pathological_stage", "fallback_field": "pathological_stage", "invalid_values": ["", "0000", "8888", "9999"], "values": ["1C", "2A", "2B", "2C"]}]}]}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "surgery_date", "candidate_fields": ["radiation_date", "chemotherapy_date"]}},
    4: {**OWNED_CANCER_RULES["Corpus_Uteri"][4], "denominator": {"op": "all", "rules": [{"op": "in", "field": "histology", "values": TYPE_I_HISTOLOGIES}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}, {"op": "valid_date", "field": "surgery_date"}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "date_year_between", "field": "diagnosis_date", "min": 1, "max": 2023}, {"op": "preferred_stage_in", "preferred_field": "other_pathological_stage", "fallback_field": "pathological_stage", "invalid_values": ["", "0000", "8888", "9999"], "values": ["3", "3A", "3B", "3C1", "3C2", "4A"]}]}, {"op": "all", "rules": [{"op": "date_year_between", "field": "diagnosis_date", "min": 2024, "max": 9999}, {"op": "preferred_stage_in", "preferred_field": "other_pathological_stage", "fallback_field": "pathological_stage", "invalid_values": ["", "0000", "8888", "9999"], "values": ["3", "3A", "3A1", "3A2", "3B", "3B1", "3B2", "3C", "3C1", "3C1I", "3C1II", "3C2", "3C2I", "3C2II", "4A"]}]}]}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "surgery_date", "candidate_fields": ["radiation_date", "chemotherapy_date", "immunotherapy_date", "targeted_therapy_date"]}},
    5: {**OWNED_CANCER_RULES["Corpus_Uteri"][5], "denominator": {"op": "all", "rules": [{"op": "concatenated_text_in", "fields": ["case_class", "diagnosis_status", "treatment_status"], "values": ["111", "221"]}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}, {"op": "any_date_on_or_after", "reference_field": "surgery_date", "candidate_fields": ["radiation_date", "chemotherapy_date"]}]}, "numerator": {"op": "earliest_on_or_after_within", "reference_field": "surgery_date", "candidate_fields": ["radiation_date", "chemotherapy_date"], "min_days": 0, "max_days": 60}},
    6: {**OWNED_CANCER_RULES["Corpus_Uteri"][6], "denominator": {"op": "all", "rules": [{"op": "in", "field": "histology", "values": TYPE_II_HISTOLOGIES}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}]}, "numerator": {"op": "all", "rules": [{"op": "between", "field": "surgery_code", "min": 50, "max": 79}, {"op": "between", "field": "regional_lymph_surgery", "min": 3, "max": 7}, {"op": "any", "rules": [{"op": "equals", "field": "other_site_surgery", "value": 4}, {"op": "zero_fill_text_in", "field": "hospital_diagnostic_surgery", "width": 2, "values": ["01", "10"]}, {"op": "zero_fill_text_in", "field": "external_diagnostic_surgery", "width": 2, "values": ["01", "10"]}]}]}},
    7: {**OWNED_CANCER_RULES["Corpus_Uteri"][7], "denominator": {"op": "all", "rules": [{"op": "in", "field": "histology", "values": TYPE_II_HISTOLOGIES}, {"op": "between", "field": "surgery_code", "min": 40, "max": 79}, {"op": "valid_date", "field": "surgery_date"}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "surgery_date", "candidate_fields": ["radiation_date", "chemotherapy_date", "immunotherapy_date", "targeted_therapy_date"]}},
})


# Dashboard3 cancer indicator definitions.
GASTRIC_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "臨床分期為第 I~ IIIC 期之胃及食道賁門癌病人手術後 R0 切除的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "first_char_in", "field": "clinical_stage", "values": ["1", "2", "3"]},
            {"op": "any", "rules": [
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {"op": "text_in", "field": "surgery_code", "values": ["2E", "2M"]},
            ]},
            {"op": "equals", "field": "palliative_care", "value": 0},
            {"op": "text_not_in", "field": "surgical_margin", "values": ["7", "9"]},
        ]},
        "numerator": {"op": "text_in", "field": "surgical_margin", "values": ["0", "C", "D", "E"]},
    },
    3: {
        "name": "胃及食道賁門癌手術病人於術後 30 天內死亡的比率。",
        "type": "negative",
        "denominator": {"op": "all", "rules": [
            {"op": "any", "rules": [
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                {"op": "text_in", "field": "surgery_code", "values": ["2E", "2M"]},
            ]},
            {"op": "equals", "field": "palliative_care", "value": 0},
        ]},
        "numerator": {"op": "all", "rules": [
            {"op": "equals", "field": "survival_status", "value": 0},
            {"op": "date_interval", "start_field": "surgery_date", "end_field": "last_contact_date", "min_days": 0, "max_days": 29},
        ]},
    },
    4: {
        "name": "病理期別第 II-III 期胃及食道賁門癌病人術後接受輔助化療的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "first_char_in", "field": "pathological_stage", "values": ["2", "3"]},
            {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
            {"op": "text_not_in", "field": "pathology_prefix", "values": ["4", "6"]},
        ]},
        "numerator": {"op": "date_on_or_after", "start_field": "surgery_date", "end_field": "chemotherapy_date"},
    },
}

LIVER_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "極早期和早期肝細胞癌病人接受治癒性療法的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "equals", "field": "treatment_status", "value": 1},
            {"op": "equals", "field": "other_staging_system", "value": 6},
            {"op": "first_char_in", "field": "other_clinical_stage", "values": ["0", "A"]},
        ]},
        "numerator": {"op": "any", "rules": [
            {"op": "any", "rules": [
                {"op": "equals", "field": "surgery_code", "value": 61},
                {"op": "equals", "field": "surgery_code", "value": 75},
            ]},
            {"op": "all", "rules": [
                {"op": "any", "rules": [
                    {"op": "between", "field": "surgery_code", "min": 20, "max": 25}, {"op": "between", "field": "surgery_code", "min": 27, "max": 29}, {"op": "between", "field": "surgery_code", "min": 30, "max": 32}, {"op": "in", "field": "surgery_code", "values": [34, 35, 38, 54, 55, 59, 60, 66, 90]},
                ]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "in", "field": "surgery_code", "values": [26, 33, 53]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
                {"op": "date_interval", "start_field": "first_surgery_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                {"op": "any", "rules": [
                    {"op": "between", "field": "surgery_code", "min": 20, "max": 25}, {"op": "between", "field": "surgery_code", "min": 30, "max": 32}, {"op": "between", "field": "surgery_code", "min": 50, "max": 52}, {"op": "in", "field": "surgery_code", "values": [60, 66, 90]},
                ]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                {"op": "any", "rules": [
                    {"op": "in", "field": "surgery_code", "values": [26, 33, 53, 34, 35, 38, 54, 55, 59]},
                    {"op": "between", "field": "surgery_code", "min": 27, "max": 29},
                ]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "in", "field": "surgery_code", "values": [16, 17, 19]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "equals", "field": "surgery_code", "value": 18},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                {"op": "in", "field": "surgery_code", "values": [16, 17, 19]},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                {"op": "equals", "field": "surgery_code", "value": 18},
                {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 60},
            ]},
        ]},
    },
    5: {"name": "肝癌患者接受手術切除其邊緣無殘留癌細胞的比率。", "type": "positive", "denominator": {"op": "any", "rules": [{"op": "between", "field": "surgery_code", "min": 22, "max": 60}, {"op": "between", "field": "surgery_code", "min": 65, "max": 66}, {"op": "equals", "field": "surgery_code", "value": 90}]}, "numerator": {"op": "text_equals", "field": "surgical_margin", "value": "0"}},
    6: {"name": "肝細胞癌 BCLC stage 0+A+B 病患等待治療時間在 45 天以內。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "equals", "field": "other_staging_system", "value": 6}, {"op": "first_char_in", "field": "other_clinical_stage", "values": ["0", "A", "B"]}, {"op": "in", "field": "treatment_status", "values": [1, 3]}]}, "numerator": {"op": "date_interval", "start_field": "diagnosis_date", "end_field": "first_treatment_date", "min_days": 0, "max_days": 45}},
}

COLON_RECTUM_CANCER_RULES: dict[int, dict[str, Any]] = {
    2: {"name": "病理期別第 I-III 期結腸癌手術病人，淋巴結病理檢查 12 顆以上的比率。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "text_starts_with", "field": "site", "values": ["C18"]}, {"op": "first_char_in", "field": "pathological_stage", "values": ["1", "2", "3"]}, {"op": "between", "field": "surgery_code", "min": 30, "max": 90}]}, "numerator": {"op": "between", "field": "lymph_nodes_examined", "min": 12, "max": 90}},
    3: {"name": "第 II、III 期直腸癌病人，6 週內開始治療的比率。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "text_starts_with", "field": "site", "values": ["C19", "C20"]}, {"op": "equals", "field": "case_classification", "value": 1}, {"op": "first_char_in", "field": "clinical_stage", "values": ["2", "3"]}]}, "numerator": {"op": "date_interval", "start_field": "microscopic_confirmation_date", "end_field": "first_treatment_date", "min_days": 0, "max_days": 42}},
}
