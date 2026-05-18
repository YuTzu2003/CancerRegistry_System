import re
import pandas as pd


def clean_value(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.lower() == "nan":
        return ""

    if value.endswith(".0"):
        value = value[:-2]

    return value


def id_to_tuple(id_str):
    """
    例如：
    7.10 -> (7, 10)
    7.5  -> (7, 5)

    這樣才不會發生字串比較錯誤：
    例如 7.10 被誤判小於 7.5
    """
    return tuple(
        int(x)
        for x in str(id_str).strip().split(".")
        if x.isdigit()
    )


def id_between(field_id, start_id, end_id):
    return id_to_tuple(start_id) <= id_to_tuple(field_id) <= id_to_tuple(end_id)


def get_rule_length(rule):
    return int(rule.get("length") or rule.get("max_length") or 0)


def make_all_9(rule):
    length = get_rule_length(rule)
    return "9" * length


def normalize_col_name(name):
    return re.sub(r"\s+", "", str(name).strip())


def build_id_to_column(df, rules, alias_mapping):
    """
    建立：
    欄位序號 ID -> Excel 原始欄位名稱

    例如：
    2.3 -> 個案分類欄位
    7.3 -> 某個實際 Excel 欄位
    """
    clean_alias_mapping = {
        normalize_col_name(k): v
        for k, v in alias_mapping.items()
    }

    id_to_col = {}

    for col in df.columns:
        clean_col = normalize_col_name(col)
        rule_name = clean_alias_mapping.get(clean_col)

        if rule_name and rule_name in rules:
            rule = rules[rule_name]
            field_id = str(rule.get("ID", "")).strip()
            id_to_col[field_id] = col

    return id_to_col