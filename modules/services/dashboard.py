from flask import Blueprint, request, session, jsonify
from modules.services.auth import login_required
from modules.blueprint.dashboard import load_user_favorites, save_user_favorites

dashboard_bp = Blueprint('dashboard', __name__)
@dashboard_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    return jsonify({"ok": True, "favorites": user_favs}), 200

@dashboard_bp.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    behavior = data.get("behavior", "")
    cancers = data.get("cancers", [])
    user_favs = load_user_favorites(db_id)
    
    if any(f.get("name") == name for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
        
    max_id = max([f.get("id", 0) for f in user_favs], default=0)
    new_id = max_id + 1
    new_fav = {"id": new_id,"name": name,"behavior": behavior,"cancers": cancers}
    user_favs.append(new_fav)
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True, "favorite": new_fav}), 200


@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['PUT'])
@login_required
def rename_favorite(fav_id):
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "請輸入新範本名稱"}), 400
     
    user_favs = load_user_favorites(db_id)
    if any(f.get("name") == name and f.get("id") != fav_id for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
       
    for f in user_favs:
        if f.get("id") == fav_id:
            f["name"] = name
            break     
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True}), 200

@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
@login_required
def delete_favorite(fav_id):
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    new_user_favs = [f for f in user_favs if f.get("id") != fav_id]
    if len(new_user_favs) == len(user_favs):
        return jsonify({"ok": False, "error": "找不到該最愛範本"}), 404      
    save_user_favorites(db_id, new_user_favs)
    return jsonify({"ok": True}), 200
