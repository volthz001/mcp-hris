# routes/notifications.py
# Disesuaikan dengan struktur app.py (session-based auth, tanpa JWT)

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from bson.objectid import ObjectId
from extensions import mongo, get_current_user

# routes/notifications.py
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')

# ─── Decorator Auth (sama seperti di app.py) ──────────────────────────────
def login_required_api(f):
    """Decorator untuk API: cek session login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized", "message": "Silakan login terlebih dahulu"}), 401
        return f(*args, **kwargs)
    return decorated

# ─── GET: Ambil semua notifikasi user ──────────────────────────────────────
@notifications_bp.route('', methods=['GET'])
@login_required_api
def get_notifications():
    """Ambil semua notifikasi untuk user yang sedang login."""
    user_id = session.get("user_id")
    try:
        notifications = list(mongo.db.notifications.find(
            {'userId': user_id}
        ).sort('createdAt', -1))
        
        # Konversi ObjectId ke string untuk JSON response
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
    """Tandai satu notifikasi sebagai sudah dibaca."""
    user_id = session.get("user_id")
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
    """Tandai semua notifikasi user sebagai sudah dibaca."""
    user_id = session.get("user_id")
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
    """Hapus satu notifikasi milik user."""
    user_id = session.get("user_id")
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
    """
    Buat notifikasi baru.
    Body JSON:
    {
        "userId": "target_user_id",
        "title": "Judul Notifikasi",
        "message": "Isi pesan",
        "type": "alert" | "info" | "success" | "warning",
        "link": "/url/tujuan" (opsional)
    }
    """
    user_id = session.get("user_id")  # Sender ID
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Data tidak boleh kosong'}), 400
    
    target_user_id = data.get('userId')
    if not target_user_id:
        return jsonify({'success': False, 'message': 'Parameter userId wajib diisi'}), 400
    
    # Dapatkan nama pengirim
    sender = get_current_user()
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
    """Ambil jumlah notifikasi yang belum dibaca untuk user saat ini."""
    user_id = session.get("user_id")
    try:
        count = mongo.db.notifications.count_documents({
            'userId': user_id,
            'isRead': {'$ne': True}
        })
        return jsonify({'success': True, 'unreadCount': count}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
