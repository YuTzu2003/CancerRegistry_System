import os
import random
import string
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
    """接收上傳檔案並回傳欄位清單"""
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
        
        # 1. 取得 SQL Server 所有的對照資料 (嚴格格式：序號名稱)
        from modules.db import get_conn
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱], [台大體系醫整庫欄位名稱], [台灣癌症登記中心] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap]")
        rows = cursor.fetchall()
        conn.close()

        alias_to_std = {}
        for r in rows:
            seq = str(r[0]).strip().replace('.0', '')
            std_name = str(r[1]).strip()
            if not std_name: continue
            for alias in r[1:]:
                if pd.notna(alias):
                    a = str(alias).strip()
                    if a:
                        alias_to_std[f"{seq}{a}"] = std_name

        # 2. 分析上傳的欄位
        analyzed_columns = []
        raw_cols = [str(c).strip() for c in df.columns if not str(c).startswith('Unnamed')]
        
        # 定義特殊欄位標準名稱與 Key 的對應
        special_map = {
            "病歷號碼": "cno",
            "姓名": "name",
            "身分證統一編號": "id",
            "性別": "gender",
            "戶籍地代碼": "district",
            "診斷年齡": "age_calc"
        }

        for col in raw_cols:
            std = alias_to_std.get(col)
            info = {
                "name": col,
                "is_date": False,
                "special_key": None
            }
            if std:
                # 判斷是否為日期 (標準名稱含"日期"或"生日")
                if "日期" in std or "日" in std or "生日" in std:
                    info["is_date"] = True
                # 判斷是否為特殊欄位
                if std in special_map:
                    info["special_key"] = special_map[std]
            
            analyzed_columns.append(info)

        system_name, _ = detect_system(raw_cols)
        session['last_gen_file'] = file_path
        session['last_gen_system'] = system_name
        
        return jsonify({
            "ok": True, 
            "analyzed_columns": analyzed_columns, 
            "detected_system": system_name,
            "filename": filename
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@data_gen_bp.route('/api/data_gen/process', methods=['POST'])
def process_file():
    """執行去識別化處理"""
    data = request.json
    # 注意：這裡的 selected_date_cols 是原始檔案的欄位名
    selected_date_cols_raw = data.get('date_cols', [])
    special_configs = data.get('special_configs', {}) 
    
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

        # --- A. 欄位標準化 (統一輸出格式為 [序號][標準名稱]) ---
        from modules.db import get_conn
        conn = get_conn()
        cursor = conn.cursor()
        # 這裡讀取所有可能的別名欄位
        cursor.execute("SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱], [台大體系醫整庫欄位名稱], [台灣癌症登記中心] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap]")
        rows = cursor.fetchall()
        conn.close()

        # 建立地圖：序號+別名 -> "序號標準中文"
        alias_to_prefixed = {}
        for r in rows:
            seq = str(r[0]).strip().replace('.0', '')
            std_name = str(r[1]).strip()
            if not std_name: continue
            
            # 統一輸出格式：序號名稱 (中間無底線)
            target_prefixed = f"{seq}{std_name}" 
            
            # 遍歷所有欄位作為別名 (r[1:] 包含中、英、體系名等)
            for alias in r[1:]:
                if pd.notna(alias):
                    a = str(alias).strip()
                    if a:
                        # 僅支援序號與名稱直接連在一起的格式
                        variation = f"{seq}{a}"
                        alias_to_prefixed[variation] = target_prefixed

        # 執行重新命名 (嚴格比對大小寫)
        rename_map = {}
        for col in df.columns:
            c = str(col).strip()
            if c in alias_to_prefixed:
                rename_map[col] = alias_to_prefixed[c]
        
        selected_date_cols_std = []
        for col in selected_date_cols_raw:
            if col in rename_map:
                selected_date_cols_std.append(rename_map[col])
            else:
                selected_date_cols_std.append(col)

        df.rename(columns=rename_map, inplace=True)
        
        # --- B. 執行原本的處理邏輯 ---

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
            # 僅認序號開頭的 (例如 "1.3")
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
            age_col = find_col_by_seq_or_key("2.1") or "2.1診斷年齡"
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

        # 8. 最終依序號排序
        def get_sort_key(col_name):
            import re
            match = re.match(r'^(\d+\.?\d*\.?\d*)', col_name)
            if match:
                prefix = match.group(1)
                try:
                    return [int(x) for x in prefix.split('.')]
                except:
                    return [9999]
            return [9999]

        sorted_cols = sorted(df.columns, key=get_sort_key)
        df = df[sorted_cols]
        
        # 定義輸出的檔名
        base_name = os.path.basename(file_path)
        out_filename = f"Gen_{base_name}"
        out_path = os.path.join('data/temp', out_filename)
        
        if ext == ".xlsx": df.to_excel(out_path, index=False)
        else: df.to_csv(out_path, index=False, encoding="utf-8-sig")
        
        session['last_gen_output'] = out_path
        preview = df.head(20).fillna('').to_dict(orient='records')
        
        return jsonify({"ok": True, "preview": preview, "download_url": f"/api/data_gen/download"})

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
