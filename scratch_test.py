import sys
import os

# add to path
sys.path.insert(0, r"D:\YLH\CancerRegistry_System")

from modules.services.dashboard import _load_user_favorites, _save_user_favorites

db_id = "1"
user_favs = _load_user_favorites(db_id)
print("loaded user favs:", user_favs)

new_fav = {
    "id": 1,
    "name": "test",
    "behavior": "all",
    "cancers": ["test_cancer"]
}
user_favs.append(new_fav)

res = _save_user_favorites(db_id, user_favs)
print("Save result:", res)
