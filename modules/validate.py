import pandas as pd
import re
from datetime import datetime

# 驗證
def validate_cell(val, rule):
    if pd.isna(val):
        val = ""
    val = str(val).strip()

    if 'SV' in rule:
        if isinstance(rule['SV'], list) and val in rule['SV']:
            return True
        elif val == rule['SV']:
            return True

    if 'length' in rule and len(val) != rule['length']:
        return False
    
    if 'digit' in rule and rule['digit'] and not val.isdigit():
        return False
    
    if 'max_length' in rule and len(val) > rule['max_length']:
        return False
    
    if 'regex' in rule and not re.match(rule['regex'], val):
        return False

    if 'choices' in rule and val not in rule['choices']:
        return False
    
    if 'is_date' in rule:
        try:
            datetime.strptime(val, rule['is_date'])
        except ValueError:
            return False
        
    if 'range' in rule:
        try:
            num_val = int(val)
            min_val, max_val = rule['range']
            if not (min_val <= num_val <= max_val):
                return False
        except ValueError:
            return False

    if 'pattern_range' in rule:
        if isinstance(rule['pattern_range'], str):
            conditions = [c.strip() for c in rule['pattern_range'].split(',')]
            for condition in conditions:
                if '-' in condition:
                    start_val, end_val = condition.split('-', 1)
                    if len(val) == len(start_val) and start_val <= val <= end_val:
                        return True
                elif val == condition:
                    return True

    return True

#規則三
DATE_RULES = [
    ('didiag', '<=', 'dcont', '最初診斷日期不可晚於首次就診日期'),
    ('didiag', '<=', 'dtrt_1st', '最初診斷日期不可晚於首次療程開始日期'),
    ('dcont', '<=', 'dtrt_1st', '首次就診日期不可晚於首次療程開始日期'),
    ('dtrt_1st', '<=', 'dop_1st', '首次療程開始日期不可晚於首次手術日期'),
    ('dtrt_1st', '<=', 'dchem', '首次療程開始日期不可晚於申報醫院化學治療開始日期'),
    ('dtrt_1st', '<=', 'dop_mds', '首次療程開始日期不可晚於原發部位最確切的手術切除日期'),
    ('dtrt_1st', '<=', 'drt_1st', '首次療程開始日期不可晚於放射治療開始日期'),
]

def parse_cancer_date(date_val):
    if pd.isna(date_val):
        return None

    date_str = str(date_val).strip()

    # 忽略無效日期
    if date_str == '0000/00/00':
        return None

    if len(date_str) == 8 and date_str.isdigit():
        # 例：20220199 → 20220115
        if date_str[6:8] == '99':
            date_str = date_str[:6] + '15'

    return date_str


def validate_date_rules(row):
    errors = []

    for d1_field, op, d2_field, error_msg in DATE_RULES:
        if d1_field in row and d2_field in row:

            d1_val = parse_cancer_date(row[d1_field])
            d2_val = parse_cancer_date(row[d2_field])

            if d1_val and d2_val:
                if op == '<=' and d1_val > d2_val:
                    errors.append(error_msg)

    return errors