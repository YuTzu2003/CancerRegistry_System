
import os
import random
import string
import re
import pandas as pd
import numpy as np
from modules.blueprint.clean.field_mapping import detect_system
from modules.blueprint.clean.pipeline import _natural_sort_key
from modules.services.db import get_conn

def get_custom_districts():
    districts = []
    
    district_rules = {
        "01": [0, 1, 2, 9, 10, 11, 12, 15, 16, 17, 18, 19, 20],
        "03": list(range(0, 30)),                # 0300 - 0329
        "05": list(range(0, 34)) + [36, 37, 38], # 0500 - 0533, 0536 - 0538
        "07": list(range(0, 39)),                # 0700 - 0738
        "11": list(range(0, 8)),                 # 1100 - 1107
        "12": [0, 1, 4, 5],                      # 1200, 1201, 1204, 1205
        "22": list(range(0, 3)),                 # 2200 - 2202
        "31": list(range(0, 30)),                # 3100 - 3129
        "32": list(range(0, 14)),                # 3200 - 3213
        "33": list(range(0, 15)),                # 3300 - 3314
        "34": list(range(0, 13)),                # 3400 - 3412
        "35": list(range(0, 19)),                # 3500 - 3518
        "37": list(range(0, 27)),                # 3700 - 3726
        "38": list(range(0, 14)),                # 3800 - 3813
        "39": list(range(0, 21)),                # 3900 - 3920
        "40": list(range(0, 19)),                # 4000 - 4018
        "43": list(range(0, 34)),                # 4300 - 4333
        "44": list(range(0, 7)),                 # 4400 - 4406
        "45": list(range(0, 14)),                # 4500 - 4513
        "46": list(range(0, 17)),                # 4600 - 4616
        "90": list(range(0, 7)),                 # 9000 - 9006
        "91": list(range(0, 5)),                 # 9100 - 9104
        "99": list(range(1, 9))                  # 9901 - 9908, 9999
    }

    for prefix, suffixes in district_rules.items():
        districts.extend([f"{prefix}{str(s).zfill(2)}" for s in suffixes])

    districts.append("9999")
    return districts

ALL_TW_DISTRICT_CODES = get_custom_districts()

def mask_name(name):
    if pd.isna(name) or str(name).strip() == "": return "OO"
    s = str(name).strip()
    return s[0] + ("O" if len(s) == 2 else "OO")

def mask_id(val):
    if pd.isna(val): return "A1********"
    s = str(val).strip().upper()
    first_char = s[0] if s and s[0].isalpha() else random.choice(string.ascii_uppercase)
    second_char = str(random.choice([1, 2]))
    return f"{first_char}{second_char}" + "*" * 8

def format_date_special(date_val, format_str="%Y/%m/%d"):
    if pd.isna(date_val): return "0000/00/00"
    try: return date_val.strftime(format_str)
    except: return "0000/00/00"


