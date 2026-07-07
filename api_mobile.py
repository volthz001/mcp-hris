# -*- coding: utf-8 -*-
"""
api_mobile.py — API JSON untuk Vris (mobile companion app MCP-HRIS)

Kenapa file terpisah, bukan ditambahin langsung di app.py:
- app.py sudah 3300+ baris, nambah lagi di situ bikin makin susah di-maintain.
- Blueprint ini reuse koneksi MongoDB yang sama persis dengan app.py lewat
  `current_app.config['MONGO_DB']` (sudah di-set di app.py baris ~95:
  `app.config['MONGO_DB'] = db`) — jadi TIDAK ada koneksi MongoDB kedua,
  TIDAK ada skema data baru.

AUTH MODEL:
- Web tetap pakai session cookie (TIDAK DIUBAH sama sekali).
- Mobile pakai JWT Bearer token, independen dari session.
- Auth memakai app.secret_key yang sama (SECRET_KEY dari environment) untuk
  sign JWT — tidak perlu env var baru.

REVOKE MECHANISM (token_version):
- Setiap user document punya field `token_version` (default 0 kalau belum ada,
  lewat `.get("token_version", 0)` — TIDAK perlu migrasi data).
- Access token (15 menit) & refresh token (7 hari) menyimpan token_version
  saat di-issue. Setiap request dicek: token_version di JWT == token_version
  di DB sekarang?
- Kalau admin lock/deactivate user atau user ganti password, token_version
  di-increment (+1) di app.py (lihat PATCH_APP_PY.md). Efeknya: SEMUA token
  yang beredar untuk user itu (di semua device) langsung invalid — tidak
  perlu nunggu access token itu expired dalam 15 menit.
- Trade-off yang perlu kamu tahu: /auth/logout di sini increment token_version
  juga, artinya logout dari satu device = logout dari SEMUA device. Untuk
  HRIS internal skala kecil ini biasanya bukan masalah; kalau nanti butuh
  logout per-device, perlu redesign ke blocklist token individual.

GEOFENCE:
- SUDAH DIPUTUSKAN bareng user: SF kerja di lapangan (door-to-door sales
  lintas WOK), jadi TIDAK ADA validasi radius terhadap satu titik kantor.
- Yang tetap divalidasi di server: lat/lng harus berupa angka valid dalam
  rentang dunia nyata, dan accuracy > 0 (accuracy persis 0.0 sering jadi
  ciri khas aplikasi fake-GPS murahan — mirror dari heuristik yang sudah
  ada di client `mock_location_service.dart`, supaya validasi ini tidak
  bisa dilewati cuma dengan hit API langsung tanpa lewat app).
- Koordinat & accuracy tetap DISIMPAN di setiap record absensi untuk audit
  trail — sebelumnya backend sama sekali tidak menyimpan lokasi.
"""

import jwt
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, current_app, g
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import check_password_hash

api_bp = Blueprint("api_mobile", __name__)

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)

KASBON_LIMIT = 500_000
KASBON_MIN = 50_000
KASBON_WINDOW_DAYS = 30


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _db():
    """Ambil instance MongoDB yang sama dengan app.py (bukan koneksi baru)."""
    return current_app.config["MONGO_DB"]


def _err(message, status=400, code=None):
    body = {"success": False, "message": message}
    if code:
        body["error_code"] = code
    return jsonify(body), status


