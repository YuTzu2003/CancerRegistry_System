import os
import pandas as pd
import re
from modules.db import get_conn
from modules.field_mapping import field_mapping,detect_system
from modules.cleaner.cleanValidate import validate_date_rules
from modules.field_mapping import field_mapping, process_data

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
    '胰臟癌': {
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

COL_SITE = '原發部位'
COL_HIST = '組織類型'
COL_DIDIAG = '最初診斷日'

# site包含
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

# hist排除
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

# hist包含
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

# didiag包含
def is_didiag_included(date_str, ranges):
    if not ranges:
        return True   
         
    if pd.isna(date_str): 
        return False
    
    year_str = str(date_str).strip()[:4]
    if not year_str.isdigit(): 
        return False
    
    num = int(year_str)
    for i in ranges:
        if len(i) == 1 and num == i[0]: 
            return True
        elif len(i) == 2:
            start, end = i
            pass_start = (start is None) or (num >= start)
            pass_end = (end is None) or (num <= end)  
            if pass_start and pass_end:
                return True
    return False

# 癌別分類
def cancer_classify(df, OUTPUT_FILE, alias_dict=None, output_field_list=None):
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for cancer_name, rules in CANCER_RULES.items():
            site_ranges = rules.get('site_include', [])
            hist_exclude_ranges = rules.get('hist_exclude', [])
            hist_include_ranges = rules.get('hist_include', [])
            year_ranges = rules.get('didiag_include', [])
            
            is_site_match = df[COL_SITE].apply(lambda x: is_target_site(x, site_ranges))
            is_hist_exclude_match = df[COL_HIST].apply(lambda x: is_hist_excluded(x, hist_exclude_ranges))
            is_hist_include_match = df[COL_HIST].apply(lambda x: is_hist_included(x, hist_include_ranges))
            
            if year_ranges:
                is_year_match = df[COL_DIDIAG].apply(lambda x: is_didiag_included(x, year_ranges))
            else:
                is_year_match = pd.Series(True, index=df.index)

            df_filtered = df[is_site_match & (~is_hist_exclude_match) & is_hist_include_match & is_year_match].copy()

            if alias_dict and not df_filtered.empty:
                df_filtered = df_filtered.rename(columns=alias_dict)
                if output_field_list:
                    valid_cols = [c for c in output_field_list if c in df_filtered.columns]
                    df_filtered = df_filtered[valid_cols]

            print(f"Cancer:[{cancer_name}] ,count:{len(df_filtered)}")
            df_filtered.to_excel(writer, sheet_name=cancer_name, index=False)

    print(f"Result save to {OUTPUT_FILE}")

# 長短表分類
def rule_table_classify(df, OUTPUT_DIR):
    df_proc = df.copy()
    result_dict = {} 
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

        if not is_long:
            if 2011 <= year <= 2017:
                return "42"
            elif 2018 <= year <= 2024:
                return "45"
            elif year >= 2025:
                return "50"
        else:
            if 2011 <= year <= 2017:
                return "114"
            elif 2018 <= year <= 2024:
                return "115"
            elif year >= 2025:
                return "129"
        return "other"

  
    df_proc['Rule_ID'] = df_proc.apply(classify_row, axis=1)
    
    system_name, _ = detect_system(df_proc.columns)
    print(f"The data for {system_name}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    conn = get_conn()
    try:
        for rid in ["42", "45", "50", "114", "115", "129"]:
            subset = df_proc[df_proc['Rule_ID'] == rid].copy()

            if subset.empty:
                print(f"Rule {rid}: no data")
                continue

            mapping_col = f"[{rid}欄位]"
            query = f"""SELECT FieldName.[{system_name}] FROM [Hospital_data].[dbo].[Field_Mapping]
                        INNER JOIN [Hospital_data].[dbo].[FieldName] ON Field_Mapping.序號 = FieldName.序號
                        WHERE Field_Mapping.{mapping_col} = 1
                    """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            df_rule_map = pd.DataFrame.from_records(rows, columns=columns)

            if not df_rule_map.empty:                
                target_headers = df_rule_map[system_name].dropna().astype(str).str.strip().tolist()
                essential_cols = [COL_SITE, COL_HIST, COL_DIDIAG]
                all_needed_headers = list(set(target_headers + essential_cols))
                available_cols = [c for c in all_needed_headers if c in subset.columns]
                output_df = subset[available_cols].copy()
                output_path = f"{OUTPUT_DIR}/Rule_{rid}.xlsx"
                output_df.to_excel(output_path, index=False)
                result_dict[rid] = output_df             
                print(f"Rule {rid}: count:{len(subset)} (Fields: {len(target_headers)})")

            else:
                output_path = f"{OUTPUT_DIR}/Rule_{rid}.xlsx"
                output_df = subset.drop(columns=['Rule_ID'])
                output_df.to_excel(output_path, index=False)
                result_dict[rid] = output_df
                print(f"Rule {rid}: count:{len(subset)} (No mapping found, outputting all)")         
    finally:
        conn.close()
    return result_dict


if __name__ == "__main__":
    INPUT_FILE = 'data/20260318測試.xlsx'     
    TARGET_SHEET = '1150318虛擬V1(給虎科)' 
    OUTPUT_FILE_CLASSIFY = 'data/cancer_cls_results.xlsx'  
    OUTPUT_DIR = 'data/output_rules'    
 
    
    df = pd.read_excel(INPUT_FILE, sheet_name=TARGET_SHEET)
    rule_table_classify(df, OUTPUT_DIR) # 年度長短表分類
    cancer_classify(df, OUTPUT_FILE_CLASSIFY) # 癌別分類
   