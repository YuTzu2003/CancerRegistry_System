import pandas as pd
import re

CANCER_RULES = {
    '口腔癌': {
        'site_include': [(0,9), (20,23), (28,29), (30,39), (40,49), (50,), (58,59), (60,69)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '口咽癌': {
        'site_include': [(19,), (24,), (51,52), (90,99), (100,109), (142,), (148,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '下咽癌:': {
        'site_include': [(12,), (13,), (140,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '主唾液腺癌:': {
        'site_include': [(7,), (8,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '鼻咽癌:': {
        'site_include': [(11,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '食道癌:': {
        'site_include': [(15,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '胃癌:': {
        'site_include': [(16,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '結直腸癌:': {
        'site_include': [(18,), (19,), (20,), (21,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '結腸癌:': {
        'site_include': [(18,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '直腸癌:': {
        'site_include': [(19,), (20,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肛門癌:': {
        'site_include': [(21,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肝癌:': {
        'site_include': [(22,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '胰臟癌(長表)': {
        'site_include': [(25,)],
        'hist_exclude': [(9140,), (9590,9993)],
        'didiag_min': 2022 
    },
    '胰臟癌(短表)': {
        'site_include': [(25,)],
        'hist_exclude': [(9140,), (9590,9993)],
        'didiag_less_than': 2022
    },
    '喉癌:': {
        'site_include': [(32,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '肺癌:': {
        'site_include': [(33,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '乳癌:': {
        'site_include': [(50,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '子宮頸癌:': {
        'site_include': [(53,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '子宮體癌:': {
        'site_include': [(54,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '卵巢癌:': {
        'site_include': [(56,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '卵巢癌:': {
        'site_include': [(56,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '攝護腺癌:': {
        'site_include': [(61,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '膀胱癌:': {
        'site_include': [(67,)],
        'hist_exclude': [(9140,), (9590,9993)]
    },
    '血液腫瘤:': {
        'site_include': [(0,80)],
        'hist_exclude': [(9590,9993)]
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