from __future__ import annotations

from typing import Any

#口腔癌
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

#食道癌
ESOPHAGEAL_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "食道癌病人手術切除標本切除端無殘餘侵襲性癌細胞(R0 切除)的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                # 2E、2M 無法轉成整數，本來就不會符合 between；保留此規則以對應規格。
                {"op": "text_not_in", "field": "surgery_code", "values": ["2E", "2M"]},
                {"op": "text_equals", "field": "clinical_m", "value": "0"},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "surgical_margin",
            "values": ["0", "C", "D", "E"],
        },
    },
    2: {
        "name": "食道切除標本淋巴結病理檢查 15 顆(含)以上的比率。",
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
        "name": "接受食道切除手術的病患於術後 30 天內死亡的比率。",
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
        "name": "cT4N0M0 or cTanyN1-3M0 接受食道切除手術的病患有接受引導性化放療的比率",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 30, "max": 80},
                {"op": "text_equals", "field": "sequence_number", "value": "01"},
                {
                    "op": "any",
                    "rules": [
                        # A：cT4N0M0定義
                        {
                            "op": "all",
                            "rules": [
                                {"op": "first_char_in", "field": "clinical_t", "values": ["4"]},
                                {"op": "first_char_in", "field": "clinical_n", "values": ["0"]},
                                {"op": "first_char_in", "field": "clinical_m", "values": ["0"]},
                            ],
                        },
                        # B：cTanyN1-3M0定義
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

#胃癌
GASTRIC_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "臨床分期為第 I~ IIIC 期之胃及食道賁門(EC junction)癌病人接受手術切除(含內視鏡切除術)後，巨觀下完全切除且顯微鏡下手術邊界為陰性的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "first_char_in", "field": "clinical_stage", "values": ["1", "2", "3"]},
                {
                    "op": "any",
                    "rules": [
                        {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                        {"op": "text_in", "field": "surgery_code", "values": ["2E", "2M"]},
                    ],
                },
                {"op": "equals", "field": "palliative_care", "value": 0},
                {"op": "text_not_in", "field": "surgical_margin", "values": ["7", "9"]},
            ],
        },
        "numerator": {
            "op": "text_in",
            "field": "surgical_margin",
            "values": ["0", "C", "D", "E"],
        },
    },
    3: {
        "name": "胃及食道賁門癌接受胃切除手術(含內視鏡切除術)的病患於術後 30 天內死亡的比率。",
        "type": "negative",
        "denominator": {
            "op": "all",
            "rules": [
                {
                    "op": "any",
                    "rules": [
                        {"op": "between", "field": "surgery_code", "min": 20, "max": 90},
                        {"op": "text_in", "field": "surgery_code", "values": ["2E", "2M"]},
                    ],
                },
                {"op": "equals", "field": "palliative_care", "value": 0},
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
                    "max_days": 29,
                },
            ],
        },
    },
    4: {
        "name": "病理期別第 II-III 期胃及食道賁門(EC junction)癌病人接受手術後有做輔助型化療(包含臨床試驗)的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "first_char_in", "field": "pathological_stage", "values": ["2", "3"]},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
                {"op": "text_not_in", "field": "pathology_prefix", "values": ["4", "6"]},
            ],
        },
        "numerator": {
            "op": "date_on_or_after",
            "start_field": "surgery_date",
            "end_field": "chemotherapy_date",
        },
    },
}

