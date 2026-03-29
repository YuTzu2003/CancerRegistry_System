import pandas as pd
import re
from datetime import datetime

# 驗證
def validate_cell(val, rule):
    if pd.isna(val):
        val = ""
    val = str(val).strip()

    # 日期標準化
    if 'is_date' in rule:
        if isinstance(val, pd.Timestamp):
            val = val.strftime('%Y%m%d')
        else:
            val = re.sub(r'[-/]', '', val)

    if 'SV' in rule:
        sv_list = rule['SV']
        if isinstance(sv_list, str):
            sv_list = [v.strip() for v in sv_list.split(',')]
        if val in sv_list:
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
        check_val = val
        if len(check_val) == 8 and check_val.endswith('99'):
            check_val = check_val[:-2] + '15'
        try:
            datetime.strptime(check_val, '%Y%m%d')
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

def check_error_type(val, rule):
    is_valid = validate_cell(val, rule)
    if is_valid:
        return ""  
    
    if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
        return "missing"
    else:
        return "format"

# #規則三
# DATE_RULES = [
#     ('didiag', '<=', 'dcont', '最初診斷日不可晚於首次診斷日'),
#     ('didiag', '<=', 'dtrt_1st', '最初診斷日不可晚於首療開始日'),
#     ('dcont', '<=', 'dtrt_1st', '首次診斷日不可晚於首療開始日'),
#     ('dtrt_1st', '<=', 'dop_1st', '首療開始日不可晚於首次手術日'),
#     ('dtrt_1st', '<=', 'dchem', '首療開始日不可晚於本院化療開始日'),
#     ('dtrt_1st', '<=', 'dop_mds', '首療開始日不可晚於原發最確切手術日'),
#     ('dtrt_1st', '<=', 'drt_1st', '首療開始日不可晚於放療開始日'),
# ]


# def validate_date_rules(row):
#     errors = []
#     for d1_field, op, d2_field, error_msg in DATE_RULES:
#         if d1_field in row and d2_field in row:
#             d1_val = parse_cancer_date(row[d1_field])
#             d2_val = parse_cancer_date(row[d2_field])
            
#             if d1_val and d2_val:
#                 if op == '<=' and d1_val > d2_val:
#                     errors.append(error_msg)
#     return errors