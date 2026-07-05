from modules.services.db import get_conn

def get_site_name_from_db(site_code):
    """
    從資料庫的 site_mapping 資料表查詢部位代碼對應的名稱。
    1. 支援自動去除點號（如 C50.9 轉換為 C509）
    2. 若找不到細項名稱，會自動截取前三碼改查大類（如 C000 找不到，改查 C00-）
    """
    if not site_code:
        return "Unknown Primary Site"
        
    # 格式化代碼（移除空白、轉大寫、去點號，例如 C50.9 -> C509）
    site_code_clean = str(site_code).strip().upper().replace(".", "")
    
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # 步驟一：先精準查詢細項名稱（如 C509）
        cursor.execute("SELECT site_name FROM site_mapping WHERE site_code = ?", (site_code_clean,))
        row = cursor.fetchone()
        if row:
            return row[0]
            
        # 步驟二：如果精準查詢失敗，截取前三碼並加上減號查詢大類（如 C509 找不到，改查 C50-）
        if len(site_code_clean) >= 3:
            group_code = site_code_clean[:3] + "-"
            cursor.execute("SELECT site_name FROM site_mapping WHERE site_code = ?", (group_code,))
            row = cursor.fetchone()
            if row:
                return row[0]
                
        return "Unknown Site Code"
        
    except Exception as e:
        print(f"查詢部位名稱失敗: {e}")
        return "Unknown Site Code"
        
    finally:
        if conn:
            conn.close()