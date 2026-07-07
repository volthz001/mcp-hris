# routes/messages.py
# Blueprint untuk fitur pesan internal (session-based auth)

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from functools import wraps
from datetime import datetime
from bson.objectid import ObjectId
from extensions import mongo, get_current_user

messages_bp = Blueprint('messages', __name__)

# ─── Decorator Auth ──────────────────────────────────────────────
def login_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized", "message": "Silakan login terlebih dahulu"}), 401
        return f(*args, **kwargs)
    return decorated

# ─── Helper: Format waktu ────────────────────────────────────────
def _fmt_message_time(dt):
    if not dt: return "—"
    diff = datetime.now() - dt
    if diff.seconds < 60: return "Baru saja"
    if diff.seconds < 3600: return f"{diff.seconds // 60} mnt lalu"
    if diff.days == 0: return dt.strftime("%H:%M")
    if diff.days == 1: return "Kemarin"
    if diff.days < 7: return dt.strftime("%A")
    return dt.strftime("%d/%m/%Y")

# ─── GET: Halaman Inbox ──────────────────────────────────────────
@messages_bp.route('/pesan')
@login_required_api
def messages_inbox():
    uid = str(session["user_id"])
    tab = request.args.get("tab", "inbox")

    if tab == "sent":
        query = {"from_id": uid, "deleted_by_sender": {"$ne": True}}
    elif tab == "starred":
        query = {"starred_by": uid}
    else:
        query = {"to_id": uid, "deleted_by_receiver": {"$ne": True}}

    messages = list(mongo.db.messages.find(query).sort("created_at", -1).limit(100))

    for m in messages:
        m["time_fmt"] = _fmt_message_time(m.get("created_at"))
        m["preview"] = (m.get("body", "")[:80]) + ("..." if len(m.get("body", "")) > 80 else "")

        other_id = m.get("from_id") if tab != "sent" else m.get("to_id", "")
        try:
            other = mongo.db.users.find_one({"_id": ObjectId(other_id)}, {"nama": 1, "role": 1, "jabatan": 1})
        except:
            other = None

        if tab == "sent":
            m["to_nama"] = other.get("nama", "?") if other else m.get("to_nama", "?")
            m["from_nama"] = m.get("from_nama", "?")
        else:
            m["from_nama"] = other.get("nama", "?") if other else m.get("from_nama", "?")
            m["to_nama"] = m.get("to_nama", "?")

        m["other_user"] = other

    unread_total = mongo.db.messages.count_documents({
        "to_id": uid, 
        "is_read": False, 
        "deleted_by_receiver": {"$ne": True}
    })

    all_users = list(mongo.db.users.find(
        {"_id": {"$ne": ObjectId(uid)}}, 
        {"nama": 1, "role": 1, "jabatan": 1}
    ).sort("nama", 1))

    return render_template("messages.html",
        user=get_current_user(),
        tab=tab,
        conversations=messages,
        unread_total=unread_total,
        all_users=all_users,
        msg=None
    )

# ─── GET: Detail pesan ──────────────────────────────────────────
@messages_bp.route('/pesan/<msg_id>')
@login_required_api
def messages_view(msg_id):
    uid = str(session["user_id"])

    try:
        msg = mongo.db.messages.find_one({"_id": ObjectId(msg_id)})
    except:
        return redirect(url_for("messages.messages_inbox"))

    if not msg or uid not in (msg.get("from_id"), msg.get("to_id")):
        return redirect(url_for("messages.messages_inbox"))

    if msg.get("to_id") == uid and not msg.get("is_read"):
        mongo.db.messages.update_one(
            {"_id": ObjectId(msg_id)},
            {"$set": {"is_read": True, "read_at": datetime.now()}}
        )
        msg["is_read"] = True

    msg["time_fmt"] = _fmt_message_time(msg.get("created_at"))

    try:
        sender = mongo.db.users.find_one(
            {"_id": ObjectId(msg["from_id"])}, 
            {"nama": 1, "role": 1, "jabatan": 1}
        )
    except:
        sender = None

    return render_template("messages_detail.html",
        user=get_current_user(),
        msg=msg,
        sender=sender
    )

