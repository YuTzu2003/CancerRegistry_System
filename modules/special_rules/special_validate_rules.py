from modules.special_rules.common import (
    clean_value,
    build_id_to_column,
    id_between,
    make_all_9,
)

from modules.clean_pipeline.validate import (
    parse_cancer_date,
    compare_cancer_date,
)


CLASS_CASE_RULES = {
    # 適用 42 欄位
    # Class 0 / Class 3：
    # 7.1~7.5 以 9 補滿
    "fmt_42": {
        "class_values": ["0", "3"],
        "all_9_ranges": [
            ("7.1", "7.5"),
        ],
        "fixed_value_ranges": [],
    },

    # 適用 45 欄位
    # Class 0 / Class 3：
    # 7.1~7.5 以 9 補滿
    "fmt_45": {
        "class_values": ["0", "3"],
        "all_9_ranges": [
            ("7.1", "7.5"),
        ],
        "fixed_value_ranges": [],
    },

    # 適用 50 欄位
    # Class 0 / Class 3：
    # 7.1~7.10 以 9 補滿
    "fmt_50": {
        "class_values": ["0", "3"],
        "all_9_ranges": [
            ("7.1", "7.10"),
        ],
        "fixed_value_ranges": [],
    },

    # 適用 114 欄位
    # Class 0：
    # 4.1~4.4、7.1~7.5 以 9 補滿
    # 8.1~8.9 以 988 填滿
    # Class 3：
    # 3.1~4.4、7.1~7.5 以 9 補滿
    # 8.1~8.9 以 988 填滿
    "fmt_114": {
        "class_values": ["0", "3"],
        "class_specific": {
            "0": {
                "all_9_ranges": [
                    ("4.1", "4.4"),
                    ("7.1", "7.5"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.9", "988"),
                ],
            },
            "3": {
                "all_9_ranges": [
                    ("3.1", "4.4"),
                    ("7.1", "7.5"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.9", "988"),
                ],
            },
        },
    },

    # 適用 115 欄位
    # Class 0：
    # 4.1~4.5.2、7.1~7.6 以 9 補滿
    # 8.1~8.10 以 988 填滿
    # Class 3：
    # 3.1~4.5.2、7.1~7.6 以 9 補滿
    # 8.1~8.10 以 988 填滿
    "fmt_115": {
        "class_values": ["0", "3"],
        "class_specific": {
            "0": {
                "all_9_ranges": [
                    ("4.1", "4.5.2"),
                    ("7.1", "7.6"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.10", "988"),
                ],
            },
            "3": {
                "all_9_ranges": [
                    ("3.1", "4.5.2"),
                    ("7.1", "7.6"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.10", "988"),
                ],
            },
        },
    },

    # 適用 129 欄位
    # Class 0：
    # 4.1~4.5.2、7.1~7.10 以 9 補滿
    # 8.1~8.20 以 988 填滿
    # Class 3：
    # 3.1~4.5.2、7.1~7.10 以 9 補滿
    # 8.1~8.20 以 988 填滿
    "fmt_129": {
        "class_values": ["0", "3"],
        "class_specific": {
            "0": {
                "all_9_ranges": [
                    ("4.1", "4.5.2"),
                    ("7.1", "7.10"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.20", "988"),
                ],
            },
            "3": {
                "all_9_ranges": [
                    ("3.1", "4.5.2"),
                    ("7.1", "7.10"),
                ],
                "fixed_value_ranges": [
                    ("8.1", "8.20", "988"),
                ],
            },
        },
    },
}


def get_rule_config(fmt, class_value):
    """
    取得不同格式、不同 class 的特殊規則。
    支援兩種寫法：

    1. 全部 class 共用：
       all_9_ranges

    2. class 0 / class 3 分開：
       class_specific
    """
    config = CLASS_CASE_RULES.get(fmt)

    if not config:
        return None

    if class_value not in config.get("class_values", []):
        return None

    if "class_specific" in config:
        return config["class_specific"].get(class_value)

    return config


def apply_class_case_rules(df, error_mask, rules, alias_mapping, fmt):
    """
    欄位序號 2.3：個案分類特殊規則。

    作用：
    1. 當 class = 0 或 class = 3 時
    2. 指定欄位範圍如果用 9 補滿，視為特殊允許值
    3. 指定欄位範圍如果填固定值，例如 988，視為特殊允許值
    4. 符合特殊允許值時，清除原本一般欄位檢查造成的誤判錯誤
    5. 不符合特殊允許值時，不額外標記錯誤，保留原本單欄位檢核結果
    """

    if fmt not in CLASS_CASE_RULES:
        return error_mask

    id_to_col = build_id_to_column(df, rules, alias_mapping)

    class_col = id_to_col.get("2.3")

    if class_col is None:
        return error_mask

    for idx, row in df.iterrows():
        class_value = clean_value(row[class_col])

        rule_config = get_rule_config(fmt, class_value)

        if not rule_config:
            continue

        all_9_ranges = rule_config.get("all_9_ranges", [])
        fixed_value_ranges = rule_config.get("fixed_value_ranges", [])

        for rule_name, rule in rules.items():
            field_id = str(rule.get("ID", "")).strip()
            col = id_to_col.get(field_id)

            if col is None:
                continue

            value = clean_value(row[col])

            # 規則一：指定欄位以 9 補滿
            need_all_9 = any(
                id_between(field_id, start_id, end_id)
                for start_id, end_id in all_9_ranges
            )

            if need_all_9:
                expected = make_all_9(rule)

                if value == expected:
                    # 填對時，清掉一般格式檢查誤判
                    error_mask.at[idx, col] = ""

                continue

            # 規則二：指定欄位填固定值，例如 988
            for start_id, end_id, expected in fixed_value_ranges:
                if id_between(field_id, start_id, end_id):
                    if value == expected:
                        # 填對時，清掉一般格式檢查誤判
                        error_mask.at[idx, col] = ""

                    break

    return error_mask

def apply_date_conditional_rules(df, error_mask, rules, alias_mapping, fmt):
    """
    特殊規則：個案分類(2.3) 與 首次就診(2.4)/最初診斷日期(2.5) 的連動。
    
    1. 個案分類為 0 或 1 時，首次就診日期應等於最初診斷日期。
    2. 個案分類為 2 或 3 時，首次就診日期應晚於最初診斷日期。
    """
    id_to_col = build_id_to_column(df, rules, alias_mapping)
    
    class_col = id_to_col.get("2.3")
    first_visit_col = id_to_col.get("2.4")
    init_diag_col = id_to_col.get("2.5")
    
    if not all([class_col, first_visit_col, init_diag_col]):
        return error_mask
        
    for idx, row in df.iterrows():
        class_val = clean_value(row[class_col])
        if class_val.endswith('.0'): class_val = class_val[:-2]
        
        fv_val = parse_cancer_date(row[first_visit_col])
        id_val = parse_cancer_date(row[init_diag_col])
        
        if not fv_val or not id_val:
            continue
            
        # 條件 A: 個案分類為 0 或 1，兩者應相等
        if class_val in ['0', '1']:
            if fv_val != id_val:
                error_mask.at[idx, first_visit_col] = "special_logic"
                error_mask.at[idx, init_diag_col] = "special_logic"
        
        # 條件 B: 個案分類為 2 或 3，首次就診日期應晚於最初診斷日期
        elif class_val in ['2', '3']:
            # id_val <= fv_val 且 不能相等
            res = compare_cancer_date(row[init_diag_col], row[first_visit_col])
            if res is False or fv_val == id_val:
                error_mask.at[idx, first_visit_col] = "special_logic"
                error_mask.at[idx, init_diag_col] = "special_logic"
                
    return error_mask

def stop_if_too_many_date_errors(error_mask, max_errors=3):

    if error_mask is None or error_mask.empty:
        return 0

    date_error_count = (error_mask == "dateformat").sum().sum()

    return int(date_error_count)
