import pandas as pd
import re
from datetime import datetime

RULES = {
    '申報醫院代碼': {
        'field': 'Reporting Hospital Code', 
        'length': 10, 
        'digit': True
    },
    '病歷號碼': {
        'field': 'Medical Record Number', 
        'length': 10, 
        'digit': True, 
        'SV': '9999999999'
    },
    '姓名': {
        'field': 'Name',
        'max_length': 200 
    },
    '身分證統一編號': {
        'field': 'ID Number',
        'length': 10,
        'regex': r'^[A-Za-z]\d{9}$' 
    },
    '性別': {
        'field': 'Sex',
        'length': 1,
        'choices': ['1', '2', '3', '4', '9']
    },
    '出生日期': {
        'field': 'Date of Birth',
        'length': 8,
        'SV': '99999999',
        'is_date': '%Y%m%d'
    },
    '戶籍地代碼': {
        'field': 'Residence Code',
        'length':4,
        'digit': True
    },
    '診斷年齡': {
        'field': 'Age at Diagnosis',
        'length': 3,
        'digit': True,
        'SV': '999',       
        'range': [0, 120] 
    },
    '癌症發生順序號碼': {
        'field': 'Sequence Number',
        'length': 2,
        'digit': True,     
        'range': [1, 99] 
    },
    '個案分類': {
        'field': 'Class of Case',
        'length': 1,
        'digit': True,     
        'choices': ['0', '1', '2', '3', '5', '7', '8', '9']
    },
    '診斷狀態分類': {
        'field': 'Class of Diagnosis Status',
        'length': 1,
        'digit': True,     
        'choices': ['1', '3', '5', '7', '8']
    },
    '首次就診日期': {
        'field': 'Date of First Contact',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
    },
    
}


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
        
    return True