def _issue_tokens(user):
    now = datetime.utcnow()
    tv = user.get("token_version", 0)
    uid = str(user["_id"])

    access_payload = {
        "sub": uid,
        "role": user.get("role") or user.get("jabatan", "SF"),
        "tv": tv,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    refresh_payload = {
        "sub": uid,
        "tv": tv,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL,
    }
    secret = current_app.secret_key
    access_token = jwt.encode(access_payload, secret, algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, secret, algorithm="HS256")
    return access_token, refresh_token


def _decode(token):
    """Return (payload, error_message). error_message None kalau sukses."""
    try:
        payload = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token kedaluwarsa."
    except jwt.InvalidTokenError:
        return None, "Token tidak valid."


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "username": user.get("username", ""),
        "name": user.get("nama") or user.get("full_name") or user.get("username", ""),
        "nama": user.get("nama", ""),
        "email": user.get("email", ""),
        "role": user.get("role") or user.get("jabatan", "SF"),
        "nik": user.get("nik", ""),
        "no_hp": user.get("no_hp", ""),
        "alamat": user.get("alamat", ""),
        "wok": user.get("wok", ""),
        "area": user.get("area", ""),
    }


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _err("Header Authorization tidak ada atau salah format.", 401)

        token = auth_header.split(" ", 1)[1].strip()
        payload, error = _decode(token)
        if error:
            return _err(error, 401)
        if payload.get("type") != "access":
            return _err("Token bukan access token.", 401)

        try:
            user = _db().users.find_one({"_id": ObjectId(payload["sub"])})
        except InvalidId:
            return _err("Token tidak valid.", 401)

        if not user:
            return _err("User tidak ditemukan.", 401)
        if user.get("is_locked", False):
            return _err("Akun Anda dikunci. Hubungi administrator.", 403, "ACCOUNT_LOCKED")
        if user.get("status") == "pending":
            return _err("Akun belum diaktivasi.", 403, "ACCOUNT_PENDING")
        if user.get("token_version", 0) != payload.get("tv"):
            # Token diterbitkan sebelum akun di-lock/ganti-password/logout-paksa.
            return _err("Sesi tidak berlaku lagi. Silakan login ulang.", 401, "TOKEN_REVOKED")

        g.current_user = user
        g.current_user_id = str(user["_id"])
        return f(*args, **kwargs)

    return decorated


def role_required_api(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = g.current_user.get("role") or g.current_user.get("jabatan", "SF")
            if role not in roles:
                return _err("Akses ditolak untuk role ini.", 403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def _valid_coords(lat, lng, accuracy):
    if lat is None or lng is None or accuracy is None:
        return False, "Data lokasi tidak lengkap."
    try:
        lat, lng, accuracy = float(lat), float(lng), float(accuracy)
    except (TypeError, ValueError):
        return False, "Format data lokasi tidak valid."
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False, "Koordinat di luar jangkauan valid."
    if accuracy <= 0:
        # Sinyal fake-GPS murahan (accuracy sempurna/0), sama seperti heuristik
        # client di mock_location_service.dart — dicek ulang di server supaya
        # tidak bisa dilewati dengan hit API langsung tanpa app.
        return False, "Data akurasi lokasi mencurigakan. Aktifkan GPS dengan sinyal yang wajar."
    return True, None


@api_bp.route("/notifications/unread-count", methods=["GET"])
@jwt_required
def api_notifications_unread_count():
    count = _db().notifications.count_documents({
        'userId': g.current_user_id,
        'isRead': {'$ne': True}
    })
    return jsonify({'success': True, 'unreadCount': count})

@api_bp.route("/notifications", methods=["GET"])
@jwt_required
def api_notifications_list():
    notifs = list(_db().notifications.find(
        {'userId': g.current_user_id}
    ).sort('createdAt', -1).limit(50))
    for n in notifs:
        n['_id'] = str(n['_id'])
        if n.get('createdAt'):
            n['createdAt'] = n['createdAt'].isoformat()
    unread = sum(1 for n in notifs if not n.get('isRead', False))
    return jsonify({'success': True, 'data': notifs, 'unreadCount': unread})

@api_bp.route("/notifications/<notification_id>/read", methods=["PATCH"])
@jwt_required
def api_notification_mark_read(notification_id):
    from bson.errors import InvalidId
    try:
        oid = ObjectId(notification_id)
    except InvalidId:
        return _err("ID tidak valid.", 400)
    result = _db().notifications.update_one(
        {'_id': oid, 'userId': g.current_user_id},
        {'$set': {'isRead': True, 'readAt': datetime.utcnow()}}
    )
    if result.matched_count == 0:
        return _err("Notifikasi tidak ditemukan.", 404)
    return jsonify({'success': True})
# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════

@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return _err("Username dan password wajib diisi.")

    user = _db().users.find_one({"username": username})
    if not user:
        return _err("Username tidak ditemukan.", 401)
    if user.get("is_locked", False):
        return _err("Akun Anda dikunci. Hubungi administrator.", 403, "ACCOUNT_LOCKED")
    if user.get("status") == "pending":
        return _err("Akun belum diaktivasi oleh VP/GML.", 403, "ACCOUNT_PENDING")
    if not check_password_hash(user.get("password", ""), password):
        return _err("Password salah.", 401)

    access_token, refresh_token = _issue_tokens(user)
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": serialize_user(user),
    })


