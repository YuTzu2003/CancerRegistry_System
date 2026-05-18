from modules.special_rules.class_case_rules import apply_class_case_rules


def apply_special_rules(df, error_mask, rules, alias_mapping, fmt):
    error_mask = apply_class_case_rules(
        df=df,
        error_mask=error_mask,
        rules=rules,
        alias_mapping=alias_mapping,
        fmt=fmt,
    )
    
    return error_mask