import pandas as pd
import re
from datetime import datetime

# 驗證
def validate_cell(val, rule):
    if pd.isna(val):
        val = ""
    val = str(val).strip()

    # 雲林台大專屬格式處理(吃檳榔和吸菸欄位)
    if rule.get('digit') is True:
        val = val.replace(',', '')

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

#規則三
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
    DATE_RULES = [
        ('最初診斷日期', '<=', '首次就診日期', '最初診斷日期不可晚於首次就診日期'),
        ('最初診斷日期', '<=', '首次療程開始日期', '最初診斷日期不可晚於首次療程開始日期'),
        ('首次就診日期', '<=', '首次療程開始日期', '首次就診日期不可晚於首次療程開始日期'),
        ('首次療程開始日期', '<=', '首次手術日期', '首次療程開始日期不可晚於首次手術日期'),
        ('首次療程開始日期', '<=', '申報醫院化學治療開始日期', '首次療程開始日期不可晚於申報醫院化學治療開始日期'),
        ('首次療程開始日期', '<=', '原發部位最確切的手術切除日期', '首次療程開始日期不可晚於原發部位最確切的手術切除日期'),
        ('首次療程開始日期', '<=', '放射治療開始日期', '首次療程開始日期不可晚於放射治療開始日期'),
    ]

    errors = []
    error_fields = set()
    for d1_field, op, d2_field, error_msg in DATE_RULES:
        if d1_field in row and d2_field in row:

            d1_val = parse_cancer_date(row[d1_field])
            d2_val = parse_cancer_date(row[d2_field])

            if d1_val and d2_val:
                if op == '<=' and d1_val > d2_val:
                    errors.append(error_msg)
                    error_fields.add(d1_field)
                    error_fields.add(d2_field)

    return list(error_fields), errors

def check_error_type(val, rule):
    is_valid = validate_cell(val, rule)
    if is_valid:
        return ""  
    
    if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
        return "missing"
    else:
        return "format"
    

if __name__ == '__main__': 
    alias_mapping, all_fields = field_mapping(target_column)
    df = process_data(INPUT_FILE, alias_mapping, all_fields, target_sheet=TARGET_SHEET)    
    print(df.columns) 

    df['日期錯誤'] = df.apply(validate_date_rules, axis=1)
    df_error = df[df['日期錯誤'].apply(lambda x: len(x) > 0)]
    for idx, row in df_error.iterrows():
        print(f"第{idx}筆錯誤: {row['日期錯誤']}")
    df_error.to_excel("data/date_error_details.xlsx", index=False)

    COL_SITE = 'site'
    COL_HIST = 'hist'
    COL_DIDIAG = 'didiag'