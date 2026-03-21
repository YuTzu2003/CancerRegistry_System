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
    }
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