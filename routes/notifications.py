# routes/notifications.py
#
# Blueprint notifikasi untuk MCP HRIS.
#
# PERUBAHAN DARI VERSI LAMA:
#   - Semua route /api/v1/notifications/* memakai JWT Bearer (untuk Vris Flutter)
#   - Semua route /notifikasi/* memakai session (untuk web browser — sudah ada di app.py)
#   - Decorator jwt_required & g.current_user_id diambil dari api_mobile
#   - Schema notifikasi diseragamkan dengan yang dipakai app.py & messages_compose():
#       target_ids, target_all, reads (array), title/body/priority
#   - Field response diseragamkan: unreadCount (bukan 'count'), id (bukan '_id')
#
# URL PREFIX Blueprint ini: /api/v1/notifications  (didaftarkan di app.py)
# Full URL contoh: POST https://host/api/v1/notifications/unread-count

from flask import Blueprint, request, jsonify, g
from functools import wraps
from datetime import datetime
from bson.objectid import ObjectId
from bson.errors import InvalidId
from extensions import mongo

notifications_bp = Blueprint(
    'notifications',
    __name__,
    url_prefix='/api/v1/notifications'
)

# ─────────────────────────────────────────────────────────────────────────────
# AUTH — import jwt_required dari api_mobile supaya satu sumber kebenaran.
# Kalau api_mobile belum di-import saat module load, pakai lazy import
# di dalam fungsi.  g.current_user_id diset oleh decorator tersebut.
# ─────────────────────────────────────────────────────────────────────────────
def _jwt_required(f):
    """Thin wrapper: delegasi ke jwt_required di api_mobile."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from api_mobile import jwt_required as _jwt
        return _jwt(f)(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _db():
    return mongo.db


def _serialize_notif(n: dict, uid: str) -> dict:
    """Konversi dokumen MongoDB ke dict JSON-safe untuk Vris."""
    reads   = [r.get('user_id') for r in n.get('reads', [])]
    is_read = uid in reads
    return {
        'id':        str(n['_id']),
        'title':     n.get('title') or n.get('judul') or '(tanpa judul)',
        'body':      n.get('body')  or n.get('isi')   or '',
        'type':      n.get('type')  or n.get('priority') or 'info',
        'isRead':    is_read,
        'link':      n.get('link', ''),
        'senderName': n.get('from_nama', ''),
        'createdAt': n['createdAt'].isoformat() if n.get('createdAt') else
                     (n['created_at'].isoformat() if n.get('created_at') else None),
    }


def _build_query(uid: str) -> dict:
    """Query notifikasi yang relevan untuk user ini."""
    return {'$or': [{'target_ids': uid}, {'target_all': True}]}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/notifications/unread-count
# Dipakai oleh NotificationsProvider.refreshCount() di Vris
# Response: { "success": true, "unreadCount": 3 }
# ─────────────────────────────────────────────────────────────────────────────
@notifications_bp.route('/unread-count', methods=['GET'])
@_jwt_required
def api_unread_count():
    uid = g.current_user_id
    try:
        count = _db().notifications.count_documents({
            **_build_query(uid),
            'reads': {'$not': {'$elemMatch': {'user_id': uid}}}
        })
        return jsonify({'success': True, 'unreadCount': count}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/notifications?page=1&limit=20
# Dipakai oleh NotificationsRepository.getList() di Vris
# Response: { "success": true, "data": [...], "unreadCount": 3, "total": 15 }
# ─────────────────────────────────────────────────────────────────────────────
@notifications_bp.route('', methods=['GET'])
@_jwt_required
def api_list():
    uid   = g.current_user_id
    page  = max(1, int(request.args.get('page', 1)))
    limit = min(50, max(1, int(request.args.get('limit', 20))))
    skip  = (page - 1) * limit

    q = _build_query(uid)
    try:
        total = _db().notifications.count_documents(q)
        docs  = list(
            _db().notifications.find(q)
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )

        items     = [_serialize_notif(n, uid) for n in docs]
        unread    = sum(1 for i in items if not i['isRead'])

        return jsonify({
            'success':    True,
            'data':       items,
            'unreadCount': unread,
            'total':      total,
            'page':       page,
            'limit':      limit,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/notifications/<notification_id>/read
# Tandai satu notifikasi sebagai sudah dibaca
# Response: { "success": true }
# ─────────────────────────────────────────────────────────────────────────────
@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@_jwt_required
def api_mark_read(notification_id):
    uid = g.current_user_id
    try:
        oid = ObjectId(notification_id)
    except InvalidId:
        return jsonify({'success': False, 'message': 'ID notifikasi tidak valid.'}), 400

    try:
        result = _db().notifications.update_one(
            {
                '_id': oid,
                **_build_query(uid),
                'reads.user_id': {'$ne': uid},
            },
            {
                '$push': {
                    'reads': {'user_id': uid, 'read_at': datetime.utcnow()}
                }
            }
        )
        # matched_count 0 bisa berarti sudah dibaca atau tidak ditemukan — keduanya OK
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/notifications/mark-all-read
# Dipakai oleh NotificationsRepository.markAllRead() di Vris
# Response: { "success": true, "updated": 5 }
# ─────────────────────────────────────────────────────────────────────────────
@notifications_bp.route('/mark-all-read', methods=['POST'])
@_jwt_required
def api_mark_all_read():
    uid = g.current_user_id
    try:
        result = _db().notifications.update_many(
            {
                **_build_query(uid),
                'reads.user_id': {'$ne': uid},
            },
            {
                '$push': {
                    'reads': {'user_id': uid, 'read_at': datetime.utcnow()}
                }
            }
        )
        return jsonify({'success': True, 'updated': result.modified_count}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/v1/notifications/<notification_id>
# Hapus satu notifikasi (hanya yang target_ids mengandung user ini)
# Response: { "success": true }
# ─────────────────────────────────────────────────────────────────────────────
@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@_jwt_required
def api_delete(notification_id):
    uid = g.current_user_id
    try:
        oid = ObjectId(notification_id)
    except InvalidId:
        return jsonify({'success': False, 'message': 'ID notifikasi tidak valid.'}), 400

    try:
        # Hanya boleh hapus notifikasi yang memang untuk user ini
        # Notif target_all tidak bisa dihapus dari sisi user (hanya VP/GML yang bisa)
        result = _db().notifications.delete_one(
            {'_id': oid, 'target_ids': uid, 'target_all': {'$ne': True}}
        )
        if result.deleted_count == 0:
            return jsonify({
                'success': False,
                'message': 'Notifikasi tidak ditemukan atau tidak dapat dihapus.'
            }), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
