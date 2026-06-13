"""
messaging_routes.py — Pesan & Notifikasi
Tidak menggunakan Flask-Login. Semua auth via session custom.

Cara pakai di app.py:
    from messaging_routes import register_messaging
    register_messaging(app, mongo, login_required, get_current_user)
"""

from datetime import datetime
from bson import ObjectId
from flask import render_template, request, redirect, url_for, jsonify, session

ROLE_LEVEL = {
    "VP": 6, "GML": 5, "MANAGER_WOK": 4,
    "TS": 3, "TC": 3, "TL": 2, "SF": 1
}
ROLE_LABEL = {
    "VP": "Vice President", "GML": "General Manager Level",
    "MANAGER_WOK": "Manager WOK", "TS": "Territory Sales",
    "TC": "Territory Collection", "TL": "Team Leader", "SF": "Sales Force"
}
BROADCAST_ROLES = {"VP", "GML", "MANAGER_WOK", "TS", "TC"}


def register_messaging(app, mongo_inst, login_required_dec, get_current_user_fn):
    """Daftarkan semua route messaging ke Flask app."""
    db = mongo_inst.db

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _can_broadcast(user):
        role = (user.get("role") or user.get("jabatan") or "SF").upper()
        return role in BROADCAST_ROLES

    def _get_unread_counts(user_id: str) -> dict:
        msg_unread = db.messages.count_documents({
            "to_id": user_id, "is_read": False,
            "deleted_by_receiver": {"$ne": True}
        })
        notif_unread = db.notifications.count_documents({
            "$or": [{"target_ids": user_id}, {"target_all": True}],
            "reads": {"$not": {"$elemMatch": {"user_id": user_id}}}
        })
        return {"messages": msg_unread, "notifications": notif_unread}

    def _fmt_time(dt) -> str:
        if not dt:
            return "—"
        now  = datetime.now()
        diff = now - dt
        if diff.seconds < 60:   return "Baru saja"
        if diff.seconds < 3600: return f"{diff.seconds // 60} mnt lalu"
        if diff.days == 0:      return dt.strftime("%H:%M")
        if diff.days == 1:      return "Kemarin"
        if diff.days < 7:       return dt.strftime("%A")
        return dt.strftime("%d/%m/%Y")

    def _get_all_users(current_user) -> list:
        query = {"_id": {"$ne": ObjectId(str(current_user["_id"]))}}
        wok = current_user.get("wok", "")
        if wok:
            query["$or"] = [{"wok": wok}, {"wok": {"$exists": False}}, {"wok": ""}]
        return list(db.users.find(query, {
            "nama": 1, "username": 1, "role": 1, "jabatan": 1, "wok": 1
        }).sort("nama", 1).limit(300))

    def _build_target_label(target, wok, role, count):
        if target == "all":  return "Semua User"
        if target == "wok":  return f"WOK {wok}"
        if target == "role": return ROLE_LABEL.get(role, role)
        return f"{count} user dipilih"

    # ── API: unread badge ──────────────────────────────────────────────────────

    @app.route("/api/unread-counts")
    @login_required_dec
    def api_unread_counts():
        uid    = session["user_id"]
        counts = _get_unread_counts(uid)
        return jsonify(counts)

    # ── Messages ──────────────────────────────────────────────────────────────

    @app.route("/messages")
    @login_required_dec
    def messages_inbox():
        user = get_current_user_fn()
        uid  = str(user["_id"])
        tab  = request.args.get("tab", "inbox")

        if tab == "sent":
            convs = list(db.messages.find({
                "from_id": uid, "deleted_by_sender": {"$ne": True}
            }).sort("created_at", -1).limit(100))
        elif tab == "starred":
            convs = list(db.messages.find({
                "$or": [{"from_id": uid}, {"to_id": uid}],
                "starred_by": uid
            }).sort("created_at", -1).limit(100))
        else:
            convs = list(db.messages.find({
                "to_id": uid, "deleted_by_receiver": {"$ne": True}
            }).sort("created_at", -1).limit(100))

        for m in convs:
            other_id = m["from_id"] if tab != "sent" else m["to_id"]
            other = None
            if other_id:
                try:
                    other = db.users.find_one({"_id": ObjectId(other_id)},
                                              {"nama": 1, "role": 1, "jabatan": 1})
                except Exception:
                    pass
            m["other_user"] = other
            m["time_fmt"]   = _fmt_time(m.get("created_at"))
            body = m.get("body", "")
            m["preview"] = (body[:80] + "…") if len(body) > 80 else body

        unread    = db.messages.count_documents({"to_id": uid, "is_read": False})
        all_users = _get_all_users(user)
        counts    = _get_unread_counts(uid)

        return render_template("messages.html",
            user=user, tab=tab,
            conversations=convs,
            all_users=all_users,
            unread_total=unread,
            counts=counts,
            role_label=ROLE_LABEL,
            msg=None
        )

    @app.route("/messages/compose", methods=["GET", "POST"])
    @login_required_dec
    def messages_compose():
        user = get_current_user_fn()
        uid  = str(user["_id"])

        if request.method == "POST":
            data     = request.get_json() or request.form
            to_id    = (data.get("to_id") or "").strip()
            subject  = (data.get("subject") or "(Tanpa Judul)").strip()
            body     = (data.get("body") or "").strip()
            priority = data.get("priority", "normal")

            if not to_id or not body:
                return jsonify({"ok": False, "msg": "Penerima dan isi pesan wajib diisi."}), 400

            try:
                receiver = db.users.find_one({"_id": ObjectId(to_id)})
            except Exception:
                receiver = None
            if not receiver:
                return jsonify({"ok": False, "msg": "User penerima tidak ditemukan."}), 404

            doc = {
                "from_id":    uid,
                "from_nama":  user.get("nama", "?"),
                "to_id":      to_id,
                "to_nama":    receiver.get("nama", "?"),
                "subject":    subject[:200],
                "body":       body[:5000],
                "priority":   priority,
                "is_read":    False,
                "starred_by": [],
                "deleted_by_sender":   False,
                "deleted_by_receiver": False,
                "created_at": datetime.now(),
                "read_at":    None,
            }
            result = db.messages.insert_one(doc)

            # Notif otomatis ke penerima
            db.notifications.insert_one({
                "type":       "message",
                "from_id":    uid,
                "from_nama":  user.get("nama", "?"),
                "target_ids": [to_id],
                "target_all": False,
                "title":      f"Pesan dari {user.get('nama','?')}",
                "body":       subject,
                "link":       f"/messages/view/{result.inserted_id}",
                "priority":   priority,
                "reads":      [],
                "created_at": datetime.now(),
            })

            if request.is_json:
                return jsonify({"ok": True, "msg": "Pesan terkirim!", "id": str(result.inserted_id)})
            return redirect(url_for("messages_inbox", tab="sent"))

        # GET
        to_id   = request.args.get("to_id", "")
        to_user = None
        if to_id:
            try:
                to_user = db.users.find_one({"_id": ObjectId(to_id)},
                                            {"nama": 1, "role": 1, "jabatan": 1})
            except Exception:
                pass

        counts = _get_unread_counts(uid)
        return render_template("messages.html",
            user=user, tab="compose",
            all_users=_get_all_users(user),
            to_user=to_user, to_id=to_id,
            conversations=[], unread_total=0,
            counts=counts, role_label=ROLE_LABEL, msg=None
        )

    @app.route("/messages/view/<msg_id>")
    @login_required_dec
    def messages_view(msg_id):
        user = get_current_user_fn()
        uid  = str(user["_id"])

        try:
            msg = db.messages.find_one({"_id": ObjectId(msg_id)})
        except Exception:
            msg = None

        if not msg or uid not in (msg["from_id"], msg["to_id"]):
            return redirect(url_for("messages_inbox"))

        if uid == msg["to_id"] and not msg["is_read"]:
            db.messages.update_one(
                {"_id": ObjectId(msg_id)},
                {"$set": {"is_read": True, "read_at": datetime.now()}}
            )
            msg["is_read"] = True

        msg["time_fmt"] = _fmt_time(msg.get("created_at"))

        def _get_user(oid):
            try:
                return db.users.find_one({"_id": ObjectId(oid)},
                                         {"nama": 1, "role": 1, "jabatan": 1, "wok": 1})
            except Exception:
                return None

        sender   = _get_user(msg["from_id"])
        receiver = _get_user(msg["to_id"])
        counts   = _get_unread_counts(uid)

        return render_template("messages.html",
            user=user, tab="view",
            msg=msg, sender=sender, receiver=receiver,
            all_users=_get_all_users(user),
            conversations=[], unread_total=0,
            counts=counts, role_label=ROLE_LABEL
        )

    @app.route("/messages/action", methods=["POST"])
    @login_required_dec
    def messages_action():
        user   = get_current_user_fn()
        uid    = str(user["_id"])
        data   = request.get_json() or {}
        action = data.get("action")
        msg_id = data.get("msg_id")

        try:
            msg = db.messages.find_one({"_id": ObjectId(msg_id)})
        except Exception:
            msg = None

        if not msg or uid not in (msg["from_id"], msg["to_id"]):
            return jsonify({"ok": False, "msg": "Tidak ditemukan."}), 404

        if action == "star":
            starred = msg.get("starred_by", [])
            if uid in starred:
                db.messages.update_one({"_id": ObjectId(msg_id)},
                                       {"$pull": {"starred_by": uid}})
                return jsonify({"ok": True, "starred": False})
            else:
                db.messages.update_one({"_id": ObjectId(msg_id)},
                                       {"$push": {"starred_by": uid}})
                return jsonify({"ok": True, "starred": True})

        elif action == "delete":
            if uid == msg["from_id"]:
                db.messages.update_one({"_id": ObjectId(msg_id)},
                                       {"$set": {"deleted_by_sender": True}})
            else:
                db.messages.update_one({"_id": ObjectId(msg_id)},
                                       {"$set": {"deleted_by_receiver": True}})
            return jsonify({"ok": True, "msg": "Pesan dihapus."})

        elif action == "mark_unread":
            db.messages.update_one({"_id": ObjectId(msg_id)},
                                   {"$set": {"is_read": False, "read_at": None}})
            return jsonify({"ok": True})

        return jsonify({"ok": False, "msg": "Aksi tidak dikenal."}), 400

    # ── Notifications ─────────────────────────────────────────────────────────

    @app.route("/notifications")
    @login_required_dec
    def notifications_list():
        user = get_current_user_fn()
        uid  = str(user["_id"])

        notifs = list(db.notifications.find({
            "$or": [{"target_ids": uid}, {"target_all": True}]
        }).sort("created_at", -1).limit(80))

        for n in notifs:
            n["time_fmt"]    = _fmt_time(n.get("created_at"))
            reads            = n.get("reads", [])
            n["sudah_dibaca"]= any(r.get("user_id") == uid for r in reads)
            n["read_count"]  = len(reads)

        unread       = sum(1 for n in notifs if not n["sudah_dibaca"])
        can_broadcast= _can_broadcast(user)
        counts       = _get_unread_counts(uid)

        return render_template("notifications.html",
            user=user, notifs=notifs, unread=unread,
            can_broadcast=can_broadcast,
            all_users=_get_all_users(user) if can_broadcast else [],
            counts=counts,
            BROADCAST_ROLES=BROADCAST_ROLES,
            ROLE_LABEL=ROLE_LABEL,
            tab="inbox"
        )

    @app.route("/notifications/send", methods=["POST"])
    @login_required_dec
    def notifications_send():
        user = get_current_user_fn()
        if not _can_broadcast(user):
            return jsonify({"ok": False, "msg": "Akses ditolak."}), 403

        uid  = str(user["_id"])
        data = request.get_json() or request.form

        title      = (data.get("title") or "").strip()
        body       = (data.get("body") or "").strip()
        priority   = data.get("priority", "normal")
        notif_type = data.get("notif_type", "info")
        target     = data.get("target", "all")
        target_wok = data.get("target_wok", "")
        target_role= data.get("target_role", "")
        target_ids = data.get("target_ids", [])
        link       = data.get("link", "")

        if not title or not body:
            return jsonify({"ok": False, "msg": "Judul dan isi wajib diisi."}), 400

        target_all   = False
        resolved_ids = []

        if target == "all":
            target_all = True
        elif target == "wok":
            users = list(db.users.find({"wok": target_wok}, {"_id": 1}))
            resolved_ids = [str(u["_id"]) for u in users]
        elif target == "role":
            users = list(db.users.find({
                "$or": [{"role": target_role}, {"jabatan": target_role}]
            }, {"_id": 1}))
            resolved_ids = [str(u["_id"]) for u in users]
        elif target == "specific":
            resolved_ids = target_ids if isinstance(target_ids, list) else [target_ids]

        result = db.notifications.insert_one({
            "type":         notif_type,
            "from_id":      uid,
            "from_nama":    user.get("nama", "?"),
            "from_role":    user.get("role") or user.get("jabatan", ""),
            "target_all":   target_all,
            "target_ids":   resolved_ids,
            "target_wok":   target_wok,
            "target_role":  target_role,
            "target_label": _build_target_label(target, target_wok, target_role, len(resolved_ids)),
            "title":        title[:200],
            "body":         body[:2000],
            "priority":     priority,
            "link":         link[:300],
            "reads":        [],
            "created_at":   datetime.now(),
        })

        recipient = "semua user" if target_all else f"{len(resolved_ids)} user"
        return jsonify({"ok": True, "msg": f"Notifikasi terkirim ke {recipient}!",
                        "id": str(result.inserted_id)})

    @app.route("/notifications/read/<notif_id>", methods=["POST"])
    @login_required_dec
    def notifications_read(notif_id):
        user = get_current_user_fn()
        uid  = str(user["_id"])

        try:
            notif = db.notifications.find_one({"_id": ObjectId(notif_id)})
        except Exception:
            return jsonify({"ok": False}), 404

        if not notif:
            return jsonify({"ok": False}), 404

        already = any(r.get("user_id") == uid for r in notif.get("reads", []))
        if not already:
            db.notifications.update_one(
                {"_id": ObjectId(notif_id)},
                {"$push": {"reads": {"user_id": uid, "read_at": datetime.now()}}}
            )
        return jsonify({"ok": True})

    @app.route("/notifications/read-all", methods=["POST"])
    @login_required_dec
    def notifications_read_all():
        user = get_current_user_fn()
        uid  = str(user["_id"])
        now  = datetime.now()

        unread = list(db.notifications.find({
            "$or": [{"target_ids": uid}, {"target_all": True}],
            "reads": {"$not": {"$elemMatch": {"user_id": uid}}}
        }, {"_id": 1}))

        for n in unread:
            db.notifications.update_one(
                {"_id": n["_id"]},
                {"$push": {"reads": {"user_id": uid, "read_at": now}}}
            )
        return jsonify({"ok": True, "count": len(unread)})

    @app.route("/notifications/delete/<notif_id>", methods=["POST"])
    @login_required_dec
    def notifications_delete(notif_id):
        user = get_current_user_fn()
        uid  = str(user["_id"])

        try:
            notif = db.notifications.find_one({"_id": ObjectId(notif_id)})
        except Exception:
            return jsonify({"ok": False}), 404

        if not notif:
            return jsonify({"ok": False}), 404

        user_role = (user.get("role") or user.get("jabatan", "")).upper()
        if notif["from_id"] != uid and user_role not in BROADCAST_ROLES:
            return jsonify({"ok": False, "msg": "Akses ditolak."}), 403

        db.notifications.delete_one({"_id": ObjectId(notif_id)})
        return jsonify({"ok": True})

    @app.route("/notifications/history")
    @login_required_dec
    def notifications_history():
        user = get_current_user_fn()
        if not _can_broadcast(user):
            return redirect(url_for("notifications_list"))

        uid    = str(user["_id"])
        notifs = list(db.notifications.find({"from_id": uid})
                      .sort("created_at", -1).limit(50))
        for n in notifs:
            n["time_fmt"]  = _fmt_time(n.get("created_at"))
            n["read_count"]= len(n.get("reads", []))

        counts = _get_unread_counts(uid)
        return render_template("notifications.html",
            user=user, notifs=notifs, unread=0, can_broadcast=True,
            all_users=_get_all_users(user), counts=counts,
            BROADCAST_ROLES=BROADCAST_ROLES,
            ROLE_LABEL=ROLE_LABEL, tab="history"
        )

    return app