# ─── POST: Kirim pesan baru ─────────────────────────────────────
@messages_bp.route('/pesan/kirim', methods=['POST'])
@login_required_api
def messages_compose():
    uid = str(session["user_id"])
    data = request.get_json(silent=True) or request.form

    to_id = (data.get("to_id") or "").strip()
    subject = (data.get("subject") or "(Tanpa Judul)").strip()
    body = (data.get("body") or "").strip()
    priority = data.get("priority", "normal")

    if not to_id or not body:
        return jsonify({"ok": False, "msg": "Penerima dan isi pesan wajib diisi."}), 400

    try:
        receiver = mongo.db.users.find_one({"_id": ObjectId(to_id)}, {"nama": 1})
    except:
        return jsonify({"ok": False, "msg": "Penerima tidak valid."}), 400

    if not receiver:
        return jsonify({"ok": False, "msg": "Penerima tidak ditemukan."}), 404

    sender = get_current_user()

    result = mongo.db.messages.insert_one({
        "from_id": uid,
        "from_nama": sender.get("nama", "?"),
        "to_id": to_id,
        "to_nama": receiver.get("nama", "?"),
        "subject": subject[:200],
        "body": body[:5000],
        "priority": priority,
        "is_read": False,
        "starred_by": [],
        "deleted_by_sender": False,
        "deleted_by_receiver": False,
        "created_at": datetime.now(),
        "read_at": None
    })

    # Notifikasi untuk penerima
    mongo.db.notifications.insert_one({
        "type": "message",
        "from_id": uid,
        "from_nama": sender.get("nama", "?"),
        "target_ids": [to_id],
        "target_all": False,
        "title": f"Pesan baru dari {sender.get('nama', '?')}",
        "body": subject[:100],
        "link": f"/pesan/{result.inserted_id}",
        "priority": priority,
        "reads": [],
        "created_at": datetime.now()
    })

    if request.is_json:
        return jsonify({"ok": True, "msg": "Pesan terkirim!", "id": str(result.inserted_id)})

    return redirect(url_for("messages.messages_inbox", tab="sent"))

# ─── POST: Aksi pada pesan (star, delete, mark_unread) ─────────
@messages_bp.route('/pesan/action', methods=['POST'])
@login_required_api
def messages_action():
    uid = str(session["user_id"])
    data = request.get_json() or {}
    action = data.get("action")
    msg_id = data.get("msg_id")

    if not msg_id:
        return jsonify({"ok": False, "msg": "ID pesan diperlukan"}), 400

    try:
        msg = mongo.db.messages.find_one({"_id": ObjectId(msg_id)})
    except:
        return jsonify({"ok": False, "msg": "Pesan tidak ditemukan"}), 404

    if not msg or uid not in (msg.get("from_id"), msg.get("to_id")):
        return jsonify({"ok": False, "msg": "Akses ditolak"}), 403

    if action == "star":
        starred = msg.get("starred_by", [])
        if uid in starred:
            mongo.db.messages.update_one(
                {"_id": ObjectId(msg_id)},
                {"$pull": {"starred_by": uid}}
            )
            return jsonify({"ok": True, "starred": False})
        else:
            mongo.db.messages.update_one(
                {"_id": ObjectId(msg_id)},
                {"$push": {"starred_by": uid}}
            )
            return jsonify({"ok": True, "starred": True})

    elif action == "delete":
        if uid == msg.get("from_id"):
            mongo.db.messages.update_one(
                {"_id": ObjectId(msg_id)},
                {"$set": {"deleted_by_sender": True}}
            )
        else:
            mongo.db.messages.update_one(
                {"_id": ObjectId(msg_id)},
                {"$set": {"deleted_by_receiver": True}}
            )
        return jsonify({"ok": True, "msg": "Pesan dihapus"})

    elif action == "mark_unread":
        mongo.db.messages.update_one(
            {"_id": ObjectId(msg_id)},
            {"$set": {"is_read": False, "read_at": None}}
        )
        return jsonify({"ok": True})

    return jsonify({"ok": False, "msg": "Aksi tidak dikenal"}), 400
