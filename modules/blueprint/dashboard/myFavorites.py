import os
import json
import logging

FAVORITES_DIR = os.path.join('work', 'favorites')
FAVORITES_FILE = os.path.join(FAVORITES_DIR, 'myfavorites.json')

def _load_all_favorites():
    if not os.path.isfile(FAVORITES_FILE):
        return {}
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading myfavorites.json: {e}")
        return {}

def _save_all_favorites(data):
    try:
        os.makedirs(FAVORITES_DIR, exist_ok=True)
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error writing myfavorites.json: {e}")
        return False

def get_favorites_logic(userid):
    all_favs = _load_all_favorites()
    user_favs = all_favs.get(userid, [])
    return {"ok": True, "favorites": user_favs}, 200

def add_favorite_logic(userid, name, behavior, cancers):
    if not name:
        return {"ok": False, "error": "請輸入範本名稱"}, 400
        
    all_favs = _load_all_favorites()
    user_favs = all_favs.get(userid, [])
    
    # 檢查是否有同名範本
    if any(f["name"] == name for f in user_favs):
        return {"ok": False, "error": "已有相同的最愛範本名稱"}, 400
        
    # 自動配發遞增 ID
    max_id = max([f.get("id", 0) for f in user_favs], default=0)
    new_id = max_id + 1
    
    new_fav = {
        "id": new_id,
        "name": name,
        "behavior": behavior,
        "cancers": cancers
    }
    
    user_favs.append(new_fav)
    all_favs[userid] = user_favs
    
    if _save_all_favorites(all_favs):
        return {"ok": True, "favorite": new_fav}, 200
    else:
        return {"ok": False, "error": "儲存失敗，伺服器寫入錯誤"}, 500

def rename_favorite_logic(userid, fav_id, name):
    if not name:
        return {"ok": False, "error": "請輸入新範本名稱"}, 400
        
    all_favs = _load_all_favorites()
    user_favs = all_favs.get(userid, [])
    
    if any(f["name"] == name and f["id"] != fav_id for f in user_favs):
        return {"ok": False, "error": "已有相同的最愛範本名稱"}, 400
        
    found = False
    for f in user_favs:
        if f["id"] == fav_id:
            f["name"] = name
            found = True
            break
            
    if not found:
        return {"ok": False, "error": "找不到該最愛範本"}, 404
        
    all_favs[userid] = user_favs
    if _save_all_favorites(all_favs):
        return {"ok": True}, 200
    else:
        return {"ok": False, "error": "重新命名失敗，伺服器寫入錯誤"}, 500

def delete_favorite_logic(userid, fav_id):
    all_favs = _load_all_favorites()
    user_favs = all_favs.get(userid, [])
    
    new_user_favs = [f for f in user_favs if f["id"] != fav_id]
    if len(new_user_favs) == len(user_favs):
        return {"ok": False, "error": "找不到該最愛範本"}, 404
        
    all_favs[userid] = new_user_favs
    if _save_all_favorites(all_favs):
        return {"ok": True}, 200
    else:
        return {"ok": False, "error": "刪除失敗，伺服器寫入錯誤"}, 500