@api_bp.route("/auth/refresh", methods=["POST"])
def api_refresh():
    data = request.get_json(silent=True) or {}
    token = data.get("refresh_token")
    if not token:
        return _err("refresh_token wajib diisi.")

    payload, error = _decode(token)
    if error:
        return _err(error, 401)
    if payload.get("type") != "refresh":
        return _err("Token bukan refresh token.", 401)

    try:
        user = _db().users.find_one({"_id": ObjectId(payload["sub"])})
    except InvalidId:
        return _err("Token tidak valid.", 401)

    if not user or user.get("is_locked", False) or user.get("status") == "pending":
        return _err("Sesi tidak berlaku. Silakan login ulang.", 401)
    if user.get("token_version", 0) != payload.get("tv"):
        return _err("Sesi tidak berlaku lagi. Silakan login ulang.", 401, "TOKEN_REVOKED")

    access_token, new_refresh_token = _issue_tokens(user)
    return jsonify({"access_token": access_token, "refresh_token": new_refresh_token})


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required
def api_me():
    return jsonify({"user": serialize_user(g.current_user)})


@api_bp.route("/auth/logout", methods=["POST"])
@jwt_required
def api_logout():
    # Increment token_version = seluruh token user ini (semua device) invalid.
    # Lihat catatan trade-off di docstring atas file.
    _db().users.update_one(
        {"_id": g.current_user["_id"]},
        {"$inc": {"token_version": 1}},
    )
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════════════════
# ATTENDANCE (absensi)
# ══════════════════════════════════════════════════════════════════════════

def _wib_today_str():
    import pytz
    wib = pytz.timezone("Asia/Jakarta")
    return datetime.now(wib).strftime("%Y-%m-%d"), datetime.now(wib)


def _absensi_to_json(rec):
    if not rec:
        return None
    tanggal = rec.get("tanggal")

    def combine(jam):
        if not jam or not tanggal:
            return None
        return f"{tanggal}T{jam}"

    return {
        "id": str(rec["_id"]),
        "status": rec.get("status") or "alpha",
        "check_in_time": combine(rec.get("jam_masuk")),
        "check_out_time": combine(rec.get("jam_keluar")),
        "check_in_lat": rec.get("lat_masuk"),
        "check_in_lng": rec.get("lng_masuk"),
        "check_out_lat": rec.get("lat_keluar"),
        "check_out_lng": rec.get("lng_keluar"),
    }


