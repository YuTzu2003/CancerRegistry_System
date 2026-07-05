from modules.services.db import get_conn

def get_histology_rules():
    """
    動態從資料庫載入最新的組織型態對照規則。
    這可以保證當使用者修改資料庫後，下一次查詢能立刻生效。
    """
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hist, behavior, raw_name, report_name, site_include, site_exclude, year_min, year_max 
            FROM histology_mapping
        """)
        
        rules = []
        for row in cursor.fetchall():
            rule = {
                "hist": int(row[0]),
                "behavior": int(row[1]),
                "raw_name": row[2],
                "report_name": row[3]
            }
            
            # 還原逗號分隔的部位代碼為列表
            if row[4]:
                rule["site_include"] = [item.strip() for item in row[4].split(",")]
            if row[5]:
                rule["site_exclude"] = [item.strip() for item in row[5].split(",")]
                
            # 還原年份限制
            if row[6] is not None:
                rule["year_min"] = int(row[6])
            if row[7] is not None:
                rule["year_max"] = int(row[7])
                
            rules.append(rule)
            
        return rules
    except Exception as e:
        print(f"從資料庫載入組織學規則失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 為了維持向後相容性，保留一次性靜態讀取的 HISTOLOGY_RULES
HISTOLOGY_RULES = get_histology_rules()
