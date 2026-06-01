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

    has_content_rule = False
    passed_content_rule = False
    
    if 'regex' in rule:
        has_content_rule = True
        if re.match(rule['regex'], val):
            passed_content_rule = True

    if 'patterns' in rule:
        has_content_rule = True
        for pattern_rule in rule['patterns']:
            if re.match(pattern_rule['regex'], val):
                passed_content_rule = True
                break

    if 'pattern_range' in rule and not passed_content_rule:
        has_content_rule = True
        conditions = [c.strip() for c in rule['pattern_range'].split(',')]
        for condition in conditions:
            if '-' in condition:
                start_val, end_val = condition.split('-', 1)
                if len(val) == len(start_val) and start_val <= val <= end_val:
                    passed_content_rule = True
                    break
            elif val == condition:
                passed_content_rule = True
                break

    if 'range' in rule and not passed_content_rule:
        has_content_rule = True
        try:
            num_val = int(val)
            min_val, max_val = rule['range']
            if min_val <= num_val <= max_val:
                passed_content_rule = True
        except:
            pass
    
    if 'choices' in rule and not passed_content_rule:
        has_content_rule = True
        if val in rule['choices']:
            passed_content_rule = True


    if has_content_rule and not passed_content_rule:
        return False

    if 'is_date' in rule:
        check_val = val
        if len(check_val) == 8 and check_val.endswith('99'):
            check_val = check_val[:-2] + '15'
        try:
            datetime.strptime(check_val, '%Y%m%d')
        except ValueError:
            return False

    return True

#規則三
def parse_cancer_date(date_val):
    if pd.isna(date_val) or str(date_val).strip().lower() == 'nan':
        return None

    date_str = str(date_val).strip().replace('/', '').replace('-', '')

    if date_str.endswith('.0'):
        date_str = date_str[:-2]

    invalid_dates = ['00000000', '99999999', '88888888', '0', '0.0', '']

    # 忽略無效日期
    if date_str in invalid_dates:
        return None

    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    
    return None

def compare_cancer_date(date1, date2):

    d1 = parse_cancer_date(date1)
    d2 = parse_cancer_date(date2)

    if d1 is None or d2 is None:
        return None

    # 只要其中一個日期的 DD 是 99，就只比較 CCYYMM
    if d1[6:8] == '99' or d2[6:8] == '99':
        return d1[:6] <= d2[:6]

    # 一般日期才比較完整 CCYYMMDD
    return d1 <= d2