@api_bp.route("/attendance/check-in", methods=["POST"])
@jwt_required
def api_checkin():
    data = request.get_json(silent=True) or {}
    ok, msg = _valid_coords(data.get("lat"), data.get("lng"), data.get("accuracy"))
    if not ok:
        return _err(msg)

    db = _db()
    user = g.current_user
    uid = g.current_user_id
    today_str, now = _wib_today_str()

    nama = user.get("nama") or user.get("full_name") or user.get("username")

    existing = db.absensi.find_one({"user_id": uid, "tanggal": today_str})
    if existing and existing.get("jam_masuk"):
        return _err("Anda sudah check-in hari ini.", 409)

    jam_masuk_str = now.strftime("%H:%M:%S")
    update = {
        "user_id": uid,
        "nama_karyawan": nama,
        "nik": user.get("nik", ""),
        "tanggal": today_str,
        "area": user.get("area", ""),
        "gml_id": user.get("gml_id"),
        "wok_id": user.get("wok_id"),
        "tl_id": user.get("tl_id"),
        "jam_masuk": jam_masuk_str,
        "status": "hadir",
        "lat_masuk": float(data["lat"]),
        "lng_masuk": float(data["lng"]),
        "accuracy_masuk": float(data["accuracy"]),
        "updated_at": now,
    }
    db.absensi.update_one(
        {"user_id": uid, "tanggal": today_str},
        {"$set": update, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    rec = db.absensi.find_one({"user_id": uid, "tanggal": today_str})
    return jsonify({"data": _absensi_to_json(rec)})


@api_bp.route("/attendance/check-out", methods=["POST"])
@jwt_required
def api_checkout():
    data = request.get_json(silent=True) or {}
    ok, msg = _valid_coords(data.get("lat"), data.get("lng"), data.get("accuracy"))
    if not ok:
        return _err(msg)

    db = _db()
    uid = g.current_user_id
    today_str, now = _wib_today_str()

    existing = db.absensi.find_one({"user_id": uid, "tanggal": today_str})
    if not existing or not existing.get("jam_masuk"):
        return _err("Anda belum check-in hari ini.", 409)
    if existing.get("jam_keluar"):
        return _err("Anda sudah check-out hari ini.", 409)

    # CATATAN: web mewajibkan `keterangan_checkout` diisi manual. Vris saat
    # ini tidak mengirim field ini sama sekali — dibuat opsional di sini
    # supaya tidak blocking. Kalau kamu mau paritas penuh dengan web,
    # tambahin input teks di UI check-out Flutter dan kirim sebagai
    # `note` di body request.
    keterangan_checkout = (data.get("note") or "").strip()

    jam_keluar_str = now.strftime("%H:%M:%S")
    db.absensi.update_one(
        {"_id": existing["_id"]},
        {"$set": {
            "jam_keluar": jam_keluar_str,
            "keterangan_checkout": keterangan_checkout,
            "lat_keluar": float(data["lat"]),
            "lng_keluar": float(data["lng"]),
            "accuracy_keluar": float(data["accuracy"]),
            "updated_at": now,
        }}
    )
    rec = db.absensi.find_one({"_id": existing["_id"]})
    return jsonify({"data": _absensi_to_json(rec)})


@api_bp.route("/attendance/today", methods=["GET"])
@jwt_required
def api_attendance_today():
    today_str, _ = _wib_today_str()
    rec = _db().absensi.find_one({"user_id": g.current_user_id, "tanggal": today_str})
    return jsonify({"data": _absensi_to_json(rec)})


@api_bp.route("/attendance/history", methods=["GET"])
@jwt_required
def api_attendance_history():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    today = date.today()
    month = month or today.month
    year = year or today.year

    prefix = f"{year:04d}-{month:02d}"
    records = list(
        _db().absensi.find({
            "user_id": g.current_user_id,
            "tanggal": {"$regex": f"^{prefix}"},
        }).sort("tanggal", -1)
    )
    return jsonify({"data": [_absensi_to_json(r) for r in records]})


# ══════════════════════════════════════════════════════════════════════════
# KASBON
# ══════════════════════════════════════════════════════════════════════════

def _kasbon_to_json(k):
    return {
        "id": str(k["_id"]),
        "amount": k.get("nominal", 0),
        "reason": k.get("keterangan", ""),
        "status": k.get("status", "pending"),
        "created_at": k["created_at"].isoformat() if k.get("created_at") else None,
        "approver_name": k.get("approved_by"),
        "rejection_note": k.get("rejection_note"),
    }


@api_bp.route("/kasbon", methods=["GET"])
@jwt_required
def api_kasbon_list():
    role = g.current_user.get("role") or g.current_user.get("jabatan", "SF")
    db = _db()
    if role in ("VP", "GML"):
        items = list(db.kasbon.find({}).sort("created_at", -1).limit(200))
    else:
        items = list(db.kasbon.find({"user_id": g.current_user_id}).sort("created_at", -1).limit(100))
    return jsonify({"data": [_kasbon_to_json(k) for k in items]})


@api_bp.route("/kasbon", methods=["POST"])
@jwt_required
def api_kasbon_create():
    data = request.get_json(silent=True) or {}
    try:
        nominal = float(data.get("amount"))
    except (TypeError, ValueError):
        return _err("amount wajib berupa angka.")
    reason = (data.get("reason") or "").strip()

    if nominal < KASBON_MIN or nominal > KASBON_LIMIT:
        return _err(f"Nominal harus antara Rp {KASBON_MIN:,.0f} dan Rp {KASBON_LIMIT:,.0f}.")

    db = _db()
    uid = g.current_user_id
    cutoff = datetime.now() - timedelta(days=KASBON_WINDOW_DAYS)
    agg = list(db.kasbon.aggregate([
        {"$match": {
            "user_id": uid,
            "status": {"$in": ["approved", "pending"]},
            "created_at": {"$gte": cutoff},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$nominal"}}},
    ]))
    used_30d = agg[0]["total"] if agg else 0
    remaining = KASBON_LIMIT - used_30d
    if nominal > remaining:
        return _err(f"Kuota tidak cukup. Sisa kuota: Rp {remaining:,.0f}.", 409)

    today = date.today()
    doc = {
        "user_id": uid,
        "nama": g.current_user.get("nama") or g.current_user.get("username", "?"),
        "nominal": nominal,
        "keterangan": reason,
        "status": "pending",
        "bulan": today.month,
        "tahun": today.year,
        "created_at": datetime.now(),
        "approved_by": None,
        "approved_at": None,
    }
    result = db.kasbon.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"data": _kasbon_to_json(doc)}), 201


@api_bp.route("/kasbon/<kasbon_id>/approve", methods=["POST"])
@jwt_required
@role_required_api("VP", "GML")
def api_kasbon_approve(kasbon_id):
    try:
        oid = ObjectId(kasbon_id)
    except InvalidId:
        return _err("ID kasbon tidak valid.", 404)
    db = _db()
    result = db.kasbon.update_one(
        {"_id": oid},
        {"$set": {
            "status": "approved",
            "approved_by": g.current_user.get("nama") or g.current_user.get("username", "?"),
            "approved_at": datetime.now(),
        }}
    )
    if result.matched_count == 0:
        return _err("Kasbon tidak ditemukan.", 404)
    return jsonify({"success": True})


@api_bp.route("/kasbon/<kasbon_id>/reject", methods=["POST"])
@jwt_required
@role_required_api("VP", "GML")
def api_kasbon_reject(kasbon_id):
    data = request.get_json(silent=True) or {}
    try:
        oid = ObjectId(kasbon_id)
    except InvalidId:
        return _err("ID kasbon tidak valid.", 404)
    db = _db()
    result = db.kasbon.update_one(
        {"_id": oid},
        {"$set": {
            "status": "rejected",
            "approved_by": g.current_user.get("nama") or g.current_user.get("username", "?"),
            "approved_at": datetime.now(),
            "rejection_note": (data.get("note") or "").strip(),
        }}
    )
    if result.matched_count == 0:
        return _err("Kasbon tidak ditemukan.", 404)
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════════════════
# KPI (dashboard agregat WOK — bukan skor personal, lihat catatan Flutter)
# ══════════════════════════════════════════════════════════════════════════

@api_bp.route("/kpi/dashboard", methods=["GET"])
@jwt_required
@role_required_api("VP", "GML")
def api_kpi_dashboard():
    # Import lokal supaya tidak circular-import dengan app.py.
    from app import get_kpi_data_for_month, _empty_kpi_data

    today = date.today()
    month = request.args.get("month", default=today.month, type=int)
    year = request.args.get("year", default=today.year, type=int)
    wok = (request.args.get("wok") or g.current_user.get("wok") or "JAKTIM").upper()

    has_data = _db().kpi_ps.count_documents({"month": month, "year": year, "wok": wok}) > 0
    ctx = get_kpi_data_for_month(month, year, wok) if has_data else _empty_kpi_data(month, year, wok)

    # Remap 2 nama field supaya cocok persis dengan KpiSummary.fromJson di Flutter:
    top_sf = [
        {"nama": nama, "ps": ps}
        for nama, ps in zip(ctx.get("top_sf_labels", []), ctx.get("top_sf_values", []))
    ]
    ctx["top_sf"] = top_sf
    ctx["tl_summary_table"] = ctx.get("tl_details", [])

    return jsonify(ctx)
