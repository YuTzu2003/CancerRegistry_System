from modules.special_rules.special_validate_rules import (
    apply_class_case_rules,
    stop_if_too_many_date_errors,
)


def apply_special_rules(df, error_mask, rules, alias_mapping, fmt):
    error_mask = apply_class_case_rules(
        df=df,
        error_mask=error_mask,
        rules=rules,
        alias_mapping=alias_mapping,
        fmt=fmt,
    )

    stop_if_too_many_date_errors(
        error_mask=error_mask,
        max_errors=3,
    )

    return error_mask