# routes/notifications.py
# Disesuaikan: sekarang menerima session (web) MAUPUN JWT Bearer (Vris/mobile)

import jwt as pyjwt
from flask import Blueprint, request, jsonify, session, current_app
from functools import wraps
from datetime import datetime
from bson.objectid import ObjectId
from extensions import mongo, get_current_user

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')

# ─── Helper: coba ambil user_id dari JWT Bearer (format sama seperti api_mobile.py) ──
def _uid_from_jwt():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = pyjwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        user = mongo.db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user or user.get("is_locked") or user.get("status") == "pending":
            return None
        if user.get("token_version", 0) != payload.get("tv"):
            return None
        return str(user["_id"])
    except Exception:
        return None

# ─── Decorator Auth: session (web) ATAU JWT (mobile/Vris) ────────────────
def login_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get("user_id") or _uid_from_jwt()
        if not uid:
            return jsonify({"error": "Unauthorized", "message": "Silakan login terlebih dahulu"}), 401
        request.auth_user_id = uid  # dipakai semua route di bawah, ganti session.get("user_id")
        return f(*args, **kwargs)
    return decorated

# ─── GET: Ambil semua notifikasi user ──────────────────────────────────────
@notifications_bp.route('', methods=['GET'])
@login_required_api
def get_notifications():
    user_id = request.auth_user_id
    try:
        notifications = list(mongo.db.notifications.find(
            {'userId': user_id}
        ).sort('createdAt', -1))

        for notif in notifications:
            notif['_id'] = str(notif['_id'])
            if notif.get('createdAt'):
                notif['createdAt'] = notif['createdAt'].isoformat()

        unread_count = sum(1 for n in notifications if not n.get('isRead', False))

        return jsonify({
            'success': True,
            'data': notifications,
            'count': len(notifications),
            'unreadCount': unread_count
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── PATCH: Tandai satu notifikasi sebagai sudah dibaca ──────────────────
@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@login_required_api
def mark_notification_read(notification_id):
    user_id = request.auth_user_id
    try:
        result = mongo.db.notifications.update_one(
            {'_id': ObjectId(notification_id), 'userId': user_id},
            {'$set': {'isRead': True, 'readAt': datetime.utcnow()}}
        )
        if result.matched_count == 0:
            return jsonify({'success': False, 'message': 'Notifikasi tidak ditemukan'}), 404
        return jsonify({'success': True, 'message': 'Notifikasi ditandai sudah dibaca'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── POST: Tandai SEMUA notifikasi sebagai sudah dibaca ──────────────────
@notifications_bp.route('/read-all', methods=['POST'])
@login_required_api
def mark_all_read():
    user_id = request.auth_user_id
    try:
        result = mongo.db.notifications.update_many(
            {'userId': user_id, 'isRead': {'$ne': True}},
            {'$set': {'isRead': True, 'readAt': datetime.utcnow()}}
        )
        return jsonify({
            'success': True,
            'message': f'{result.modified_count} notifikasi ditandai sudah dibaca'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── DELETE: Hapus satu notifikasi ─────────────────────────────────────────
@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@login_required_api
def delete_notification(notification_id):
    user_id = request.auth_user_id
    try:
        result = mongo.db.notifications.delete_one(
            {'_id': ObjectId(notification_id), 'userId': user_id}
        )
        if result.deleted_count == 0:
            return jsonify({'success': False, 'message': 'Notifikasi tidak ditemukan'}), 404
        return jsonify({'success': True, 'message': 'Notifikasi dihapus'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── POST: Buat notifikasi baru (untuk sistem/sender) ────────────────────
@notifications_bp.route('', methods=['POST'])
@login_required_api
def create_notification():
    user_id = request.auth_user_id  # Sender ID
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Data tidak boleh kosong'}), 400

    target_user_id = data.get('userId')
    if not target_user_id:
        return jsonify({'success': False, 'message': 'Parameter userId wajib diisi'}), 400

    sender = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    sender_name = sender.get('nama') or sender.get('username', 'Sistem') if sender else 'Sistem'

    try:
        notification = {
            'userId': target_user_id,
            'title': data.get('title', 'Notifikasi'),
            'message': data.get('message', ''),
            'type': data.get('type', 'alert'),
            'link': data.get('link', ''),
            'isRead': False,
            'readAt': None,
            'senderId': user_id,
            'senderName': sender_name,
            'createdAt': datetime.utcnow()
        }
        result = mongo.db.notifications.insert_one(notification)
        notification['_id'] = str(result.inserted_id)
        notification['createdAt'] = notification['createdAt'].isoformat()

        return jsonify({'success': True, 'data': notification}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── GET: Ambil jumlah notifikasi belum dibaca (untuk badge) ─────────────
@notifications_bp.route('/unread-count', methods=['GET'])
@login_required_api
def get_unread_count():
    user_id = request.auth_user_id
    try:
        count = mongo.db.notifications.count_documents({
            'userId': user_id,
            'isRead': {'$ne': True}
        })
        return jsonify({'success': True, 'unreadCount': count}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
