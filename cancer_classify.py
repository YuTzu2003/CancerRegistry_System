import pandas as pd
import re

CANCER_RULES = {
    '口腔癌': {
        'site_include': [(0,6),(8,9),(20,23),(28,29),(30,31),(39,41),(48,50),(58,59),(60,62),(68,69)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '口咽癌': {
        'site_include': [(19,),(24,),(51,52),(90,91),(98,104),(108,109),(142,),(148,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '下咽癌': {
        'site_include': [(129,), (130,132), (138,140)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '主唾液腺癌': {
        'site_include': [(79,81), (88,89)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '鼻咽癌': {
        'site_include': [(110,113),(118,119)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '食道癌': {
        'site_include': [(150,155),(158,159)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '胃癌': {
        'site_include': [(160,166),(168,169)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '結直腸癌': {
        'site_include': [(180,189), (199,), (209,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '結腸癌': {
        'site_include': [(180,189)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '直腸癌': {
        'site_include': [(199,),(209,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肛門癌': {
        'site_include': [(210,212),(218,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肝癌': {
        'site_include': [(220,221)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '胰臟癌(長表)': {
        'site_include': [(250,254),(257,259)],
        'hist_exclude': [(9140,), (9590,9993)],
        'didiag_min': 2022 
    },
    '胰臟癌(短表)': {
        'site_include': [(250,254),(257,259)],
        'hist_exclude': [(9140,), (9590,9993)],
        'didiag_less_than': 2022
    },
    '喉癌': {
        'site_include': [(320,323),(328,329)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肺癌': {
        'site_include': [(339,343),(348,349)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '乳癌': {
        'site_include': [(501,506),(508,509)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '子宮頸癌': {
        'site_include': [(530,531),(538,539)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '子宮體癌': {
        'site_include': [(540,543),(548,549)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '卵巢癌': {
        'site_include': [(569,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '攝護腺癌': {
        'site_include': [(619,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '膀胱癌': {
        'site_include': [(670,679)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '血液腫瘤': {
        'site_include': [(0,809)],
        'hist_exclude': [(0,9589),(9994,9999)]
    },
}

def is_target_site(site_str, ranges):
    if pd.isna(site_str): 
        return False
    site_str = str(site_str).strip().upper()
    
    if not re.match(r'^C\d', site_str):
        return False
        
    digits = re.sub(r'[^0-9]', '', site_str)
    if not digits: 
        return False
    
    num = int(digits)
    for i in ranges:
        if len(i) == 1 and num == i[0]: 
            return True
        elif len(i) == 2 and i[0] <= num <= i[1]: 
            return True
    return False

def is_hist_excluded(hist_str, ranges):
    if not ranges:
        return False
        
    if pd.isna(hist_str): 
        return False
    
    digits = re.sub(r'[^0-9]', '', str(hist_str))
    if not digits: 
        return False
    
    num = int(digits)
    for i in ranges:
        if len(i) == 1 and num == i[0]: 
            return True
        elif len(i) == 2 and i[0] <= num <= i[1]: 
            return True
    return False

def is_hist_included(hist_str, ranges):
    if not ranges:
        return True
        
    if pd.isna(hist_str): 
        return False
    
    digits = re.sub(r'[^0-9]', '', str(hist_str))
    if not digits: 
        return False
    
    num = int(digits)
    for i in ranges:
        if len(i) == 1 and num == i[0]: 
            return True
        elif len(i) == 2 and i[0] <= num <= i[1]: 
            return True
    return False

def is_didiag_match(date_str, min_year=None, less_than_year=None):
    if pd.isna(date_str):
        return False if (min_year or less_than_year) else True
    
    year_str = str(date_str).strip()[:4]
    if not year_str.isdigit():
        return False
        
    year = int(year_str)
    if min_year and year < min_year:
        return False

    if less_than_year and year >= less_than_year:
        return False
    return True

if __name__ == "__main__":
    INPUT_FILE = 'data/20260318測試.xlsx'     
    TARGET_SHEET = '1150318虛擬V1(給虎科)' 
    OUTPUT_FILE = 'data/cancer_cls_results.xlsx'      
    COL_SITE = '原發部位'
    COL_HIST = '組織類型'

    df = pd.read_excel(INPUT_FILE, sheet_name=TARGET_SHEET)
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:

        for cancer_name, rules in CANCER_RULES.items():
            site_ranges = rules['site_include']
            hist_ranges = rules['hist_exclude']
            is_site_match = df[COL_SITE].apply(lambda x: is_target_site(x, site_ranges))
            is_hist_exclude_match = df[COL_HIST].apply(lambda x: is_hist_excluded(x, hist_ranges))
            df_filtered = df[is_site_match & (~is_hist_exclude_match)]
            print(f"Cancer:[{cancer_name}] ,count:{len(df_filtered)}")

            df_filtered.to_excel(writer, sheet_name=cancer_name, index=False)

    print(f"Result save to {OUTPUT_FILE}")

    #規則三
    DATE_RULES = [
    ('didiag', '<=', 'dcont', '最初診斷日不可晚於首次診斷日'),
    ('didiag', '<=', 'dtrt_1st', '最初診斷日不可晚於首療開始日'),
    ('dcont', '<=', 'dtrt_1st', '首次診斷日不可晚於首療開始日'),
    ('dtrt_1st', '<=', 'dop_1st', '首療開始日不可晚於首次手術日'),
    ('dtrt_1st', '<=', 'dchem', '首療開始日不可晚於本院化療開始日'),
    ('dtrt_1st', '<=', 'dop_mds', '首療開始日不可晚於原發最確切手術日'),
    ('dtrt_1st', '<=', 'drt_1st', '首療開始日不可晚於放療開始日'),
]

def parse_cancer_date(date_val):
    if pd.isna(date_val):
        return None
    date_str = str(date_val).strip()
    
    if len(date_str) == 8 and date_str.isdigit():
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