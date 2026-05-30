import os
import random
import string
import re
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from modules.field_mapping import detect_system, field_mapping

data_gen_bp = Blueprint('data_gen', __name__)

# --- 核心邏輯配置 ---
def get_custom_districts():
    districts = []
    districts.extend([f"01{str(i).zfill(2)}" for i in range(1, 21)]) 
    districts.extend([f"03{str(i).zfill(2)}" for i in range(1, 30)])
    districts.extend([f"05{str(i).zfill(2)}" for i in range(1, 38)])
    districts.extend([f"07{str(i).zfill(2)}" for i in range(1, 39)])
    districts.extend([f"11{str(i).zfill(2)}" for i in range(1, 8)])
    districts.extend([f"12{str(i).zfill(2)}" for i in range(1, 4)])
    districts.extend([f"22{str(i).zfill(2)}" for i in range(1, 3)])
    districts.extend([f"31{str(i).zfill(2)}" for i in range(1, 30)])
    districts.extend([f"32{str(i).zfill(2)}" for i in range(1, 14)])
    districts.extend([f"33{str(i).zfill(2)}" for i in range(1, 14)])
    districts.extend([f"34{str(i).zfill(2)}" for i in range(1, 13)])
    districts.extend([f"35{str(i).zfill(2)}" for i in range(1, 19)])
    districts.extend([f"37{str(i).zfill(2)}" for i in range(1, 27)])
    districts.extend([f"38{str(i).zfill(2)}" for i in range(1, 14)])
    districts.extend([f"39{str(i).zfill(2)}" for i in range(1, 21)])
    districts.extend([f"40{str(i).zfill(2)}" for i in range(1, 19)])
    districts.extend([f"43{str(i).zfill(2)}" for i in range(1, 34)])
    districts.extend([f"44{str(i).zfill(2)}" for i in range(1, 7)])
    districts.extend([f"45{str(i).zfill(2)}" for i in range(1, 14)])
    districts.extend([f"46{str(i).zfill(2)}" for i in range(1, 17)])
    districts.extend([f"90{str(i).zfill(2)}" for i in range(1, 7)])
    districts.extend([f"91{str(i).zfill(2)}" for i in range(1, 5)])
    return districts

ALL_TW_DISTRICT_CODES = get_custom_districts()

# --- 輔助函數 ---
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

# --- API 路由 ---