def analyze_file_logic(file_path, filename):
    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.xlsx':
            df = pd.read_excel(file_path, nrows=5, dtype=str)
        else:
            df = pd.read_csv(file_path, nrows=5, encoding='utf-8-sig', dtype=str)

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱], [台大體系醫整庫欄位名稱], [台灣癌症登記中心], [雲醫癌AI模組] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap]")
        rows = cursor.fetchall()
        conn.close()

        field_db_map = {}
        for r in rows:
            seq = str(r[0]).strip().replace('.0', '')
            field_db_map[seq] = {
                "field_name_zh": str(r[1]).strip() if pd.notna(r[1]) else "",
                "field_name_en": str(r[2]).strip() if pd.notna(r[2]) else "",
                "ntu_yunlin": str(r[3]).strip() if pd.notna(r[3]) else "",
                "ntu_system": str(r[4]).strip() if pd.notna(r[4]) else "",
                "taiwan_cancer_registry": str(r[5]).strip() if pd.notna(r[5]) else "",
                "AI_module": str(r[6]).strip() if pd.notna(r[6]) else "",
                "aliases": [] 
            }

            for alias in r[1:7]:
                if pd.notna(alias):
                    clean_val = str(alias).strip()
                    if clean_val:
                        if seq in ['4.2.1.8', '7.6'] and '/' in clean_val:
                            for v in clean_val.split('/'):
                                v = v.strip()
                                if v:
                                    field_db_map[seq]["aliases"].append(f"{seq}{v}")
                        else:
                            field_db_map[seq]["aliases"].append(f"{seq}{clean_val}")

        analyzed_columns = []
        raw_cols = [str(c).strip() for c in df.columns if not str(c).startswith('Unnamed')]
        
        special_map = {
            "病歷號碼": "cno",
            "姓名": "name",
            "身分證統一編號": "id",
            "性別": "gender",
            "戶籍地代碼": "district",
            "診斷年齡": "age_calc"
        }

        for col in raw_cols:
            found_seq = None
            for seq, data in field_db_map.items():
                if col in data["aliases"]:
                    found_seq = seq
                    break
            
            info = {
                "name": col,
                "is_date": False,
                "special_key": None,
                "seq": found_seq,
                "mappings": field_db_map.get(found_seq, {}) if found_seq else {}
            }
            
            if found_seq:
                std = field_db_map[found_seq]["field_name_zh"]
                std_en = field_db_map[found_seq]["field_name_en"]
                
                date_keywords = ['日期', 'Date', '日', 'Birth', 'day']
                
                is_date_by_std = any(kw.lower() in std.lower() or kw.lower() in std_en.lower() for kw in date_keywords)
                is_date_by_raw = any(kw.lower() in col.lower() for kw in date_keywords)

                if is_date_by_std or is_date_by_raw:
                    info["is_date"] = True

                if std in special_map:
                    info["special_key"] = special_map[std]
            
            analyzed_columns.append(info)

        analyzed_columns.sort(key=lambda x: _natural_sort_key(x["name"]))

        system_name, _ = detect_system(raw_cols)
        
        return {
            "ok": True, 
            "analyzed_columns": analyzed_columns, 
            "detected_system": system_name,
            "filename": filename
        }, 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}, 500


