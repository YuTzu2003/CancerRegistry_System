"""
各癌別品質指標規則定義 (Cancer Indicator Rules)
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
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                {"op": "valid_date", "field": "4.1.2"},
                # 放射治療開始日期不得為 00000000。
                {"op": "valid_date", "field": "4.2.1.3"},
                {
                    "op": "any",
                    "rules": [
                        {
                            "op": "date_after",
                            "start_field": "4.1.2",
                            "end_field": "4.2.1.3",
                        },
                        {
                            "op": "date_after",
                            "start_field": "4.1.2",
                            "end_field": "4.3.4",
                        },
                    ],
                },
            ],
        },
        "numerator": {
            "op": "earliest_after_within",
            "reference_field": "4.1.2",
            "candidate_fields": ["4.2.1.3", "4.3.4"],
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
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                {"op": "equals", "field": "4.4", "value": 0},
                {"op": "valid_date", "field": "4.1.2"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "5.4", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "4.1.2",
                    "end_field": "5.3",
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
                {"op": "valid_date", "field": "4.2.1.3"},
                {"op": "greater_than", "field": "4.2.2.2.2", "value": 0},
                {"op": "equals", "field": "4.3.3", "value": 0},
                {"op": "equals", "field": "4.4", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "5.4", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "4.2.1.3",
                    "end_field": "5.3",
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
                {"op": "valid_date", "field": "4.2.1.3"},
                {"op": "greater_than", "field": "4.2.2.2.2", "value": 0},
                {"op": "greater_than", "field": "4.3.3", "value": 0},
                {
                    "op": "not_in",
                    "field": "4.3.3",
                    "values": [82, 83, 85, 86, 87, 88, 99],
                },
                {"op": "valid_date", "field": "4.3.4"},
                {"op": "equals", "field": "4.4", "value": 0},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "5.4", "value": 0},
                {
                    "op": "earliest_date_interval",
                    "start_fields": ["4.2.1.3", "4.3.4"],
                    "end_field": "5.3",
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
                {"op": "equals", "field": "2.2", "value": 1},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "2.14",
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
                {"op": "between", "field": "2.8", "min": 8050, "max": 8086},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                {"op": "not_in", "field": "4.1.5.1", "values": [991, 999]},
            ],
        },
        "numerator": {
            "op": "any",
            "rules": [
                {"op": "between", "field": "4.1.5.1", "min": 0, "max": 39},
                {"op": "equals", "field": "4.1.5.1", "value": 987},
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
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                # 2E、2M 無法轉成整數，本來就不會符合 between；保留此規則以對應規格。
                {"op": "text_not_in", "field": "4.1.4", "values": ["2E", "2M"]},
                {"op": "first_char_in", "field": "3.6", "values": ["0"]},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "4.1.5",
            "values": ["0", "C", "D", "E"],
        },
    },
    2: {
        "name": "食道切除標本淋巴結病理檢查15顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {
                    "op": "text_not_in",
                    "field": "4.1.5",
                    "values": ["2", "3", "4", "A", "B"],
                },
            ],
        },
        "numerator": {
            "op": "between",
            "field": "2.14",
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
                {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
                {"op": "equals", "field": "4.4", "value": 0},
                {"op": "valid_date", "field": "4.1.2"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "5.4", "value": 0},
                {
                    "op": "date_interval",
                    "start_field": "4.1.2",
                    "end_field": "5.3",
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
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
                {"op": "text_equals", "field": "2.2", "value": "01"},
                {
                    "op": "any",
                    "rules": [
                        # A：cT4N0M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "3.4", "values": ["4"]},
                                {"op": "first_char_in", "field": "3.5", "values": ["0"]},
                                {"op": "first_char_in", "field": "3.6", "values": ["0"]},
                            ],
                        },
                        # B：cTanyN1-3M0。
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "3.5", "values": ["1", "2", "3"]},
                                {"op": "first_char_in", "field": "3.6", "values": ["0"]},
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
                {"op": "valid_date", "field": "4.1.2"},
                {"op": "valid_date", "field": "4.2.1.3"},
                {"op": "valid_date", "field": "4.3.4"},
                {
                    "op": "date_after",
                    "start_field": "4.2.1.3",
                    "end_field": "4.1.2",
                },
                {
                    "op": "date_after",
                    "start_field": "4.3.4",
                    "end_field": "4.1.2",
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
    "4.3.2", "4.3.3", "4.3.5", "4.3.6",
    "4.3.8", "4.3.9", "4.3.13", "4.3.14",
]
LOCALLY_ADVANCED_PROSTATE = {"op": "all", "rules": [
    {"op": "text_in_without_prefix", "field": "3.4", "prefix": "T", "values": ["3", "3A", "3B", "4"]},
    {"op": "text_in_without_prefix", "field": "3.5", "prefix": "N", "values": ["0", "1"]},
    {"op": "text_in_without_prefix", "field": "3.6", "prefix": "M", "values": ["0"]},
    {"op": "text_in_without_prefix", "field": "3.12", "prefix": "M", "values": ["B"]},
    {"op": "equals", "field": "4.4", "value": 0},
    {"op": "all_fields_not_in", "fields": CLINICAL_TRIAL_FIELDS, "values": ["20", "21", "30", "31"]},
    {"op": "equals", "field": "4.5.1", "value": 0},
]}

# ---------------------------------------------------------------------------
# 3. 卵巢癌 (Ovary) 分子分母規則裝配
# ---------------------------------------------------------------------------
for _number in (2, 3):
    OWNED_CANCER_RULES["Ovary"][_number].update({
        "denominator": {"op": "all", "rules": [
            {"op": "stage_first_char_in", "field": "3.13", "values": ["2", "3", "4"]},
            {"op": "between", "field": "4.1.4", "min": 25, "max": 90},
            {"op": "present", "field": "8.3"},
            {"op": "not_in", "field": "8.3", "values": [988]},
        ]},
        "numerator": (
            {"op": "text_in", "field": "8.3", "values": ["000", "010", "020", "030", "040"]}
            if _number == 2 else {"op": "equals", "field": "8.3", "value": 0}
        ),
    })

# ---------------------------------------------------------------------------
# 4. 膀胱癌 (Bladder) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Bladder"].update({
    1: {**OWNED_CANCER_RULES["Bladder"][1], "denominator": {"op": "all", "rules": [
        {"op": "between", "field": "4.1.4", "min": 20, "max": 27},
        {"op": "present", "field": "8.3"}, {"op": "not_in", "field": "8.3", "values": [988]},
    ]}, "numerator": {"op": "equals", "field": "8.3", "value": 10}},
    2: {**OWNED_CANCER_RULES["Bladder"][2], "denominator": {"op": "between", "field": "4.1.4", "min": 50, "max": 80},
        "numerator": {"op": "any", "rules": [{"op": "stage_in", "field": "3.13", "values": ["BBB"]}, {"op": "stage_matches", "field": "3.13", "pattern": r"[0-4](?:A|B|C|IS)?"}]}},
    3: {**OWNED_CANCER_RULES["Bladder"][3], "denominator": {"op": "between", "field": "4.1.4", "min": 60, "max": 74},
        "numerator": {"op": "between", "field": "2.14", "min": 10, "max": 90}},
})

# ---------------------------------------------------------------------------
# 5. 攝護腺癌 (Prostate) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Prostate"].update({
    1: {**OWNED_CANCER_RULES["Prostate"][1], "denominator": {"op": "text_not_in", "field": "3.19", "values": ["X", "TX"]}, "numerator": {"op": "text_not_equals", "field": "3.19", "value": "8888"}},
    2: {**OWNED_CANCER_RULES["Prostate"][2], "denominator": {"op": "all", "rules": []}, "numerator": {"op": "between", "field": "8.1", "min": 1, "max": 998}},
    3: {**OWNED_CANCER_RULES["Prostate"][3], "denominator": {"op": "all", "rules": [
        {"op": "text_in_without_prefix", "field": "3.4", "prefix": "T", "values": ["1", "1A", "1B", "1C", "2A"]},
        {"op": "text_in_without_prefix", "field": "3.5", "prefix": "N", "values": ["0"]}, {"op": "text_in_without_prefix", "field": "3.6", "prefix": "M", "values": ["0"]},
        {"op": "between", "field": "8.1", "min": 1, "max": 99}, {"op": "between", "field": "8.3", "min": 2, "max": 6}, {"op": "equals", "field": "4.4", "value": 0},
        {"op": "all_fields_not_in", "fields": CLINICAL_TRIAL_FIELDS, "values": ["20", "21", "30", "31"]}, {"op": "equals", "field": "4.5.1", "value": 0},
    ]}, "numerator": {"op": "all", "rules": [{"op": "equals", "field": "2.3.2", "value": 4}, {"op": "valid_date", "field": "4.1"}]}},
    4: {**OWNED_CANCER_RULES["Prostate"][4], "denominator": {"op": "all", "rules": [LOCALLY_ADVANCED_PROSTATE, {"op": "in", "field": "4.2.1.1", "values": [1, 3]}, {"op": "present", "field": "4.2.1.2"}, {"op": "not_in", "field": "4.2.1.2", "values": [4, 5, 8, 9, 20, 21, 24, 25, 36, 37, 40, 41, 52, 56, 64, 65, 80, 81, 96, 97, 112]}, {"op": "present", "field": "4.1.4"}, {"op": "not_in", "field": "4.1.4", "values": [14, 16, 17, 24, 26, 27, 30, 50, 70, 80]}]}, "numerator": {"op": "all", "rules": [{"op": "bed_at_least", "courses": [{"dose_field": "4.2.2.2.2", "fractions_field": "4.2.2.2.3"}, {"dose_field": "4.2.3.3.2", "fractions_field": "4.2.3.3.3"}], "value": 150}, {"op": "equals", "field": "4.3.6", "value": 1}]}},
    5: {**OWNED_CANCER_RULES["Prostate"][5], "denominator": {"op": "all", "rules": [LOCALLY_ADVANCED_PROSTATE, {"op": "present", "field": "4.1.4"}, {"op": "not_in", "field": "4.1.4", "values": [14, 16, 17, 24, 26, 27, 30]}]}, "numerator": {"op": "between", "field": "4.1.4", "min": 31, "max": 80}},
})

# ---------------------------------------------------------------------------
# 6. 子宮體癌 (Corpus Uteri) 分子分母規則裝配
# ---------------------------------------------------------------------------
OWNED_CANCER_RULES["Corpus_Uteri"].update({
    2: {**OWNED_CANCER_RULES["Corpus_Uteri"][2], "denominator": {"op": "all", "rules": [{"op": "in", "field": "2.8", "values": TYPE_I_HISTOLOGIES}, {"op": "stage_in", "field": "3.7", "values": ["1", "1A", "1B", "1C", "2"]}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}, {"op": "not", "rule": {"op": "all", "rules": [{"op": "stage_in", "field": "3.7", "values": ["1A"]}, {"op": "text_in", "field": "2.10.1", "values": ["1", "L"]}]}}]}, "numerator": {"op": "all", "rules": [{"op": "between", "field": "4.1.4", "min": 50, "max": 79}, {"op": "between", "field": "4.1.7", "min": 3, "max": 7}]}},
    3: {**OWNED_CANCER_RULES["Corpus_Uteri"][3], "denominator": {"op": "all", "rules": [{"op": "in", "field": "2.8", "values": TYPE_I_HISTOLOGIES}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "date_year_between", "field": "2.5", "min": 1, "max": 2023}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "preferred_stage_in", "preferred_field": "3.21", "fallback_field": "3.13", "invalid_values": ["", "0000", "8888", "9999"], "values": ["1B"]}, {"op": "text_in", "field": "2.10.2", "values": ["3", "H", "C"]}]}, {"op": "preferred_stage_in", "preferred_field": "3.21", "fallback_field": "3.13", "invalid_values": ["", "0000", "8888", "9999"], "values": ["2"]}]}, {"op": "not_in", "field": "4.1.4", "values": [60, 61, 62, 63, 64]}]}, {"op": "all", "rules": [{"op": "date_year_between", "field": "2.5", "min": 2024, "max": 9999}, {"op": "preferred_stage_in", "preferred_field": "3.21", "fallback_field": "3.13", "invalid_values": ["", "0000", "8888", "9999"], "values": ["1C", "2A", "2B", "2C"]}]}]}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "4.1.2", "candidate_fields": ["4.2.1.3", "4.3.4"]}},
    4: {**OWNED_CANCER_RULES["Corpus_Uteri"][4], "denominator": {"op": "all", "rules": [{"op": "in", "field": "2.8", "values": TYPE_I_HISTOLOGIES}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}, {"op": "valid_date", "field": "4.1.2"}, {"op": "any", "rules": [{"op": "all", "rules": [{"op": "date_year_between", "field": "2.5", "min": 1, "max": 2023}, {"op": "preferred_stage_in", "preferred_field": "3.21", "fallback_field": "3.13", "invalid_values": ["", "0000", "8888", "9999"], "values": ["3", "3A", "3B", "3C1", "3C2", "4A"]}]}, {"op": "all", "rules": [{"op": "date_year_between", "field": "2.5", "min": 2024, "max": 9999}, {"op": "preferred_stage_in", "preferred_field": "3.21", "fallback_field": "3.13", "invalid_values": ["", "0000", "8888", "9999"], "values": ["3", "3A", "3A1", "3A2", "3B", "3B1", "3B2", "3C", "3C1", "3C1I", "3C1II", "3C2", "3C2I", "3C2II", "4A"]}]}]}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "4.1.2", "candidate_fields": ["4.2.1.3", "4.3.4", "4.3.10", "4.3.15"]}},
    5: {**OWNED_CANCER_RULES["Corpus_Uteri"][5], "denominator": {"op": "all", "rules": [{"op": "concatenated_text_in", "fields": ["2.3", "2.3.1", "2.3.2"], "values": ["111", "221"]}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}, {"op": "any_date_on_or_after", "reference_field": "4.1.2", "candidate_fields": ["4.2.1.3", "4.3.4"]}]}, "numerator": {"op": "earliest_on_or_after_within", "reference_field": "4.1.2", "candidate_fields": ["4.2.1.3", "4.3.4"], "min_days": 0, "max_days": 60}},
    6: {**OWNED_CANCER_RULES["Corpus_Uteri"][6], "denominator": {"op": "all", "rules": [{"op": "in", "field": "2.8", "values": TYPE_II_HISTOLOGIES}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}]}, "numerator": {"op": "all", "rules": [{"op": "between", "field": "4.1.4", "min": 50, "max": 79}, {"op": "between", "field": "4.1.7", "min": 3, "max": 7}, {"op": "any", "rules": [{"op": "equals", "field": "4.1.9", "value": 4}, {"op": "zero_fill_text_in", "field": "3.3", "width": 2, "values": ["01", "10"]}, {"op": "zero_fill_text_in", "field": "3.2", "width": 2, "values": ["01", "10"]}]}]}},
    7: {**OWNED_CANCER_RULES["Corpus_Uteri"][7], "denominator": {"op": "all", "rules": [{"op": "in", "field": "2.8", "values": TYPE_II_HISTOLOGIES}, {"op": "between", "field": "4.1.4", "min": 40, "max": 79}, {"op": "valid_date", "field": "4.1.2"}]}, "numerator": {"op": "any_date_on_or_after", "reference_field": "4.1.2", "candidate_fields": ["4.2.1.3", "4.3.4", "4.3.10", "4.3.15"]}},
})

# Named exports keep these four cancer types consistent with the other
# cancer-specific rule collections above.
OVARY_CANCER_RULES = OWNED_CANCER_RULES["Ovary"]
PROSTATE_CANCER_RULES = OWNED_CANCER_RULES["Prostate"]
BLADDER_CANCER_RULES = OWNED_CANCER_RULES["Bladder"]
CORPUS_UTERI_CANCER_RULES = OWNED_CANCER_RULES["Corpus_Uteri"]


# Dashboard3 cancer indicator definitions.
GASTRIC_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "臨床分期為第 I~ IIIC 期之胃及食道賁門癌病人手術後 R0 切除的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "first_char_in", "field": "3.7", "values": ["1", "2", "3"]},
            {"op": "any", "rules": [
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {"op": "text_in", "field": "4.1.4", "values": ["2E", "2M"]},
            ]},
            {"op": "equals", "field": "4.4", "value": 0},
            {"op": "text_not_in", "field": "4.1.5", "values": ["7", "9"]},
        ]},
        "numerator": {"op": "text_in", "field": "4.1.5", "values": ["0", "C", "D", "E"]},
    },
    3: {
        "name": "胃及食道賁門癌手術病人於術後 30 天內死亡的比率。",
        "type": "negative",
        "denominator": {"op": "all", "rules": [
            {"op": "any", "rules": [
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {"op": "text_in", "field": "4.1.4", "values": ["2E", "2M"]},
            ]},
            {"op": "equals", "field": "4.4", "value": 0},
        ]},
        "numerator": {"op": "all", "rules": [
            {"op": "equals", "field": "5.4", "value": 0},
            {"op": "date_interval", "start_field": "4.1.2", "end_field": "5.3", "min_days": 0, "max_days": 29},
        ]},
    },
    4: {
        "name": "病理期別第 II-III 期胃及食道賁門癌病人術後接受輔助化療的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "first_char_in", "field": "3.13", "values": ["2", "3"]},
            {"op": "between", "field": "4.1.4", "min": 30, "max": 90},
            {"op": "text_not_in", "field": "3.14", "values": ["4", "6"]},
        ]},
        "numerator": {"op": "date_on_or_after", "start_field": "4.1.2", "end_field": "4.3.4"},
    },
}

LIVER_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "極早期和早期肝細胞癌病人接受治癒性療法的比率。",
        "type": "positive",
        "denominator": {"op": "all", "rules": [
            {"op": "equals", "field": "2.3.2", "value": 1},
            {"op": "equals", "field": "3.17", "value": 6},
            {"op": "first_char_in", "field": "3.19", "values": ["0", "A"]},
        ]},
        "numerator": {"op": "any", "rules": [
            {"op": "any", "rules": [
                {"op": "equals", "field": "4.1.4", "value": 61},
                {"op": "equals", "field": "4.1.4", "value": 75},
            ]},
            {"op": "all", "rules": [
                {"op": "any", "rules": [
                    {"op": "between", "field": "4.1.4", "min": 20, "max": 25}, {"op": "between", "field": "4.1.4", "min": 27, "max": 29}, {"op": "between", "field": "4.1.4", "min": 30, "max": 32}, {"op": "in", "field": "4.1.4", "values": [34, 35, 38, 54, 55, 59, 60, 66, 90]},
                ]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.1", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "in", "field": "4.1.4", "values": [26, 33, 53]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.1", "min_days": 0, "max_days": 0},
                {"op": "date_interval", "start_field": "4.1.1", "end_field": "4.1.2", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "4.3.3", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.3.4", "min_days": 0, "max_days": 0},
                {"op": "any", "rules": [
                    {"op": "between", "field": "4.1.4", "min": 20, "max": 25}, {"op": "between", "field": "4.1.4", "min": 30, "max": 32}, {"op": "between", "field": "4.1.4", "min": 50, "max": 52}, {"op": "in", "field": "4.1.4", "values": [60, 66, 90]},
                ]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.2", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "4.3.3", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.3.4", "min_days": 0, "max_days": 0},
                {"op": "any", "rules": [
                    {"op": "in", "field": "4.1.4", "values": [26, 33, 53, 34, 35, 38, 54, 55, 59]},
                    {"op": "between", "field": "4.1.4", "min": 27, "max": 29},
                ]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.1", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "in", "field": "4.1.4", "values": [16, 17, 19]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.2", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "equals", "field": "4.1.4", "value": 18},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.1", "min_days": 0, "max_days": 0},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "4.3.3", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.3.4", "min_days": 0, "max_days": 0},
                {"op": "in", "field": "4.1.4", "values": [16, 17, 19]},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.2", "min_days": 0, "max_days": 60},
            ]},
            {"op": "all", "rules": [
                {"op": "between", "field": "4.3.3", "min": 4, "max": 7},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.3.4", "min_days": 0, "max_days": 0},
                {"op": "equals", "field": "4.1.4", "value": 18},
                {"op": "date_interval", "start_field": "4.1", "end_field": "4.1.1", "min_days": 0, "max_days": 60},
            ]},
        ]},
    },
    5: {"name": "肝癌患者接受手術切除其邊緣無殘留癌細胞的比率。", "type": "positive", "denominator": {"op": "any", "rules": [{"op": "between", "field": "4.1.4", "min": 22, "max": 60}, {"op": "between", "field": "4.1.4", "min": 65, "max": 66}, {"op": "equals", "field": "4.1.4", "value": 90}]}, "numerator": {"op": "text_equals", "field": "4.1.5", "value": "0"}},
    6: {"name": "肝細胞癌 BCLC stage 0+A+B 病患等待治療時間在 45 天以內。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "equals", "field": "3.17", "value": 6}, {"op": "first_char_in", "field": "3.19", "values": ["0", "A", "B"]}, {"op": "in", "field": "2.3.2", "values": [1, 3]}]}, "numerator": {"op": "date_interval", "start_field": "2.5", "end_field": "4.1", "min_days": 0, "max_days": 45}},
}

COLON_RECTUM_CANCER_RULES: dict[int, dict[str, Any]] = {
    2: {"name": "病理期別第 I-III 期結腸癌手術病人，淋巴結病理檢查 12 顆以上的比率。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "text_starts_with", "field": "2.6", "values": ["C18"]}, {"op": "first_char_in", "field": "3.13", "values": ["1", "2", "3"]}, {"op": "between", "field": "4.1.4", "min": 30, "max": 90}]}, "numerator": {"op": "between", "field": "2.14", "min": 12, "max": 90}},
    3: {"name": "第 II、III 期直腸癌病人，6 週內開始治療的比率。", "type": "positive", "denominator": {"op": "all", "rules": [{"op": "text_starts_with", "field": "2.6", "values": ["C19", "C20"]}, {"op": "equals", "field": "2.3", "value": 1}, {"op": "first_char_in", "field": "3.7", "values": ["2", "3"]}]}, "numerator": {"op": "date_interval", "start_field": "2.12", "end_field": "4.1", "min_days": 0, "max_days": 42}},
}

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
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "valid_date", "field": "2.12"},
                {"op": "text_not_in", "field": "4.4", "values": ["7"]},
                {"op": "valid_date", "field": "4.1"},
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "2.12",
            "end_field": "4.1",
        },
    },
    4: {
        "name": "胰臟癌病人確診後30天內開始治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "2.3", "value": "1"},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "valid_date", "field": "2.12"},
                {"op": "text_not_in", "field": "4.4", "values": ["7"]},
                {"op": "valid_date", "field": "4.1"},
            ],
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "2.5",
            "end_field": "4.1",
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
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
                {"op": "text_not_in", "field": "4.1.5.1", "values": ["988", "991", "999"]},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "text_equals", "field": "4.1.5", "value": "0"},
                {"op": "between", "field": "4.1.5.1", "min": 10, "max": 980},
            ],
        },
    },
    6: {
        "name": "胰臟癌治癒性手術淋巴結病理檢查12顆以上的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
                {"op": "text_not_in", "field": "4.1.5.1", "values": ["988", "991", "999"]},
                {"op": "text_not_in", "field": "4.1.5", "values": ["3", "A", "B"]},
            ],
        },
        "numerator": {
            "op": "greater_than_or_equal",
            "field": "2.14",
            "value": 12,
        },
    },
    7: {
        "name": "胰臟癌前置切除手術後接受輔助型化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
                {"op": "text_in", "field": "4.1.5", "values": ["0", "2", "5", "C", "D", "E"]},
                {
                    "op": "not",
                    "rule": {"op": "first_char_in", "field": "3.7", "values": ["4"]},
                },
                {
                    "op": "not",
                    "rule": {
                        "op": "date_after",
                        "start_field": "4.3.4",
                        "end_field": "4.1.2",
                    },
                },
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "4.1.2",
            "end_field": "4.3.4",
        },
    },
    8: {
        "name": "臨床第三期胰臟癌手術前接受前導化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "text_not_in", "field": "4.4", "values": ["7"]},
                {"op": "first_char_in", "field": "3.7", "values": ["3"]},
                {"op": "first_char_in", "field": "3.4", "values": ["4"]},
                {"op": "first_char_in", "field": "3.5", "values": ["0", "1", "2", "3"]},
                {"op": "first_char_in", "field": "3.6", "values": ["0"]},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 80},
                {"op": "valid_date", "field": "4.1.2"},
            ],
        },
        "numerator": {
            "op": "date_after",
            "start_field": "4.3.4",
            "end_field": "4.1.2",
        },
    },
    9: {
        "name": "臨床第三或第四期胰臟癌接受全身性化療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "2.8", "values": PANCREATIC_ADENOCARCINOMA_HISTOLOGIES},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "text_equals", "field": "2.9", "value": "3"},
                {"op": "first_char_in", "field": "3.7", "values": ["3", "4"]},
            ],
        },
        "numerator": {"op": "valid_date", "field": "4.3.4"},
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
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "text_equals", "field": "2.9", "value": "2"},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "4.1.4", "min": 20, "max": 29},
                {"op": "not_in", "field": "4.1.4", "values": [25]},
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
                    "field": "3.19",
                    "values": [
                        "1A2", "1B", "1B1", "1B2", "1B3", "2", "2A", "2A1",
                        "2A2", "2B", "3", "3A", "3B", "3C1", "3C2", "4A", "4B",
                    ],
                },
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {
                    "op": "dates_equal",
                    "left_field": "4.1",
                    "right_field": "4.1.2",
                },
            ],
        },
        "numerator": {
            "op": "between",
            "field": "2.14",
            "min": 12,
            "max": 90,
        },
    },
    3: {
        "name": "子宮頸癌首次接受放射治療於63天內完成的比率",
        "type": "positive",
        "denominator": {
            "op": "dates_equal",
            "left_field": "4.1",
            "right_field": "4.2.1.3",
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "4.2.1.3",
            "end_field": "????????",
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
                {"op": "text_not_in", "field": "3.19", "values": ["4B"]},
                {
                    "op": "dates_equal",
                    "left_field": "4.1",
                    "right_field": "4.2.1.3",
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "4.2.1.2",
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
                    "field": "3.19",
                    "values": ["1B2", "1B3", "2A2", "2B", "3", "3A", "3B", "3C1", "3C2", "4A"],
                },
                {
                    "op": "dates_equal",
                    "left_field": "4.1",
                    "right_field": "4.2.1.3",
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "????????????",
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
                {"op": "text_in", "field": "3.7", "values": ["1B", "2A", "2B"]},
                {"op": "text_equals", "field": "is_nsclc", "value": "TRUE"},
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {"op": "text_not_in", "field": "8.5", "values": ["988"]},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "8.5",
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
                {"op": "text_equals", "field": "3.7", "value": "3A"},
                {"op": "text_equals", "field": "is_nsclc", "value": "TRUE"},
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {"op": "text_not_in", "field": "8.5", "values": ["988"]},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "between",
            "field": "8.5",
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
                {"op": "first_char_in", "field": "3.7", "values": ["1", "2"]},
                {"op": "between", "field": "4.1.4", "min": 20, "max": 90},
                {"op": "text_in", "field": "3.11", "values": ["0", "0A", "0B", "0C", "0D"]},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "equals", "field": "2.15", "value": 0},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "4.1.7",
            "values": ["2", "6", "7"],
        },
    },
    3: {
        "name": "乳房全切除且淋巴結陽性4顆以上病人接受放射治療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "2.15", "min": 4, "max": 90},
                {"op": "between", "field": "4.1.4", "min": 30, "max": 72},
                {"op": "first_char_in", "field": "SUMMARY_STAGE", "values": ["0", "1", "2", "3"]},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
            ],
        },
        "numerator": {
            "op": "all",
            "rules": [
                {"op": "text_in", "field": "????????", "values": ["00", "04", "09", "10"]},
                {"op": "greater_than_or_equal", "field": "4.2.2.2.2", "value": 4000},
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
                            "field": "8.7",
                            "values": ["103", "201", "301", "401", "501", "901"],
                        },
                        {
                            "op": "all",
                            "rules": [
                                {"op": "date_year_between", "field": "2.5", "min": 2023, "max": 2023},
                                {"op": "text_in", "field": "8.7", "values": ["511", "521", "591"]},
                            ],
                        },
                        {
                            "op": "all",
                            "rules": [
                                {"op": "date_year_between", "field": "2.5", "min": 2024, "max": 2024},
                                {"op": "text_in", "field": "8.7", "values": ["530", "531", "532"]},
                            ],
                        },
                    ],
                },
                {"op": "between", "field": "2.15", "min": 1, "max": 97},
                {"op": "text_in", "field": "2.3", "values": ["1", "2"]},
                {"op": "between", "field": "4.1.4", "min": 10, "max": 90},
                {
                    "op": "not",
                    "rule": {"op": "first_char_in", "field": "SUMMARY_STAGE", "values": ["4"]},
                },
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "4.3.14",
            "values": ["01", "20", "21", "31"],
        },
    },
}
