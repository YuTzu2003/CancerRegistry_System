from modules.special_rules.common import (
    clean_value,
    build_id_to_column,
    id_between,
    make_all_9,
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
    2. 指定欄位範圍必須用 9 補滿
    3. 指定欄位範圍必須填固定值，例如 988
    4. 如果填對，清除原本一般欄位檢查造成的誤判錯誤
    5. 如果填錯，標記為 dateformat
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
                else:
                    error_mask.at[idx, col] = "dateformat"

                continue

            # 規則二：指定欄位填固定值，例如 988
            for start_id, end_id, expected in fixed_value_ranges:
                if id_between(field_id, start_id, end_id):
                    if value == expected:
                        # 填對時，清掉一般格式檢查誤判
                        error_mask.at[idx, col] = ""
                    else:
                        error_mask.at[idx, col] = "dateformat"

                    break

    return error_mask

def stop_if_too_many_date_errors(error_mask, max_errors=3):
    """
    error_mask 裡面如果有 dateformat，代表日期格式或日期邏輯錯誤。
    預設超過或等於 3 筆時，要求使用者先修正。
    """

    if error_mask is None or error_mask.empty:
        return

    date_error_count = (error_mask == "dateformat").sum().sum()

    if date_error_count >= max_errors:
        raise ValueError(
            f"日期邏輯錯誤共有 {date_error_count} 筆，已達系統限制 ({max_errors} 筆)\n"
            f"請先修正錯誤的日期資料，完成修正後再進行後續資料清洗作業"
        )