def process_file_logic(file_path, format_id, selected_date_cols_raw, extra_cols, special_configs, naming_scheme):
    if not file_path or not os.path.exists(file_path):
        return {"ok": False, "error": "請重新上傳檔案"}, 400
        
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            df = pd.read_excel(file_path, dtype=str)
        else:
            df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str)
            
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = df.columns.str.strip()
        row_count = len(df)

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱], [台大體系醫整庫欄位名稱], [台灣癌症登記中心], [雲醫癌AI模組] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap]")
        rows = cursor.fetchall()
        conn.close()

        fmt_rules = {}
        if format_id:
             from modules.blueprint.clean.cleaner import FORMAT_RULES_MAP
             fmt_key = f"fmt_{format_id}"
             if fmt_key in FORMAT_RULES_MAP:
                 rules_def = FORMAT_RULES_MAP[fmt_key]
                 for friendly_name, info in rules_def.items():
                     fid = info.get('ID')
                     if fid:
                         fmt_rules[fid] = friendly_name

        alias_to_target = {}
        all_possible_target_headers = set() 
        scheme_target_for_seq = {} 
        
        scheme_idx_map = {
            'field_name_zh': 1,
            'field_name_en': 2,
            'ntu_yunlin': 3,
            'ntu_system': 4,
            'taiwan_cancer_registry': 5,
            'AI_module': 6
        }
        target_idx = 1 if naming_scheme == 'original' else scheme_idx_map.get(naming_scheme, 1)

        for r in rows:
            seq = str(r[0]).strip().replace('.0', '')
            target_val = r[target_idx]

            if pd.notna(target_val) and str(target_val).strip():
                target_header = f"{seq}{str(target_val).strip()}"
                all_possible_target_headers.add(target_header)
                scheme_target_for_seq[seq] = target_header
                
                for alias in r[1:7]:
                    if pd.notna(alias):
                        clean_alias = str(alias).strip()
                        if clean_alias:
                            if seq in ['4.2.1.8', '7.6'] and '/' in clean_alias:
                                parts = [p.strip() for p in clean_alias.split('/') if p.strip()]
                            else:
                                parts = [clean_alias]
                                
                            for part in parts:
                                alias_to_target[f"{seq}{part}"] = target_header

        rename_map = {}
        
        DEFAULT_PREFERENCE = {
            "4.2.1.8": fmt_rules.get("4.2.1.8", "放射治療執行狀態"),
            "7.6": fmt_rules.get("7.6", "首次治療前生活功能狀態評估")
        }

        for col in df.columns:
            if col in alias_to_target:
                if naming_scheme == 'original':
                    final_name = col
                else:
                    target_name = alias_to_target[col]
                    final_name = target_name
                    
                    if naming_scheme == 'field_name_zh' and '/' in target_name:
                        m_target = re.match(r'^(\d+(\.\d+)*)', target_name)
                        if m_target:
                            seq = m_target.group(1)
                            if seq in ['4.2.1.8', '7.6']:

                                 target_raw_name = target_name[len(seq):].strip()
                                 valid_parts = [p.strip() for p in target_raw_name.split('/') if p.strip()]
                                 
                                 found_part = None
                                 if col.startswith(seq):
                                     source_raw_name = col[len(seq):].strip()
                                     if source_raw_name in valid_parts:
                                         found_part = source_raw_name

                                 if found_part:
                                     final_name = f"{seq}{found_part}"
                                 elif seq in DEFAULT_PREFERENCE:
                                     final_name = f"{seq}{DEFAULT_PREFERENCE[seq]}"
                
                rename_map[col] = final_name

        selected_date_cols_std = []
        for col in selected_date_cols_raw:
            if col in rename_map:
                selected_date_cols_std.append(rename_map[col])
            else:
                selected_date_cols_std.append(col)

        df.rename(columns=rename_map, inplace=True)
        
        is_originally_99 = {col: [False] * row_count for col in selected_date_cols_std}
        for col in selected_date_cols_std:
            if col in df.columns:
                vals = df[col].astype(str).str.strip()
                for i in range(row_count):
                    val = vals[i]
                    if len(val) >= 8 and (val.endswith("99") or "/99" in val):
                        is_originally_99[col][i] = True
                        df.loc[i, col] = val[:-2] + "15"
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
                except:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

        diag_col_name = next((c for c in df.columns if "最初診斷日期" in c or "診斷日期" in c), None)
        first_diag_col = next((c for c in df.columns if "首次就診日期" in c), None)
        
        BIN1, BIN2, BIN3 = (2011, 2017), (2018, 2024), (2025, 2099)
        final_offsets = []
        for i in range(row_count):
            current_offset = random.randint(-1500, 1500)
            if diag_col_name and pd.notna(df.loc[i, diag_col_name]):
                dt_orig = df.loc[i, diag_col_name]
                year = dt_orig.year
                target = BIN1 if BIN1[0] <= year <= BIN1[1] else (BIN2 if BIN2[0] <= year <= BIN2[1] else (BIN3 if year >= BIN3[0] else (year, year)))
                l_bound, u_bound = pd.Timestamp(target[0], 1, 1), pd.Timestamp(target[1], 12, 31)
                current_offset = random.randint(max((l_bound - dt_orig).days, -1500), min((u_bound - dt_orig).days, 1500))
            final_offsets.append(current_offset)

        offset_timedelta = pd.to_timedelta(final_offsets, unit='D')
        for col in selected_date_cols_std:
            if col in df.columns:
                df[col] = df[col] + offset_timedelta

        if diag_col_name and first_diag_col and diag_col_name in df.columns and first_diag_col in df.columns:
            for i in range(row_count):
                dt_init, dt_first = df.loc[i, diag_col_name], df.loc[i, first_diag_col]
                if pd.notna(dt_init) and pd.notna(dt_first) and dt_init > dt_first:
                    df.loc[i, diag_col_name] = dt_first

        def find_col_by_seq_or_key(seq_prefix):
            target_name = scheme_target_for_seq.get(seq_prefix)
            if target_name and target_name in df.columns:
                return target_name
            for c in df.columns:
                if c.startswith(seq_prefix):
                    return c
                for orig_c, target_h in alias_to_target.items():
                    if orig_c == c and target_h.startswith(seq_prefix):
                        return c
            return None

        cno_col = find_col_by_seq_or_key("1.2")
        if special_configs.get('cno') and cno_col:
            df[cno_col] = [f"TEST{i+1}" for i in range(row_count)]
        
        name_col = find_col_by_seq_or_key("1.3")
        if special_configs.get('name') and name_col:
            df[name_col] = df[name_col].apply(mask_name)
            
        id_col = find_col_by_seq_or_key("1.4")
        if special_configs.get('id') and id_col:
            df[id_col] = df[id_col].apply(mask_id)
            
        gender_col = find_col_by_seq_or_key("1.5")
        if special_configs.get('gender') and gender_col:
            df[gender_col] = np.random.choice([1, 2], size=row_count)
            
        dist_col = find_col_by_seq_or_key("1.7")
        if special_configs.get('district') and dist_col:
            df[dist_col] = np.random.choice(ALL_TW_DISTRICT_CODES, size=row_count)

        birth_col = find_col_by_seq_or_key("1.6")
        diag_col_name = find_col_by_seq_or_key("2.5")
        
        if special_configs.get('age_calc') and birth_col and diag_col_name:
            age_col = scheme_target_for_seq.get("2.1") or find_col_by_seq_or_key("2.1") or "2.1診斷年齡"
            temp_birth = pd.to_datetime(df[birth_col], errors='coerce')
            temp_diag = pd.to_datetime(df[diag_col_name], errors='coerce')

            df[age_col] = [
                (d.year - b.year) if pd.notna(d) and pd.notna(b) else np.nan 
                for b, d in zip(temp_birth, temp_diag)
            ]
            df[birth_col] = temp_birth.apply(lambda x: format_date_special(x, "%Y/%m/01") if pd.notna(x) else "0000/00/00")

        for col in selected_date_cols_std:
            if col in df.columns:
                res = []
                for i in range(row_count):
                    dt = df.loc[i, col]
                    if pd.isna(dt) or dt == "0000/00/00":
                        res.append("0000/00/00")
                    elif isinstance(dt, str):
                        res.append(dt)
                    else:
                        fmt = "%Y/%m/99" if is_originally_99[col][i] else "%Y/%m/%d"
                        res.append(dt.strftime(fmt))
                df[col] = res

        current_cols = list(df.columns)

        mapped_target_headers = set(rename_map.values())

        user_extra_targets = set()
        for c in extra_cols:
            user_extra_targets.add(rename_map.get(c, c))

        final_standard_cols = []
        for col in current_cols:
            if col in mapped_target_headers and col not in user_extra_targets:
                m = re.match(r'^(\d+(\.\d+)*)', col)
                seq_val = m.group(1) if m else "999"
                try:
                    seq_parts = [int(x) for x in seq_val.split('.')]
                except:
                    seq_parts = [999]
                final_standard_cols.append({"name": col, "seq_parts": seq_parts})

        final_standard_cols.sort(key=lambda x: x["seq_parts"])
        ordered_left = [x["name"] for x in final_standard_cols]

        ordered_right = []
        for c in extra_cols:
            target = rename_map.get(c, c)
            if target in current_cols and target not in ordered_right:
                ordered_right.append(target)

        final_col_order = ordered_left + ordered_right
        df = df[final_col_order]
        
        base_name = os.path.basename(file_path)
        out_filename = f"Gen_{base_name}"
        out_path = os.path.join('data/temp', out_filename)
        
        if ext == ".xlsx": df.to_excel(out_path, index=False)
        else: df.to_csv(out_path, index=False, encoding="utf-8-sig")
        
        preview_data = []
        for _, row in df.head(20).iterrows():
            item = {}
            for col in final_col_order:
                val = row[col]
                item[col] = str(val) if pd.notna(val) else ""
            preview_data.append(item)
        
        return {
            "ok": True, 
            "preview": preview_data, 
            "headers": final_col_order, 
            "download_url": "/api/data_gen/download",
            "out_path": out_path
        }, 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}, 500