# 肝癌（肝細胞癌）
LIVER_CANCER_RULES: dict[int, dict[str, Any]] = {
    1: {
        "name": "極早期和早期肝癌(肝細胞癌)病人接受治癒性療法的比率。",
        "type": "positive",
        # BCLC stage 0、A，且首次療程於本院完成的肝細胞癌個案。
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "treatment_status", "value": 1},
                {"op": "equals", "field": "other_staging_system", "value": 6},
                {"op": "first_char_in", "field": "other_clinical_stage", "values": ["0", "A"]},
            ],
        },
        # 外科或內科治癒性療法；TA(C)E 後 60 天內再接受治癒性療法亦納入。
        "numerator": {
            "op": "any",
            "rules": [
                # A1：手術切除或肝移植。
                {
                    "op": "any",
                    "rules": [
                        {"op": "equals", "field": "surgery_code", "value": 61},
                        {"op": "equals", "field": "surgery_code", "value": 75},
                    ],
                },
                # A2：首次療程即為指定外科治癒性療法。
                {
                    "op": "all",
                    "rules": [
                        {
                            "op": "any",
                            "rules": [
                                {"op": "between", "field": "surgery_code", "min": 20, "max": 25},
                                {"op": "between", "field": "surgery_code", "min": 27, "max": 29},
                                {"op": "between", "field": "surgery_code", "min": 30, "max": 32},
                                {"op": "equals", "field": "surgery_code", "value": 34},
                                {"op": "equals", "field": "surgery_code", "value": 35},
                                {"op": "equals", "field": "surgery_code", "value": 38},
                                {"op": "between", "field": "surgery_code", "min": 50, "max": 52},
                                {"op": "equals", "field": "surgery_code", "value": 54},
                                {"op": "equals", "field": "surgery_code", "value": 55},
                                {"op": "equals", "field": "surgery_code", "value": 59},
                                {"op": "equals", "field": "surgery_code", "value": 60},
                                {"op": "equals", "field": "surgery_code", "value": 66},
                                {"op": "equals", "field": "surgery_code", "value": 90},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
                    ],
                },
                # A3：指定手術方式，三個手術日期皆為同一天。
                {
                    "op": "all",
                    "rules": [
                        {
                            "op": "any",
                            "rules": [
                                {"op": "equals", "field": "surgery_code", "value": 26},
                                {"op": "equals", "field": "surgery_code", "value": 33},
                                {"op": "equals", "field": "surgery_code", "value": 53},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
                        {"op": "date_interval", "start_field": "first_surgery_date", "end_field": "surgery_date", "min_days": 0, "max_days": 0},
                    ],
                },
                # A4：指定手術方式，首次手術至最確切切除日在 60 天內。
                {
                    "op": "all",
                    "rules": [
                        {
                            "op": "any",
                            "rules": [
                                {"op": "equals", "field": "surgery_code", "value": 26},
                                {"op": "equals", "field": "surgery_code", "value": 33},
                                {"op": "equals", "field": "surgery_code", "value": 53},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
                        {"op": "date_interval", "start_field": "first_surgery_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
                    ],
                },
                # A5：TA(C)E 後 60 天內接受指定外科治癒性療法。
                {
                    "op": "all",
                    "rules": [
                        {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                        {
                            "op": "any",
                            "rules": [
                                {"op": "between", "field": "surgery_code", "min": 20, "max": 25},
                                {"op": "between", "field": "surgery_code", "min": 30, "max": 32},
                                {"op": "between", "field": "surgery_code", "min": 50, "max": 52},
                                {"op": "equals", "field": "surgery_code", "value": 60},
                                {"op": "equals", "field": "surgery_code", "value": 66},
                                {"op": "equals", "field": "surgery_code", "value": 90},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
                    ],
                },
                # A6：TA(C)E 後 60 天內接受其他指定外科治癒性療法。
                {
                    "op": "all",
                    "rules": [
                        {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                        {
                            "op": "any",
                            "rules": [
                                {"op": "equals", "field": "surgery_code", "value": 26},
                                {"op": "equals", "field": "surgery_code", "value": 33},
                                {"op": "equals", "field": "surgery_code", "value": 53},
                                {"op": "between", "field": "surgery_code", "min": 27, "max": 29},
                                {"op": "equals", "field": "surgery_code", "value": 34},
                                {"op": "equals", "field": "surgery_code", "value": 35},
                                {"op": "equals", "field": "surgery_code", "value": 38},
                                {"op": "equals", "field": "surgery_code", "value": 54},
                                {"op": "equals", "field": "surgery_code", "value": 55},
                                {"op": "equals", "field": "surgery_code", "value": 59},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 60},
                    ],
                },
                # B1：首次療程即為指定內科治癒性療法。
                {
                    "op": "all",
                    "rules": [
                        {
                            "op": "any",
                            "rules": [
                                {"op": "equals", "field": "surgery_code", "value": 16},
                                {"op": "equals", "field": "surgery_code", "value": 17},
                                {"op": "equals", "field": "surgery_code", "value": 19},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 0},
                    ],
                },
                # B2：首次療程即為手術方式 18。
                {
                    "op": "all",
                    "rules": [
                        {"op": "equals", "field": "surgery_code", "value": 18},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 0},
                    ],
                },
                # B3：TA(C)E 後 60 天內接受指定內科治癒性療法。
                {
                    "op": "all",
                    "rules": [
                        {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                        {
                            "op": "any",
                            "rules": [
                                {"op": "equals", "field": "surgery_code", "value": 16},
                                {"op": "equals", "field": "surgery_code", "value": 17},
                                {"op": "equals", "field": "surgery_code", "value": 19},
                            ],
                        },
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "surgery_date", "min_days": 0, "max_days": 60},
                    ],
                },
                # B4：TA(C)E 後 60 天內接受手術方式 18。
                {
                    "op": "all",
                    "rules": [
                        {"op": "between", "field": "chemotherapy_code", "min": 4, "max": 7},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "chemotherapy_date", "min_days": 0, "max_days": 0},
                        {"op": "equals", "field": "surgery_code", "value": 18},
                        {"op": "date_interval", "start_field": "first_treatment_date", "end_field": "first_surgery_date", "min_days": 0, "max_days": 60},
                    ],
                },
            ],
        },
    },
    5: {
        "name": "肝癌患者接受手術切除其邊緣無殘留癌細胞的比率。",
        "type": "positive",
        "denominator": {
            "op": "any",
            "rules": [
                {"op": "between", "field": "surgery_code", "min": 22, "max": 60},
                {"op": "between", "field": "surgery_code", "min": 65, "max": 66},
                {"op": "equals", "field": "surgery_code", "value": 90},
            ],
        },
        "numerator": {"op": "text_equals", "field": "surgical_margin", "value": "0"},
    },
    6: {
        "name": "肝癌(肝細胞癌)BCLC stage 0+A+B 病患等待治療時間在 45 天以內。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "equals", "field": "other_staging_system", "value": 6},
                {"op": "first_char_in", "field": "other_clinical_stage", "values": ["0", "A", "B"]},
                {"op": "any", "rules": [
                    {"op": "equals", "field": "treatment_status", "value": 1},
                    {"op": "equals", "field": "treatment_status", "value": 3},
                ]},
            ],
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "diagnosis_date",
            "end_field": "first_treatment_date",
            "min_days": 0,
            "max_days": 45,
        },
    },
}

# 大腸直腸癌
COLON_RECTUM_CANCER_RULES: dict[int, dict[str, Any]] = {
    2: {
        "name": "病理期別第 I-III 期結腸癌(Colon Ca)手術病人，淋巴結病理檢查 12 顆以上的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_starts_with", "field": "site", "values": ["C18"]},
                {"op": "first_char_in", "field": "pathological_stage", "values": ["1", "2", "3"]},
                {"op": "between", "field": "surgery_code", "min": 30, "max": 90},
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
        "name": "第 II、III 期(臨床期別為主)直腸癌(Rectum Ca)病人，6 週內開始治療(手術或放療或 CCRT)的比率。",
        "type": "positive",
        "denominator": {
            "op": "all",
            "rules": [
                {"op": "text_starts_with", "field": "site", "values": ["C19", "C20"]},
                {"op": "equals", "field": "case_classification", "value": 1},
                {"op": "first_char_in", "field": "clinical_stage", "values": ["2", "3"]},
            ],
        },
        "numerator": {
            "op": "date_interval",
            "start_field": "microscopic_confirmation_date",
            "end_field": "first_treatment_date",
            "min_days": 0,
            "max_days": 42,
        },
    },
}