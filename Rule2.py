import pandas as pd
import re
import os
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
        'didiag_include': [(2022, None)],
        'split_by_didiag': True
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
        'hist_include': [(9590,9993)]
    },
}


def is_target_site(site_str, ranges):
    if pd.isna(site_str): return False
    site_str = str(site_str).strip().upper()
    if not re.match(r'^C\d', site_str): return False
    digits = re.sub(r'[^0-9]', '', site_str)
    if not digits: return False
    num = int(digits)
    for i in ranges:
        if len(i) == 1 and num == i[0]: return True
        elif len(i) == 2 and i[0] <= num <= i[1]: return True
    return False

def is_hist_excluded(hist_str, ranges):
    if not ranges or pd.isna(hist_str): return False
    digits = re.sub(r'[^0-9]', '', str(hist_str))
    num = int(digits) if digits else -1
    for i in ranges:
        if len(i) == 1 and num == i[0]: return True
        elif len(i) == 2 and i[0] <= num <= i[1]: return True
    return False

def is_hist_included(hist_str, ranges):
    if not ranges: return True
    if pd.isna(hist_str): return False
    digits = re.sub(r'[^0-9]', '', str(hist_str))
    num = int(digits) if digits else -1
    for i in ranges:
        if len(i) == 1 and num == i[0]: return True
        elif len(i) == 2 and i[0] <= num <= i[1]: return True
    return False

def is_didiag_included(date_str, ranges):
    if not ranges: return True   
    year_str = str(date_str).strip()[:4]
    if not year_str.isdigit(): return False
    num = int(year_str)
    for i in ranges:
        if len(i) == 2:
            start, end = i
            if (start is None or num >= start) and (end is None or num <= end): return True
    return False

# ----------------------------------------Rule2---------------------------------------------------------
def process_data(input_file, sheet_name):
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    COL_SITE = '原發部位'
    COL_HIST =  '組織類型'
    COL_DIDIAG = '最初診斷日'

    def classify_row(row):
        is_long = False
        for _, rule in CANCER_RULES.items():
            site_ok = is_target_site(row[COL_SITE], rule.get('site_include', []))
            hist_ex = is_hist_excluded(row[COL_HIST], rule.get('hist_exclude', []))
            hist_in = is_hist_included(row[COL_HIST], rule.get('hist_include', []))
            date_ok = is_didiag_included(row[COL_DIDIAG], rule.get('didiag_include', []))
            
            if site_ok and not hist_ex and hist_in and date_ok:
                is_long = True
                break

        try:
            year = int(str(row[COL_DIDIAG]).strip()[:4])
        except:
            return "ERROR_DATE"

        # 短表
        if not is_long: 
            if 2011 <= year <= 2017: 
                return "42"
            if 2018 <= year <= 2024: 
                return "45"
            if year >= 2025: 
                return "50"

        # 長表
        else: 
            if 2011 <= year <= 2017: 
                return "114"
            if 2018 <= year <= 2024: 
                return "115"
            if year >= 2025: 
                return "129"
        return "other"

    df['Rule_ID'] = df.apply(classify_row, axis=1)

    output_dir = "data/output_rules"
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    for rid in ["42", "45", "50", "114", "115", "129"]:
        subset = df[df['Rule_ID'] == rid].copy()
        if not subset.empty:
            subset.drop(columns=['Rule_ID']).to_excel(f"{output_dir}/Rule_{rid}.xlsx", index=False)
            print(f"Rule {rid}: count:{len(subset)}")
        else:
            print(f"Rule {rid}: no data")

if __name__ == "__main__":
    INPUT_FILE = 'data/20260318測試.xlsx' 
    TARGET_SHEET = '1150318虛擬V1(給虎科)'
    process_data(INPUT_FILE, TARGET_SHEET)