def validate_date_rules(row, alias_mapping):
    std_row = {}
    std_to_orig = {}  
    for col_name, val in row.items():
        clean_col = str(col_name).strip()
        std_name = alias_mapping.get(clean_col, clean_col)
        std_row[std_name] = val
        std_to_orig[std_name] = col_name

    DATE_RULES = [
        ('最初診斷日期', '<=', '首次就診日期', '最初診斷日期不可晚於首次就診日期'),
        ('最初診斷日期', '<=', '首次顯微鏡檢證實日期', '最初診斷日期不可晚於首次顯微鏡檢證實日期'),
        ('最初診斷日期', '<=', '首次療程開始日期', '最初診斷日期不可晚於首次療程開始日期 '),
        ('最初診斷日期', '<=', '首次手術日期', '最初診斷日期不可晚於首次手術日期'),
        ('最初診斷日期', '<=', '原發部位最確切的手術切除日期', '最初診斷日期不可晚於原發部位最確切的手術切除日期'),
        ('最初診斷日期', '<=', '放射治療開始日期', '最初診斷日期不可晚於放射治療開始日期'),
        ('最初診斷日期', '<=', '放射治療結束日期', '最初診斷日期不可晚於放射治療結束日期'),
        ('最初診斷日期', '<=', '全身性治療開始日期', '最初診斷日期不可晚於全身性治療開始日期'),
        ('最初診斷日期', '<=', '申報醫院化學治療開始日期', '最初診斷日期不可晚於申報醫院化學治療開始日期'),
        ('最初診斷日期', '<=', '申報醫院荷爾蒙/類固醇治療開始日期', '最初診斷日期不可晚於申報醫院荷爾蒙/類固醇治療開始日期'),
        ('最初診斷日期', '<=', '申報醫院免疫治療開始日期', '最初診斷日期不可晚於申報醫院免疫治療開始日期'),
        ('最初診斷日期', '<=', '申報醫院骨髓/幹細胞移植或內分泌處置開始日期', '最初診斷日期不可晚於申報醫院骨髓/幹細胞移植或內分泌處置開始日期'),
        ('最初診斷日期', '<=', '申報醫院標靶治療開始日期', '最初診斷日期不可晚於申報醫院標靶治療開始日期'),
        ('最初診斷日期', '<=', '其他治療開始日期', '最初診斷日期不可晚於其他治療開始日期'),
        ('最初診斷日期', '<=', '首次復發或癌症狀態追蹤日期', '最初診斷日期不可晚於首次復發或癌症狀態追蹤日期'),
        ('最初診斷日期', '<=', '最後聯絡或死亡日期', '最初診斷日期不可晚於最後聯絡或死亡日期'),
        ('首次就診日期', '<=', '首次療程開始日期', '首次就診日期不可晚於首次療程開始日期'),
        ('首次就診日期', '<=', '首次手術日期', '首次就診日期不可晚於首次手術日期'),
        ('首次就診日期', '<=', '原發部位最確切的手術切除日期', '首次就診日期不可晚於原發部位最確切的手術切除日期'),        
        ('首次就診日期', '<=', '放射治療開始日期', '首次就診日期不可晚於放射治療開始日期'),
        ('首次就診日期', '<=', '放射治療結束日期', '首次就診日期不可晚於放射治療結束日期'),
        ('首次就診日期', '<=', '全身性治療開始日期', '首次就診日期不可晚於全身性治療開始日期'),
        ('首次就診日期', '<=', '申報醫院化學治療開始日期', '首次就診日期不可晚於申報醫院化學治療開始日期'),
        ('首次就診日期', '<=', '申報醫院荷爾蒙/類固醇治療開始日期', '首次就診日期不可晚於申報醫院荷爾蒙/類固醇治療開始日期'),
        ('首次就診日期', '<=', '申報醫院免疫治療開始日期', '首次就診日期不可晚於申報醫院免疫治療開始日期'),
        ('首次就診日期', '<=', '申報醫院骨髓/幹細胞移植或內分泌處置開始日期', '首次就診日期不可晚於申報醫院骨髓/幹細胞移植或內分泌處置開始日期'),
        ('首次就診日期', '<=', '申報醫院標靶治療開始日期', '首次就診日期不可晚於申報醫院標靶治療開始日期'),
        ('首次就診日期', '<=', '其他治療開始日期', '首次就診日期不可晚於其他治療開始日期'),
        ('首次就診日期', '<=', '首次復發或癌症狀態追蹤日期', '首次就診日期不可晚於首次復發或癌症狀態追蹤日期'),        
        ('首次就診日期', '<=', '最後聯絡或死亡日期', '首次就診日期不可晚於最後聯絡或死亡日期'),
        ('首次療程開始日期', '<=', '首次手術日期', '首次療程開始日期不可晚於首次手術日期'),
        ('首次療程開始日期', '<=', '原發部位最確切的手術切除日期', '首次療程開始日期不可晚於原發部位最確切的手術切除日期'),
        ('首次療程開始日期', '<=', '放射治療開始日期', '首次療程開始日期不可晚於放射治療開始日期'),
        ('首次療程開始日期', '<=', '放射治療結束日期', '首次療程開始日期不可晚於放射治療結束日期'),
        ('首次療程開始日期', '<=', '全身性治療開始日期', '首次療程開始日期不可晚於全身性治療開始日期'),
        ('首次療程開始日期', '<=', '申報醫院化學治療開始日期', '首次療程開始日期不可晚於申報醫院化學治療開始日期'),
        ('首次療程開始日期', '<=', '申報醫院荷爾蒙/類固醇治療開始日期', '首次療程開始日期不可晚於申報醫院荷爾蒙/類固醇治療開始日期'),
        ('首次療程開始日期', '<=', '申報醫院免疫治療開始日期', '首次療程開始日期不可晚於申報醫院免疫治療開始日期'),
        ('首次療程開始日期', '<=', '申報醫院骨髓/幹細胞移植或內分泌處置開始日期', '首次療程開始日期不可晚於申報醫院骨髓/幹細胞移植或內分泌處置開始日期'),
        ('首次療程開始日期', '<=', '申報醫院標靶治療開始日期', '首次療程開始日期不可晚於申報醫院標靶治療開始日期'),
        ('首次療程開始日期', '<=', '其他治療開始日期', '首次療程開始日期不可晚於其他治療開始日期'),
        ('首次療程開始日期', '<=', '首次復發或癌症狀態追蹤日期', '首次療程開始日期不可晚於首次復發或癌症狀態追蹤日期'),
        ('首次療程開始日期', '<=', '最後聯絡或死亡日期', '首次療程開始日期不可晚於最後聯絡或死亡日期'),
        ('放射治療開始日期', '<=', '放射治療結束日期', '放射治療開始日期不可晚於放射治療結束日期'),
    ]

    errors = []
    error_fields = set()
    for d1_field, op, d2_field, error_msg in DATE_RULES:
        if d1_field in std_row and d2_field in std_row:
            d1_val = parse_cancer_date(std_row[d1_field])
            d2_val = parse_cancer_date(std_row[d2_field])

            if d1_val and d2_val:
                if op == '<=':
                    result = compare_cancer_date(
                        std_row[d1_field],
                        std_row[d2_field]
                    )

                    if result is False:
                        errors.append(error_msg)
                        error_fields.add(std_to_orig[d1_field])
                        error_fields.add(std_to_orig[d2_field])
    return list(error_fields), errors

def check_error_type(val, rule):
    is_valid = validate_cell(val, rule)
    if is_valid:
        return ""  
    
    if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
        return "missing"
    else:
        return "format"