@data_gen_bp.route('/api/data_gen/analyze', methods=['POST'])
def analyze_file():
    """接收上傳檔案並回傳欄位清單與所有可能的映射資訊"""
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "無檔案"}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    upload_folder = 'data/temp'
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.xlsx':
            df = pd.read_excel(file_path, nrows=5, dtype=str)
        else:
            df = pd.read_csv(file_path, nrows=5, encoding='utf-8-sig', dtype=str)
        
        # 1. 取得 SQL Server 所有的完整對照資料
        from modules.db import get_conn
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
                "aliases": [] # 初始化為 list，稍後填充
            }
            # 收集所有可能的嚴格別名 (序號+名稱)，支援斜線拆解 (僅限 4.2.1.8, 7.6)
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

        # 2. 分析上傳的欄位
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
            # 尋找這個欄位屬於哪個序號 (嚴格比對)
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
                if "日期" in std or "日" in std or "生日" in std:
                    info["is_date"] = True
                if std in special_map:
                    info["special_key"] = special_map[std]
            
            analyzed_columns.append(info)

        system_name, _ = detect_system(raw_cols)
        session['last_gen_file'] = file_path
        
        return jsonify({
            "ok": True, 
            "analyzed_columns": analyzed_columns, 
            "detected_system": system_name,
            "filename": filename
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@data_gen_bp.route('/api/data_gen/process', methods=['POST'])
def process_file():
    """執行去識別化處理"""
    data = request.json
    selected_date_cols_raw = data.get('date_cols', [])
    extra_cols = data.get('extra_cols', []) 
    special_configs = data.get('special_configs', {}) 
    naming_scheme = data.get('naming_scheme', 'field_name_zh')
    
    file_path = session.get('last_gen_file')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"ok": False, "error": "請重新上傳檔案"}), 400
        
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            df = pd.read_excel(file_path, dtype=str)
        else:
            df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str)
            
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = df.columns.str.strip()
        row_count = len(df)

        # --- A. 欄位標準化 (依據 naming_scheme 與 嚴格匹配 決定) ---
        from modules.db import get_conn
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱], [台大體系醫整庫欄位名稱], [台灣癌症登記中心], [雲醫癌AI模組] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap]")
        rows = cursor.fetchall()
        conn.close()

        # 建立嚴格的 alias -> target_header 地圖
        alias_to_target = {}
        all_possible_target_headers = set() # 記錄所有該體系定義過的標準名稱
        scheme_target_for_seq = {} # 記錄每個序號對應的目標名稱
        
        scheme_idx_map = {
            'field_name_zh': 1,
            'field_name_en': 2,
            'ntu_yunlin': 3,
            'ntu_system': 4,
            'taiwan_cancer_registry': 5,
            'AI_module': 6
        }
        target_idx = scheme_idx_map.get(naming_scheme, 1)

        for r in rows:
            seq = str(r[0]).strip().replace('.0', '')
            target_val = r[target_idx]

            if pd.notna(target_val) and str(target_val).strip():
                # 統一目標名稱：使用完整的資料庫名稱
                target_header = f"{seq}{str(target_val).strip()}"
                all_possible_target_headers.add(target_header)
                scheme_target_for_seq[seq] = target_header
                
                for alias in r[1:7]:
                    if pd.notna(alias):
                        clean_alias = str(alias).strip()
                        if clean_alias:
                            # 支援斜線拆解匹配，但統一指向同一個 target_header
                            if seq in ['4.2.1.8', '7.6'] and '/' in clean_alias:
                                parts = [p.strip() for p in clean_alias.split('/') if p.strip()]
                            else:
                                parts = [clean_alias]
                                
                            for part in parts:
                                alias_to_target[f"{seq}{part}"] = target_header

        # 執行重新命名 (僅針對有目標名稱的欄位)
        rename_map = {}
        for col in df.columns:
            if col in alias_to_target:
                target_name = alias_to_target[col]
                final_name = target_name
                
                # 智慧重命名：僅限中文方案且包含斜線
                if naming_scheme == 'field_name_zh' and '/' in target_name:
                    m_target = re.match(r'^(\d+(\.\d+)*)', target_name)
                    if m_target:
                        seq = m_target.group(1)
                        if seq in ['4.2.1.8', '7.6'] and col.startswith(seq):
                             # 拆分目標名稱為多個部分
                             target_raw_name = target_name[len(seq):].strip()
                             valid_parts = [p.strip() for p in target_raw_name.split('/') if p.strip()]
                             
                             # 取得目前來源欄位名稱部分
                             source_raw_name = col[len(seq):].strip()
                             
                             # 精準匹配二選一：如果符合其中一邊，則保留原本的來源名稱作為新欄位名
                             if source_raw_name in valid_parts:
                                 final_name = col
                
                rename_map[col] = final_name

        # 轉換日期選取清單
        selected_date_cols_std = []
        for col in selected_date_cols_raw:
            if col in rename_map:
                selected_date_cols_std.append(rename_map[col])
            else:
                selected_date_cols_std.append(col)

        df.rename(columns=rename_map, inplace=True)
        
        # --- B. 執行處理邏輯 ---


        # 1. 記錄 99
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

        # 2. 計算偏移 (尋找包含標準名稱的標籤)
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

        # 3. 執行平移
        offset_timedelta = pd.to_timedelta(final_offsets, unit='D')
        for col in selected_date_cols_std:
            if col in df.columns:
                df[col] = df[col] + offset_timedelta

        # 4. 邏輯校正
        if diag_col_name and first_diag_col and diag_col_name in df.columns and first_diag_col in df.columns:
            for i in range(row_count):
                dt_init, dt_first = df.loc[i, diag_col_name], df.loc[i, first_diag_col]
                if pd.notna(dt_init) and pd.notna(dt_first) and dt_init > dt_first:
                    df.loc[i, diag_col_name] = dt_first

        # 5. 特殊欄位遮罩 (嚴格使用序號定位，確保與 Mapping 邏輯一致)
        def find_col_by_seq_or_key(seq_prefix):
            # 優先找已經改名後的目標標頭，再找原始標頭
            target_name = scheme_target_for_seq.get(seq_prefix)
            if target_name and target_name in df.columns:
                return target_name
            # 尋找序號開頭的原始欄位
            for c in df.columns:
                if c.startswith(seq_prefix):
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

        # 6. 年齡與格式化
        birth_col = find_col_by_seq_or_key("1.6")
        diag_col_name = find_col_by_seq_or_key("2.5")
        
        if special_configs.get('age_calc') and birth_col and diag_col_name:
            # 決定年齡欄位名稱：優先用體系名稱，若無則用預設
            age_col = scheme_target_for_seq.get("2.1") or find_col_by_seq_or_key("2.1") or "2.1診斷年齡"
            # 確保日期是 datetime 格式才能計算
            temp_birth = pd.to_datetime(df[birth_col], errors='coerce')
            temp_diag = pd.to_datetime(df[diag_col_name], errors='coerce')
            
            # 重算年齡
            df[age_col] = [
                (d.year - b.year) if pd.notna(d) and pd.notna(b) else np.nan 
                for b, d in zip(temp_birth, temp_diag)
            ]
            # 將出生日期遮蔽為僅年月
            df[birth_col] = temp_birth.apply(lambda x: format_date_special(x, "%Y/%m/01") if pd.notna(x) else "0000/00/00")

        # 7. 最終所有日期欄位轉回字串格式 (包含還原 99)
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

        # --- 最終順序調整：嚴格執行「標準欄位在左(依序號)，未匹配欄位在右」 ---
        current_cols = list(df.columns)
        
        # 1. 找出真正屬於「目標格式」且有定義名稱的標準名稱
        mapped_target_headers = set(rename_map.values())
        
        final_standard_cols = []
        for col in current_cols:
            if col in mapped_target_headers:
                import re
                m = re.match(r'^(\d+(\.\d+)*)', col)
                seq_val = m.group(1) if m else "999"
                try:
                    seq_parts = [int(x) for x in seq_val.split('.')]
                except:
                    seq_parts = [999]
                final_standard_cols.append({"name": col, "seq_parts": seq_parts})
        
        # 依照序號排序標準欄位 (左側)
        final_standard_cols.sort(key=lambda x: x["seq_parts"])
        ordered_left = [x["name"] for x in final_standard_cols]
        
        # 2. 處理未匹配欄位 (排除掉已經在左側的欄位，其餘通通丟右側)
        # 這裡要包含所有 extra_cols 中沒被 match 到的
        ordered_right = [c for c in extra_cols if c in current_cols and c not in mapped_target_headers]
        
        # 3. 組合最終順序並重新選取 DataFrame 欄位
        final_col_order = ordered_left + ordered_right
        df = df[final_col_order]
        
        # 定義輸出的檔名
        base_name = os.path.basename(file_path)
        out_filename = f"Gen_{base_name}"
        out_path = os.path.join('data/temp', out_filename)
        
        if ext == ".xlsx": df.to_excel(out_path, index=False)
        else: df.to_csv(out_path, index=False, encoding="utf-8-sig")
        
        session['last_gen_output'] = out_path
        
        # --- 關鍵：確保預覽資料的欄位順序也是正確的 ---
        preview_data = []
        for _, row in df.head(20).iterrows():
            # 使用 OrderedDict 或是依照 final_col_order 建立 dict 確保順序
            item = {}
            for col in final_col_order:
                val = row[col]
                item[col] = str(val) if pd.notna(val) else ""
            preview_data.append(item)
        
        return jsonify({"ok": True, "preview": preview_data, "headers": final_col_order, "download_url": f"/api/data_gen/download"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@data_gen_bp.route('/api/data_gen/download')
def download_file():
    path = session.get('last_gen_output')
    if path and os.path.exists(path):
        return send_file(os.path.abspath(path), as_attachment=True)
    return "檔案不存在", 404
