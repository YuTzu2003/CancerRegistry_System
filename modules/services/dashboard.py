from flask import Blueprint, request, session, jsonify
from modules.services.auth import login_required
from modules.blueprint.dashboard import get_favorites_logic,add_favorite_logic,rename_favorite_logic,delete_favorite_logic

favorites_bp = Blueprint('favorites', __name__)

@favorites_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    userid = session.get("userid")
    if not userid:
        return jsonify({"ok": False, "error": "請先登入系統"}), 401
    
    res, status = get_favorites_logic(userid)
    return jsonify(res), status

@favorites_bp.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    userid = session.get("userid")
    if not userid:
        return jsonify({"ok": False, "error": "請先登入系統"}), 401
    
    data = request.json or {}
    name = data.get("name", "").strip()
    behavior = data.get("behavior", "")
    cancers = data.get("cancers", [])
    
    res, status = add_favorite_logic(userid, name, behavior, cancers)
    return jsonify(res), status

@favorites_bp.route('/api/favorites/<int:fav_id>', methods=['PUT'])
@login_required
def rename_favorite(fav_id):
    userid = session.get("userid")
    if not userid:
        return jsonify({"ok": False, "error": "請先登入系統"}), 401
        
    data = request.json or {}
    name = data.get("name", "").strip()
    
    res, status = rename_favorite_logic(userid, fav_id, name)
    return jsonify(res), status

@favorites_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
@login_required
def delete_favorite(fav_id):
    userid = session.get("userid")
    if not userid:
        return jsonify({"ok": False, "error": "請先登入系統"}), 401
        
    res, status = delete_favorite_logic(userid, fav_id)
    return jsonify(res), status
