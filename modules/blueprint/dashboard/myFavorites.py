import os
import json

FAVORITES_DIR = os.path.join('work', 'favorites')

def get_user_fav_file(db_id):
    return os.path.join(FAVORITES_DIR, f"{db_id}_favorites.json")

def load_user_favorites(db_id):
    file_path = get_user_fav_file(db_id)
    if not os.path.isfile(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_favorites(db_id, data):
    file_path = get_user_fav_file(db_id)
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True
