"""
app.py — PT. Mega Creative Promosindo
Sistem Manajemen: Kasbon, Absensi, KPI, Pesan, Notifikasi
Flask + Flask-PyMongo + Session-based Auth (TANPA Flask-Login)
"""

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
# Di bagian atas app.py, setelah import lainnya
#from email_utils import send_password_reset_email, send_reset_confirmation_email
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os, io, calendar, json
import hashlib
import hmac
from functools import wraps
import threading
import pytz
import uuid
from flask_wtf.csrf import CSRFProtect
import pandas as pd
from bson import ObjectId
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, make_response, Blueprint,send_file,get_flashed_messages
)
import secrets
from dotenv import load_dotenv
from flask_pymongo import PyMongo
from collections import defaultdict
from datetime import datetime, date, timedelta,time
from werkzeug.security import generate_password_hash, check_password_hash

# ══════════════════════════════════════════════════════════════════════════════
# 1. KONFIGURASI ENVIRONMENT (WAJIB ADA)
# ══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
csrf = CSRFProtect(app)
WTF_CSRF_ENABLED = True
# Load .env hanya jika file ada (development)
if os.path.exists('.env'):
    load_dotenv()
    print("✅ Memuat konfigurasi dari file .env")

# ══════════════════════════════════════════════════════════════════════════════
# 2. SECRET KEY (WAJIB DARI ENVIRONMENT DI PRODUCTION)
# ══════════════════════════════════════════════════════════════════════════════
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if os.environ.get("FLASK_ENV") == 'production':
        raise ValueError("SECRET_KEY harus diset di environment variable untuk production!")
    else:
        # Development: generate otomatis (tapi berubah tiap restart)
        SECRET_KEY = secrets.token_hex(32)
        print("⚠️ PERINGATAN: Menggunakan SECRET_KEY sementara (random). Tetapkan di .env untuk persistensi session.")

app.secret_key = SECRET_KEY
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
# ══════════════════════════════════════════════════════════════════════════════
# 3. MONGODB URI (WAJIB DARI ENVIRONMENT, TIDAK ADA FALLBACK)
# ══════════════════════════════════════════════════════════════════════════════
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI harus diset di environment variable!")

app.config["MONGO_URI"] = MONGO_URI

# ══════════════════════════════════════════════════════════════════════════════
# 4. KONFIGURASI SESSION (KEAMANAN COOKIE)
# ══════════════════════════════════════════════════════════════════════════════
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,        # Mencegah akses cookie via JavaScript
    SESSION_COOKIE_SAMESITE='Lax',       # Melindungi dari CSRF
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8)
)

# Aktifkan Secure cookie hanya jika menggunakan HTTPS (di production)
if os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true":
    app.config["SESSION_COOKIE_SECURE"] = True

# ══════════════════════════════════════════════════════════════════════════════
# 5. INISIALISASI MONGODB (SETELAH URI DI SET)
# ══════════════════════════════════════════════════════════════════════════════
mongo = PyMongo(app)    

# ══════════════════════════════════════════════════════════════════════════════
# KONSTANTA
# ══════════════════════════════════════════════════════════════════════════════
# Tempat penyimpanan progress upload (in-memory)
upload_progress = {}
BULAN_NAMA = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember"
]
MONTHS_LIST = [(i+1, BULAN_NAMA[i]) for i in range(12)]
WOK_LIST    = ["JAKTIM","JAKBAR","JAKSEL","JAKUT","JAKPUS",
               "DEPOK","BEKASI","BOGOR","TANGERANG"]
ROLE_LIST   = ["VP","GML","MANAGER_WOK","TS","TC","TL","SF"]
WIB = pytz.timezone('Asia/Jakarta')
def get_current_time_wib():
    return datetime.now(WIB)

def is_time_between(start_hour, start_min, end_hour, end_min, current_time=None):
    if current_time is None:
        current_time = get_current_time_wib()
    start = current_time.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    end   = current_time.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
    return start <= current_time <= end

from bson import ObjectId
from bson.errors import InvalidId

def get_user_detail(user_id):
    try:
        # Pastikan user_id bisa dijadikan ObjectId
        if isinstance(user_id, str):
            oid = ObjectId(user_id)
        else:
            oid = user_id
        user = mongo.db.users.find_one({"_id": oid})
    except (InvalidId, Exception):
        user = None

    if not user:
        return None, None, None, None, None, None

    # Coba beberapa kemungkinan nama field
    nama = user.get("nama") or user.get("full_name") or user.get("name") or user.get("username")
    nik = user.get("nik") or ""
    area = user.get("area") or ""
    gml_id = user.get("gml_id")
    wok_id = user.get("wok_id")
    tl_id = user.get("tl_id")
    
    return nama, nik, area, gml_id, wok_id, tl_id
# ══════════════════════════════════════════════════════════════════════════════
# AUTH HELPERS  (TIDAK pakai Flask-Login)
# ══════════════════════════════════════════════════════════════════════════════
def login_required(f):
    """Decorator: redirect ke login jika belum login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Ambil dokumen user aktif dari MongoDB."""
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        return mongo.db.users.find_one({"_id": ObjectId(uid)})
    except Exception:
        return None


def role_required(*roles):
    """Decorator: batasi akses berdasarkan role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("Akses ditolak.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/login", methods=["GET", "POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def login():
    if "user_id" in session:
        # Sudah login -> cek apakah akun dikunci (ambil dokumen user dulu)
        existing_user = get_current_user()
        if existing_user and existing_user.get("is_locked", False):
            session.clear()
            flash("Akun Anda sedang dikunci. Hubungi administrator.", "danger")
            return render_template("login.html")
        return redirect(url_for("dashboard"))

    # Hapus semua flash message yang tersisa (hanya untuk method GET)
    if request.method == "GET":
        _ = get_flashed_messages()   # sekarang sudah terdefinisi

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = mongo.db.users.find_one({"username": username})
        
        if not user:
            flash("Username tidak ditemukan.", "danger")
            return render_template("login.html")

        if user.get("is_locked", False):
            flash("Akun Anda sedang dikunci. Hubungi administrator.", "danger")
            return render_template("login.html")

        # Blokir akun pending (belum diaktivasi VP/GML)
        if user.get("status") == "pending":
            flash("Akun Anda belum diaktivasi. Hubungi VP atau GML untuk aktivasi.", "warning")
            return render_template("login.html")

        if not check_password_hash(user.get("password", ""), password):
            flash("Password salah.", "danger")
            return render_template("login.html")

        session["user_id"] = str(user["_id"])
        session["username"] = user.get("username", "")
        session["name"] = user.get("nama") or user.get("full_name") or user.get("username", "")
        session["role"] = user.get("role") or user.get("jabatan", "SF")
        session["wok"] = user.get("wok", "")
        session["area"] = user.get("area", "")
        session["wok_id"] = user.get("wok_id", "")
        session["gml_id"] = user.get("gml_id", "")
        session["tl_id"] = user.get("tl_id", "")
        return redirect(url_for("dashboard"))

    return render_template("login.html")
def generate_reset_token(user_id, expires_hours=1):
    """Generate token reset password yang aman"""
    expiry = datetime.now() + timedelta(hours=expires_hours)
    # Buat string unique: user_id + expiry + secret_key
    data = f"{user_id}|{expiry.isoformat()}"
    signature = hmac.new(
        key=app.secret_key.encode('utf-8'),
        msg=data.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    token = f"{user_id}|{expiry.isoformat()}|{signature}"
    # Encode to base64 untuk URL safety
    return secrets.token_urlsafe(32) + "|" + token
def verify_reset_token(token):
    """Verifikasi token reset password, return user_id jika valid"""
    try:
        parts = token.split('|')
        if len(parts) < 4:
            return None
        
        # Extract parts (token_random|user_id|expiry|signature)
        token_random = parts[0]
        user_id = parts[1]
        expiry_str = parts[2]
        signature = parts[3] if len(parts) > 3 else None
        
        # Verify expiry
        expiry = datetime.fromisoformat(expiry_str)
        if expiry < datetime.now():
            return None
        
        # Verify signature
        data = f"{user_id}|{expiry_str}"
        expected = hmac.new(
            key=app.secret_key.encode('utf-8'),
            msg=data.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return None
        
        return user_id
    except Exception as e:
        print(f"Token verification error: {e}")
        return None
@app.route("/register", methods=["GET", "POST"])
@csrf.exempt
def register():
    """
    Register mandiri: karyawan daftar sendiri.
    - Role SELALU default ke SF (tidak bisa dipilih dari form)
    - Status akun = 'pending' — tidak bisa login sampai VP/GML aktifkan
    - Tujuan: mencegah siapapun membuat akun VP/GML dari luar
    """
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            nama     = data.get("nama", "").strip()
            nik      = data.get("nik", "").strip()
            wok      = data.get("wok", "").strip()
            area     = data.get("area", wok)
            email    = data.get("email", "").strip()
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            nama     = request.form.get("nama", "").strip()
            nik      = request.form.get("nik", "").strip()
            wok      = request.form.get("wok", "").strip()
            area     = request.form.get("area", wok)
            email    = request.form.get("email", "").strip()

        # Validasi wajib
        if not username or not password or not nama or not nik or not wok:
            if request.is_json:
                return jsonify({"success": False, "message": "Username, password, nama, nik, dan wok wajib diisi."}), 400
            flash("Semua field wajib diisi.", "danger")
            return render_template("register.html")

        # Validasi panjang password
        if len(password) < 8:
            if request.is_json:
                return jsonify({"success": False, "message": "Password minimal 8 karakter."}), 400
            flash("Password minimal 8 karakter.", "danger")
            return render_template("register.html")

        # Cek username duplikat
        if mongo.db.users.find_one({"username": username}):
            if request.is_json:
                return jsonify({"success": False, "message": "Username sudah terdaftar."}), 400
            flash("Username sudah terdaftar.", "danger")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)

        # Role SELALU SF, status SELALU pending
        new_user = {
            "username":   username,
            "password":   hashed_password,
            "nama":       nama,
            "nik":        nik,
            "wok":        wok.upper(),
            "area":       area or wok.upper(),
            "email":      email,
            "role":       "SF",       # ← HARDCODED, tidak dari form
            "jabatan":    "SF",
            "is_locked":  False,
            "status":     "pending",  # ← akun belum aktif, tunggu aktivasi VP/GML
            "gml_id":     None,
            "wok_id":     None,
            "tl_id":      None,
            "created_at": datetime.now()
        }

        try:
            mongo.db.users.insert_one(new_user)
            if request.is_json:
                return jsonify({"success": True, "message": "Registrasi berhasil. Akun menunggu aktivasi oleh admin."}), 201
            flash("✅ Registrasi berhasil! Akun Anda sedang menunggu aktivasi oleh VP/GML sebelum bisa digunakan.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            if request.is_json:
                return jsonify({"success": False, "message": f"Gagal registrasi: {str(e)}"}), 500
            flash(f"Gagal registrasi: {str(e)}", "danger")
            return render_template("register.html")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    month, year = today.month, today.year

    # Ringkasan cepat
    total_kasbon_pending = mongo.db.kasbon.count_documents({"status": "pending"})
    total_kasbon_bulan   = mongo.db.kasbon.count_documents({
        "bulan": month, "tahun": year
    })
    total_absensi_hari   = mongo.db.absensi.count_documents({
        "tanggal": today.strftime("%Y-%m-%d")
    })
    total_ps_bulan = mongo.db.kpi_ps.count_documents({"month": month, "year": year})

    # Notif unread (untuk badge)
    uid = session["user_id"]
    msg_unread = mongo.db.messages.count_documents({"to_id": uid, "is_read": False})
    notif_unread = mongo.db.notifications.count_documents({
        "$or": [{"target_ids": uid}, {"target_all": True}],
        "reads": {"$not": {"$elemMatch": {"user_id": uid}}}
    })

    return render_template("dashboard.html",
        user                 = get_current_user(),
        total_kasbon_pending = total_kasbon_pending,
        total_kasbon_bulan   = total_kasbon_bulan,
        total_absensi_hari   = total_absensi_hari,
        total_ps_bulan       = total_ps_bulan,
        msg_unread           = msg_unread,
        notif_unread         = notif_unread,
        today                = today,
    )


# ══════════════════════════════════════════════════════════════════════════════
# KASBON
# ══════════════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────
# HELPER — Hitung kuota kasbon rolling 30 hari
# ─────────────────────────────────────────────────────────────
def get_kasbon_limit_info(user_id):
    """
    Logika:
    - Limit = Rp 500.000 per 30 hari rolling window
    - Kasbon yang dihitung: status 'approved' atau 'pending' dalam 30 hari terakhir
    - Kasbon 'rejected' tidak dihitung (dianggap batal)
    - Reset otomatis saat entri tertua keluar dari window 30 hari
 
    Return dict:
      used_30d        : nominal terpakai dalam 30 hari
      remaining       : sisa kuota (max 500.000 - used)
      can_apply       : bool, boleh ajukan kalau remaining >= 50.000
      limit           : 500000
      reset_date      : datetime — kapan slot pertama expire
      days_until_reset: int hari
      active_entries  : list kasbon aktif dalam window
      window_days     : 30
    """
    LIMIT  = 500_000
    MIN    = 50_000
    WINDOW = 30
 
    cutoff = datetime.now() - timedelta(days=WINDOW)
 
    active = list(mongo.db.kasbon.find({
        "user_id":    user_id,
        "status":     {"$in": ["approved", "pending"]},
        "created_at": {"$gte": cutoff},
    }).sort("created_at", 1))   # urut dari tertua
 
    used      = sum(k.get("nominal", 0) for k in active)
    remaining = max(0, LIMIT - used)
    can_apply = remaining >= MIN  # harus ada sisa cukup untuk minimum bon
 
    # Reset = tanggal tertua + 30 hari
    reset_date       = None
    days_until_reset = None
    if active:
        oldest = active[0].get("created_at")
        if oldest:
            reset_date       = oldest + timedelta(days=WINDOW)
            days_until_reset = max(0, (reset_date.date() - date.today()).days)
 
    return {
        "used_30d":          used,
        "remaining":         remaining,
        "can_apply":         can_apply,
        "limit":             LIMIT,
        "min":               MIN,
        "reset_date":        reset_date,
        "days_until_reset":  days_until_reset,
        "active_entries":    active,
        "window_days":       WINDOW,
        "pct_used":          round(min(used / LIMIT * 100, 100), 1),
    }
 





 #===============================================================================
 #messages
 #===============================================================================
 # ============================================================
# MESSAGING ROUTES - FIXED VERSION
# ============================================================
# Di awal app.py, setelah import
_ROLE_LABEL = {
    "VP": "Vice President",
    "GML": "General Manager Level",
    "MANAGER_WOK": "Manager WOK",
    "TS": "Territory Sales",
    "TC": "Territory Collection",
    "TL": "Team Leader",
    "SF": "Sales Force"
}

# Helper function
def _fmt_message_time(dt):
    if not dt: return "—"
    from datetime import datetime
    diff = datetime.now() - dt
    if diff.seconds < 60: return "Baru saja"
    if diff.seconds < 3600: return f"{diff.seconds // 60} mnt lalu"
    if diff.days == 0: return dt.strftime("%H:%M")
    if diff.days == 1: return "Kemarin"
    if diff.days < 7: return dt.strftime("%A")
    return dt.strftime("%d/%m/%Y")

@app.route("/pesan")
@login_required
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
    
    # ✅ FIXED: Hanya inclusion, no mixing
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
        role_label=_ROLE_LABEL,  # ✅ sekarang terdefinisi
        msg=None
    )

@app.route("/pesan/<msg_id>")
@login_required
def messages_view(msg_id):
    uid = str(session["user_id"])
    
    try:
        msg = mongo.db.messages.find_one({"_id": ObjectId(msg_id)})
    except:
        return redirect(url_for("messages_inbox"))
    
    if not msg or uid not in (msg.get("from_id"), msg.get("to_id")):
        return redirect(url_for("messages_inbox"))
    
    # Mark as read jika penerima
    if msg.get("to_id") == uid and not msg.get("is_read"):
        mongo.db.messages.update_one(
            {"_id": ObjectId(msg_id)},
            {"$set": {"is_read": True, "read_at": datetime.now()}}
        )
        msg["is_read"] = True
    
    msg["time_fmt"] = _fmt_message_time(msg.get("created_at"))
    
    # Get sender info - ✅ FIXED projection
    try:
        sender = mongo.db.users.find_one(
            {"_id": ObjectId(msg["from_id"])}, 
            {"nama": 1, "role": 1, "jabatan": 1}  # Hanya inclusion
        )
    except:
        sender = None
    
    # Get conversation list untuk sidebar
    tab = "sent" if msg.get("from_id") == uid else "inbox"
    query = {"from_id": uid} if tab == "sent" else {"to_id": uid}
    query["deleted_by_sender" if tab == "sent" else "deleted_by_receiver"] = {"$ne": True}
    
    conversations = list(mongo.db.messages.find(query).sort("created_at", -1).limit(100))
    
    for m in conversations:
        m["time_fmt"] = _fmt_message_time(m.get("created_at"))
        m["preview"] = (m.get("body", "")[:80])
        other_id = m.get("from_id") if tab != "sent" else m.get("to_id", "")
        try:
            other = mongo.db.users.find_one({"_id": ObjectId(other_id)}, {"nama": 1, "role": 1, "jabatan": 1})
        except:
            other = None
        if tab == "sent":
            m["to_nama"] = other.get("nama", "?") if other else m.get("to_nama", "?")
        else:
            m["from_nama"] = other.get("nama", "?") if other else m.get("from_nama", "?")
        m["other_user"] = other
    
    unread_total = mongo.db.messages.count_documents({
        "to_id": uid, 
        "is_read": False, 
        "deleted_by_receiver": {"$ne": True}
    })
    
    # ✅ FIXED: Gunakan inclusion (1) saja
    all_users = list(mongo.db.users.find(
        {"_id": {"$ne": ObjectId(uid)}},
        {"nama": 1, "role": 1, "jabatan": 1}  # Hanya inclusion
    ).sort("nama", 1))
    
    return render_template("messages.html",
        user=get_current_user(),
        tab=tab,
        conversations=conversations,
        unread_total=unread_total,
        all_users=all_users,
        role_label=_ROLE_LABEL,
        msg=msg,
        sender=sender
    )


@app.route("/pesan/kirim", methods=["POST"])
@login_required
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
    
    # Optional: Create notification for receiver
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
    
    return redirect(url_for("messages_inbox", tab="sent"))


@app.route("/pesan/action", methods=["POST"])
@login_required
def messages_action():
    """
    SINGLE ENDPOINT untuk SEMUA action pesan
    Actions: star, delete, mark_unread
    """
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
    
    # ACTION: STAR / UNSTAR
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
    
    # ACTION: DELETE
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
    
    # ACTION: MARK AS UNREAD
    elif action == "mark_unread":
        mongo.db.messages.update_one(
            {"_id": ObjectId(msg_id)},
            {"$set": {"is_read": False, "read_at": None}}
        )
        return jsonify({"ok": True})
    
    return jsonify({"ok": False, "msg": "Aksi tidak dikenal"}), 400


# ══════════════════════════════════════════════════════════════════════════════
# KASBON
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/kasbon")
@login_required
@role_required("VP", "GML", "MANAGER_WOK", "TL", "TS", "TC", "SF")
def kasbon_list():
    role    = session.get("role", "SF")
    uid     = session["user_id"]
    is_admin = role in ("VP", "GML")  # hanya VP & GML lihat semua
 
    if is_admin:
        # ── VP / GML: lihat SEMUA kasbon, bisa filter status ──────────────
        q = {}
        status_filter = request.args.get("status")
        if status_filter:
            q["status"] = status_filter
 
        items = list(mongo.db.kasbon.find(q).sort("created_at", -1).limit(500))
 
        # Statistik global
        user_doc = get_current_user()
        uid = str(user_doc["_id"]) if user_doc else session.get("user_id", "")
        user_kasbon_pending = mongo.db.kasbon.count_documents({
            "user_id": uid,
            "status": "pending"})
        total_pending  = mongo.db.kasbon.count_documents({"status": "pending"})
        total_approved = mongo.db.kasbon.count_documents({"status": "approved"})
        total_rejected = mongo.db.kasbon.count_documents({"status": "rejected"})
        total_nominal  = sum(i.get("nominal", 0) for i in
                             mongo.db.kasbon.find({"status": "approved"}, {"nominal": 1}))
 
        return render_template("kasbon_list.html",
            user          = get_current_user(),
            is_admin      = True,
            items         = items,
            status_filter = status_filter or "",
            total_pending  = total_pending,
            total_approved = total_approved,
            total_rejected = total_rejected,
            total_nominal  = total_nominal,
            user_kasbon_pending = user_kasbon_pending,
        )
 
    else:
        # ── Selain VP/GML: hanya lihat kasbon MILIK SENDIRI ───────────────
        my_items = list(mongo.db.kasbon.find(
            {"user_id": uid}
        ).sort("created_at", -1).limit(100))
 
        total_saya    = len(my_items)
        pending_saya  = sum(1 for i in my_items if i.get("status") == "pending")
        approved_saya = sum(1 for i in my_items if i.get("status") == "approved")
        total_nominal = sum(i.get("nominal", 0) for i in my_items if i.get("status") == "approved")
 
        return render_template("kasbon_list.html",
            user          = get_current_user(),
            is_admin      = False,
            items         = my_items,
            status_filter = "",
            total_saya    = total_saya,
            pending_saya  = pending_saya,
            approved_saya = approved_saya,
            total_nominal = total_nominal,
        )
 
@app.route("/kasbon/saya")
@login_required
def kasbon_saya():
    """Menampilkan riwayat kasbon untuk pengguna yang sedang login."""

    uid = session["user_id"]

    my_items = list(
        mongo.db.kasbon.find({"user_id": uid}).sort("created_at", -1)
    )

    stats = {
        "total": len(my_items),
        "pending": sum(1 for k in my_items if k.get("status") == "pending"),
        "approved": sum(1 for k in my_items if k.get("status") == "approved"),
        "rejected": sum(1 for k in my_items if k.get("status") == "rejected"),
        "total_nominal": sum(
            float(k.get("nominal", 0))
            for k in my_items
            if k.get("status") == "approved"
        )
    }

    limit_info = get_kasbon_limit_info(uid)

    return render_template(
        "kasbon_saya.html",
        items=my_items,
        limit_info=limit_info,
        user=get_current_user(),
        stats=stats
    )
@app.route("/kasbon/tambah", methods=["GET", "POST"])
@login_required
def kasbon_tambah():
    if request.method == "POST":
        nominal  = request.form.get("nominal", 0)
        keterangan = request.form.get("keterangan", "").strip()
        today    = date.today()
 
        nominal_float = float(nominal)
        uid_kasbon = session["user_id"]
        LIMIT  = 500_000
        MIN    = 50_000
        WINDOW = 30

        if nominal_float < MIN or nominal_float > LIMIT:
            flash(f"Nominal harus antara Rp {MIN:,.0f} dan Rp {LIMIT:,.0f}.", "danger")
            return redirect(url_for("kasbon_tambah"))

        # ── Atomic check & insert menggunakan transaksi satu operasi ──
        cutoff = datetime.now() - timedelta(days=WINDOW)
        used_pipeline = [
            {"$match": {
                "user_id": uid_kasbon,
                "status":  {"$in": ["approved", "pending"]},
                "created_at": {"$gte": cutoff}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$nominal"}}}
        ]
        agg = list(mongo.db.kasbon.aggregate(used_pipeline))
        used_30d = agg[0]["total"] if agg else 0
        remaining = LIMIT - used_30d

        if nominal_float > remaining:
            flash(f"Kuota tidak cukup. Sisa kuota: Rp {remaining:,.0f}.", "danger")
            return redirect(url_for("kasbon_tambah"))

        mongo.db.kasbon.insert_one({
            "user_id":    uid_kasbon,
            "nama":       session.get("name") or session.get("username", "?"),
            "nominal":    nominal_float,
            "keterangan": keterangan,
            "status":     "pending",
            "bulan":      today.month,
            "tahun":      today.year,
            "created_at": datetime.now(),
            "approved_by": None,
            "approved_at": None,
        })
        flash("✅ Pengajuan kasbon berhasil. Menunggu persetujuan.", "success")
        return redirect(url_for("kasbon_list"))
 
    user_doc = get_current_user()
    uid = str(user_doc["_id"]) if user_doc else session.get("user_id", "")
    user_kasbon_pending = mongo.db.kasbon.count_documents({
    "user_id": uid,
    "status": "pending"
})
    return render_template("kasbon_form.html",
    user                = user_doc,
    today               = date.today(),
    user_kasbon_pending = user_kasbon_pending,
    )
 
 
@app.route("/kasbon/approve/<kasbon_id>", methods=["POST"])
@login_required
@role_required("VP", "GML")
def kasbon_approve(kasbon_id):
    action = request.form.get("action", "approve")
    status = "approved" if action == "approve" else "rejected"
    mongo.db.kasbon.update_one(
        {"_id": ObjectId(kasbon_id)},
        {"$set": {
            "status":      status,
            "approved_by": session.get("name") or session.get("username", "?"),
            "approved_at": datetime.now(),
        }}
    )
    flash(f"Kasbon {status}.", "success")
    return redirect(url_for("kasbon_list"))
 

# ─── Absensi ──────────────────────────────────────────────────────────────────
@app.route("/absensi")
@login_required
def absensi_list():
    role   = session.get("role")
    area   = session.get("area")
    wok_id = session.get("wok_id")
    gml_id = session.get("gml_id")
    uid    = session.get("user_id")

    # Scope filter berdasarkan role
    if role == "VP":
        flt = {}  # VP lihat semua
    elif role == "GML":
        flt = {"gml_id": gml_id} if gml_id else {}
    elif role == "MANAGER_WOK":
        flt = {"wok_id": wok_id} if wok_id else {"area": area}
    elif role in ("TS", "TC"):
        flt = {"area": area}
    elif role == "TL":
        flt = {"tl_id": uid}
    else:
        # SF dan role lain: redirect ke riwayat pribadi
        return redirect(url_for("absensi_history"))

    date_from   = request.args.get("date_from", "")
    date_to     = request.args.get("date_to", "")
    search      = request.args.get("search", "")
    area_filter = request.args.get("area", "")
    query       = dict(flt)

    if date_from and date_to:
        query["tanggal"] = {"$gte": date_from, "$lte": date_to}
    elif date_from:
        query["tanggal"] = {"$gte": date_from}
    elif date_to:
        query["tanggal"] = {"$lte": date_to}
    if search:
        query["nama_karyawan"] = {"$regex": search, "$options": "i"}

    # Filter area tambahan — hanya VP/GML/MANAGER_WOK,ALL boleh
    if area_filter:
        if role in ("VP", "GML", "MANAGER_WOK","ALL"):
            query["area"] = area_filter
        else:
            flash("Anda tidak bisa melihat area lain.", "danger")
            return redirect(url_for("absensi_list"))

    absensi_hari = list(mongo.db.absensi.find(query).sort("tanggal", -1))

    # Daftar area untuk dropdown filter
    area_list = []
    if role in ("VP", "GML", "MANAGER_WOK"):
        distinct_areas = mongo.db.absensi.distinct("area", flt)
        area_list = sorted([a for a in distinct_areas if a is not None])

    # Rekap per area
    area_summary = {}
    if role in ("VP"):
        for a in absensi_hari:
            ar = a.get("area", "—")
            if ar not in area_summary:
                area_summary[ar] = {"total": 0, "hadir": 0, "izin": 0, "sakit": 0, "alpha": 0}
            area_summary[ar]["total"] += 1
            status = a.get("status", "")
            if status in area_summary[ar]:
                area_summary[ar][status] += 1

    wilayah_info = {
        "role":   role,
        "area":   area or "—",
        "wok_id": wok_id or "—",
        "gml_id": gml_id or "—",
    }

    return render_template("absensi.html",
        user=get_current_user(),
        absensi_hari=absensi_hari,
        date_from=date_from, date_to=date_to,
        search=search, area_list=area_list,
        area_filter=area_filter,
        area_summary=area_summary,
        wilayah_info=wilayah_info)
@app.route("/absensi/tambah", methods=["GET", "POST"])
@login_required
def absensi_tambah():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sesi tidak valid.", "danger")
        return redirect(url_for("login"))

    nama, nik, area, gml_id, wok_id, tl_id = get_user_detail(user_id)
    if not nama:
        flash("Data profil tidak lengkap.", "danger")
        return redirect(url_for("dashboard"))

    today_str = get_current_time_wib().strftime("%Y-%m-%d")
    now = get_current_time_wib()

    # Cek existing record
    existing = mongo.db.absensi.find_one({"user_id": user_id, "tanggal": today_str})

    # Tentukan status tombol
    tampil_checkin = False
    tampil_checkout = False
    izin_sakit_enabled = False
    pesan_warning = None

    if existing:
        status = existing.get("status")
        jam_masuk = existing.get("jam_masuk")
        jam_keluar = existing.get("jam_keluar")
        
        # Check-in: jika belum ada jam_masuk dan status bukan izin/sakit
        if not jam_masuk and status not in ["izin", "sakit"]:
            tampil_checkin = True   # Bisa check-in kapan saja
        
        # Check-out: hanya jika sudah check-in, jam_keluar masih kosong, dan waktu antara 17:00-18:30
        if jam_masuk and not jam_keluar:
            if is_time_between(17, 0, 18, 30, now):
                tampil_checkout = True
            else:
                pesan_warning = "⏰ Check-out hanya bisa dilakukan pukul 17:00 - 18:30"
        
        # Izin/sakit: jika belum ada status apapun dan di jam 08:00-10:00
        if not existing.get("status") and is_time_between(8, 0, 10, 0, now):
            izin_sakit_enabled = True
    else:
        # Belum ada record hari ini
        # Cek alpha otomatis jika sudah lewat 18:30
        if now > now.replace(hour=18, minute=30):
            alpha_data = {
                "user_id": user_id,
                "nama_karyawan": nama,
                "nik": nik,
                "tanggal": today_str,
                "status": "alpha",
                "keterangan": "Otomatis alpha karena tidak ada aktivitas hingga pukul 18:30",
                "area": area,
                "gml_id": gml_id,
                "wok_id": wok_id,
                "tl_id": tl_id,
                "created_at": now,
                "updated_at": now
            }
            mongo.db.absensi.insert_one(alpha_data)
            flash("❌ Tidak melakukan absensi hari ini. Status ALPHA.", "danger")
            return redirect(url_for("absensi_tambah"))
        
        # Tersedia check-in (selalu)
        tampil_checkin = True
        if is_time_between(8, 0, 10, 0, now):
            izin_sakit_enabled = True

    # --- HANDLE POST ---
    if request.method == "POST":
        aksi = request.form.get("aksi")
        if not aksi:
            flash("Aksi tidak dikenali.", "danger")
            return redirect(url_for("absensi_tambah"))

        # Pastikan record kosong ada
        if not existing:
            empty_record = {
                "user_id": user_id,
                "nama_karyawan": nama,
                "nik": nik,
                "tanggal": today_str,
                "area": area,
                "gml_id": gml_id,
                "wok_id": wok_id,
                "tl_id": tl_id,
                "status": None,
                "jam_masuk": None,
                "jam_keluar": None,
                "keterangan": None,
                "keterangan_checkout": None,
                "surat_dikirim": False,
                "no_surat": None,
                "created_at": now,
                "updated_at": now
            }
            mongo.db.absensi.insert_one(empty_record)
            existing = mongo.db.absensi.find_one({"user_id": user_id, "tanggal": today_str})

        # --- CHECK-IN (bebas waktu) ---
        if aksi == "checkin":
            if existing.get("jam_masuk"):
                flash("Anda sudah check-in hari ini.", "warning")
                return redirect(url_for("absensi_tambah"))
            
            jam_masuk_str = now.strftime("%H:%M:%S")
            mongo.db.absensi.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "jam_masuk": jam_masuk_str,
                    "status": "hadir",
                    "updated_at": now
                }}
            )
            flash("✅ Check-in berhasil dicatat.", "success")
            return redirect(url_for("absensi_tambah"))

        # --- CHECK-OUT (wajib di jam 17:00-18:30 + keterangan) ---
        elif aksi == "checkout":
            if not existing.get("jam_masuk"):
                flash("❌ Anda belum check-in, tidak bisa check-out.", "danger")
                return redirect(url_for("absensi_tambah"))
            if existing.get("jam_keluar"):
                flash("Anda sudah check-out.", "warning")
                return redirect(url_for("absensi_tambah"))
            
            # Validasi jam
            if not is_time_between(17, 0, 18, 30, now):
                flash("❌ Check-out hanya dapat dilakukan antara pukul 17:00 - 18:30.", "danger")
                return redirect(url_for("absensi_tambah"))
            
            keterangan_checkout = request.form.get("keterangan_checkout", "").strip()
            if not keterangan_checkout:
                flash("⚠️ Keterangan check-out wajib diisi (contoh: ringkasan pekerjaan).", "danger")
                return redirect(url_for("absensi_tambah"))
            
            jam_keluar_str = now.strftime("%H:%M:%S")
            mongo.db.absensi.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "jam_keluar": jam_keluar_str,
                    "keterangan_checkout": keterangan_checkout,
                    "updated_at": now
                }}
            )
            flash("✅ Check-out berhasil. Terima kasih.", "success")
            return redirect(url_for("absensi_tambah"))

        # --- IZIN ---
        elif aksi == "izin":
            if not izin_sakit_enabled:
                flash("❌ Izin hanya dapat diajukan pukul 08:00-10:00.", "danger")
                return redirect(url_for("absensi_tambah"))
            if existing.get("status"):
                flash("Status sudah ada untuk hari ini.", "warning")
                return redirect(url_for("absensi_tambah"))
            keterangan = request.form.get("keterangan", "").strip()
            if not keterangan:
                flash("Keterangan izin wajib diisi.", "danger")
                return redirect(url_for("absensi_tambah"))
            mongo.db.absensi.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "status": "izin",
                    "keterangan": keterangan,
                    "updated_at": now
                }}
            )
            flash("📋 Izin telah dicatat.", "success")
            return redirect(url_for("absensi_tambah"))

        # --- SAKIT ---
        elif aksi == "sakit":
            if not izin_sakit_enabled:
                flash("❌ Sakit hanya dapat diajukan pukul 08:00-10:00.", "danger")
                return redirect(url_for("absensi_tambah"))
            if existing.get("status"):
                flash("Status sudah ada untuk hari ini.", "warning")
                return redirect(url_for("absensi_tambah"))
            keterangan = request.form.get("keterangan", "").strip()
            no_surat = request.form.get("no_surat", "").strip()
            if not keterangan:
                flash("Keterangan sakit wajib diisi.", "danger")
                return redirect(url_for("absensi_tambah"))
            update_data = {
                "status": "sakit",
                "keterangan": keterangan,
                "surat_dikirim": True if no_surat else False,
                "no_surat": no_surat if no_surat else None,
                "updated_at": now
            }
            mongo.db.absensi.update_one({"_id": existing["_id"]}, {"$set": update_data})
            flash("🏥 Sakit telah dicatat.", "success")
            return redirect(url_for("absensi_tambah"))

        else:
            flash("Aksi tidak valid.", "danger")

    # Render template
    record = mongo.db.absensi.find_one({"user_id": user_id, "tanggal": today_str})
    return render_template("absensi_tambah.html",
                           record=record,
                           today=today_str,
                           tampil_checkin=tampil_checkin,
                           tampil_checkout=tampil_checkout,
                           izin_sakit_enabled=izin_sakit_enabled,
                           pesan_warning=pesan_warning)


@app.route('/absensi/kirim-surat', methods=['POST'])
@login_required
def kirim_surat():
    """Simpan nomor surat keterangan (izin/sakit) untuk tanggal tertentu."""
    user_id  = session["user_id"]
    tanggal  = request.form.get("tanggal", "").strip()
    no_surat = request.form.get("no_surat", "").strip()

    if not tanggal or not no_surat:
        flash("Nomor surat wajib diisi.", "danger")
        return redirect(url_for("absensi_tambah"))

    record = mongo.db.absensi.find_one({"user_id": user_id, "tanggal": tanggal})
    if not record:
        flash("Data absensi untuk tanggal tersebut tidak ditemukan.", "danger")
        return redirect(url_for("absensi_tambah"))

    if record.get("status") not in ("izin", "sakit"):
        flash("Surat hanya berlaku untuk status izin/sakit.", "danger")
        return redirect(url_for("absensi_tambah"))

    # Tandai terlambat jika dikirim bukan di hari yang sama
    try:
        terlambat = date.today().strftime("%Y-%m-%d") != tanggal
    except Exception:
        terlambat = False

    mongo.db.absensi.update_one(
        {"_id": record["_id"]},
        {"$set": {
            "surat_dikirim": True,
            "no_surat": no_surat[:100],
            "terlambat": terlambat,
            "updated_at": get_current_time_wib(),
        }}
    )
    flash("📄 Nomor surat berhasil disimpan.", "success")
    return redirect(url_for("absensi_tambah"))


@app.route('/absensi/tambah/excel', methods=['GET', 'POST'])
@login_required
@role_required("VP", "GML")
def upload_excel():
    """Upload Excel untuk data absensi massal — hanya VP/GML."""
    ALLOWED_TABLES = {
        "absensi": mongo.db.absensi,
        "kasbon":  mongo.db.kasbon,
        "users":   mongo.db.users,
    }

    if request.method == 'POST':
        file = request.files.get('file')
        table = request.form.get('table', '').strip().lower()

        if not file or not table:
            flash("File dan nama tabel wajib diisi.", "danger")
            return redirect(url_for("upload_excel"))

        if table not in ALLOWED_TABLES:
            flash(f"Tabel '{table}' tidak diizinkan.", "danger")
            return redirect(url_for("upload_excel"))

        # Validasi ekstensi file
        filename = file.filename or ""
        if not filename.lower().endswith(('.xlsx', '.xls')):
            flash("File harus berformat .xlsx atau .xls", "danger")
            return redirect(url_for("upload_excel"))

        try:
            df = pd.read_excel(file)
            data = df.to_dict(orient="records")
            col = ALLOWED_TABLES[table]
            if data:
                col.insert_many(data)
                flash(f"✅ {len(data)} baris berhasil diupload ke tabel '{table}'.", "success")
            else:
                flash("File kosong atau tidak ada data.", "warning")
        except Exception as e:
            flash(f"Gagal memproses file: {str(e)}", "danger")

        return redirect(url_for("upload_excel"))

    return render_template("excel.html", user=get_current_user())
"""
@app.route("/absensi/edit/<id>", methods=["GET","POST"])
@login_required
def absensi_edit(id):
    absensi = mongo.db.absensi.find_one_or_404({"_id": ObjectId(id)})
    if request.method == "POST":
        mongo.db.absensi.update_one({"_id": ObjectId(id)}, {"$set": {
            "nama_karyawan": request.form["nama_karyawan"],
            "nik":           request.form["nik"],
            "tanggal":       request.form["tanggal"],
            "jam_masuk":     request.form.get("jam_masuk",""),
            "jam_keluar":    request.form.get("jam_keluar",""),
            "status":        request.form["status"],
            "keterangan":    request.form.get("keterangan",""),
            "updated_at":    datetime.now(),
        }})
        flash("Data absensi diperbarui.", "success")
        return redirect(url_for("absensi_list"))
    return render_template("absensi_tambah.html", absensi=absensi)
"""

@app.route("/absensi/history")
@login_required
def absensi_history():
    role     = session.get("role", "").lower()
    user_id  = session.get("user_id")
    area     = session.get("area", "")

    # Filter dari query string
    tgl_dari = request.args.get("dari", "")
    tgl_sampai = request.args.get("sampai", "")
    filter_status = request.args.get("status", "")
    filter_user = request.args.get("user_id", "")   # hanya untuk admin/vp
    page = int(request.args.get("page", 1))
    per_page = 20

    # ── Build query berdasarkan role ──────────────────────────
    query = {}

    if role in ["vp", "admin", "gml"]:
        # Lihat semua — filter opsional per user
        if filter_user:
            query["user_id"] = filter_user

    elif role in ["manager_wok", "manager"]:
        # Lihat semua di area mereka
        query["area"] = area

    else:
        # TL, TS, TC — hanya milik sendiri
        query["user_id"] = user_id

    # Filter tanggal
    if tgl_dari or tgl_sampai:
        query["tanggal"] = {}
        if tgl_dari:
            query["tanggal"]["$gte"] = tgl_dari
        if tgl_sampai:
            query["tanggal"]["$lte"] = tgl_sampai

    # Filter status
    if filter_status:
        query["status"] = filter_status

    # ── Pagination ────────────────────────────────────────────
    total  = mongo.db.absensi.count_documents(query)
    skip   = (page - 1) * per_page
    data   = list(
        mongo.db.absensi.find(query)
        .sort("tanggal", -1)
        .skip(skip)
        .limit(per_page)
    )
    total_pages = (total + per_page - 1) // per_page

    # ── Data dropdown user (hanya untuk vp/admin/gml) ─────────
    all_users = []
    if role in ["vp", "admin", "gml"]:
        all_users = list(mongo.db.users.find(
            {}, {"_id": 1, "nama": 1, "username": 1, "jabatan": 1}
        ))

    # ── Ringkasan status ──────────────────────────────────────
    summary = {
        "hadir" : mongo.db.absensi.count_documents({**query, "status": "hadir"}),
        "absen" : mongo.db.absensi.count_documents({**query, "status": "absen"}),
        "izin"  : mongo.db.absensi.count_documents({**query, "status": "izin"}),
        "sakit" : mongo.db.absensi.count_documents({**query, "status": "sakit"}),
    }

    is_admin_view = role in ["vp", "admin", "gml", "manager_wok", "manager"]

    return render_template("absensi_saya.html",
        data         = data,
        summary      = summary,
        total        = total,
        page         = page,
        total_pages  = total_pages,
        all_users    = all_users,
        is_admin_view= is_admin_view,
        filter_dari  = tgl_dari,
        filter_sampai= tgl_sampai,
        filter_status= filter_status,
        filter_user  = filter_user,
        role         = role,
    )
@app.route("/absensi/hapus/<id>")
@login_required
@role_required("VP","GML","MANAGER_WOK")
def absensi_hapus(id):
    mongo.db.absensi.delete_one({"_id": ObjectId(id)})
    flash("Data absensi dihapus.", "danger")
    return redirect(url_for("absensi_list"))
# ══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/users")
@login_required
@role_required("VP", "GML")
def user_list():
    # Ambil parameter filter
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()
    wok_filter = request.args.get("wok", "").strip()

    # Bangun query MongoDB
    query = {}
    if search:
        query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"nama": {"$regex": search, "$options": "i"}}
        ]
    if role_filter:
        query["role"] = role_filter
    if wok_filter:
        query["wok"] = wok_filter

    users = list(mongo.db.users.find(query, {"password": 0}).sort("nama", 1))

    return render_template("user_list.html",
        users=users,
        role_list=ROLE_LIST,
        wok_list=WOK_LIST,
        search=search,
        role_filter=role_filter,
        wok_filter=wok_filter,
        user=get_current_user()
    ) 
@app.route("/users/tambah", methods=["GET", "POST"])
@login_required
@role_required("VP", "GML")
def user_tambah():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        if mongo.db.users.find_one({"username": username}):
            flash("Username sudah dipakai.", "danger")
            return redirect(url_for("user_list"))
 
        raw_pw = request.form.get("password", "")
        mongo.db.users.insert_one({
            "username":   username,
            "password":   generate_password_hash(raw_pw),  # ← hash, tidak plain text
            "nama":       request.form.get("nama","").strip(),
            "role":       request.form.get("role","SF"),
            "jabatan":    request.form.get("role","SF"),
            "wok":        request.form.get("wok","JAKTIM"),
            "is_locked":  False,
            "status":     "active",  # ← ditambah VP/GML = langsung aktif
            "created_at": datetime.now(),
        })
        flash("User berhasil ditambahkan.", "success")
        return redirect(url_for("user_list"))
 
    return render_template("user_list.html",
        users=[], role_list=ROLE_LIST, wok_list=WOK_LIST,
        show_form=True, user=get_current_user())
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()
    if not user:
        flash("Sesi tidak valid.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        # Ambil data dari form
        nama     = request.form.get("nama", "").strip()
        email    = request.form.get("email", "").strip()
        nik      = request.form.get("nik", "").strip()
        area     = request.form.get("area", "").strip()
        wok      = request.form.get("wok", "").strip()
        no_hp    = request.form.get("no_hp", "").strip()
        alamat   = request.form.get("alamat", "").strip()

        # Validasi sederhana
        if not nama:
            flash("Nama lengkap wajib diisi.", "danger")
            return render_template("profile.html", user=user)

        # Update ke database
        update_data = {
            "nama": nama,
            "email": email,
            "nik": nik,
            "area": area,
            "wok": wok.upper() if wok else user.get("wok", ""),
            "no_hp": no_hp,
            "alamat": alamat,
            "updated_at": datetime.now()
        }
        # Jangan ubah field kunci seperti username, role, password
        mongo.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )
        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("profile"))

    # GET: tampilkan form dengan data existing
    return render_template("profile.html", user=user)

 # ============================================================
# USER MANAGEMENT - EDIT ROLE & LOCK/UNLOCK
# ============================================================
@csrf.exempt
@app.route("/user/update-role/<user_id>", methods=["POST"])
@login_required
@role_required("VP")
def user_update_role(user_id):
    try:
        # Cek apakah request berupa JSON
        if request.is_json:
            data = request.get_json()
            new_role = data.get("role", "").strip()
        else:
            new_role = request.form.get("role", "").strip()
        
        if not new_role or new_role not in ROLE_LIST:
            return jsonify({"success": False, "message": "Role tidak valid."}), 400

        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": new_role, "jabatan": new_role}}
        )
        if result.modified_count:
            return jsonify({"success": True, "message": f"Role berhasil diubah menjadi {new_role}."})
        else:
            return jsonify({"success": False, "message": "Tidak ada perubahan atau user tidak ditemukan."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@csrf.exempt
@app.route("/user/toggle-lock/<user_id>", methods=["POST"])
@login_required
@role_required("VP")
def user_toggle_lock(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"success": False, "message": "User tidak ditemukan."}), 404

        if str(user["_id"]) == session.get("user_id"):
            return jsonify({"success": False, "message": "Anda tidak dapat mengunci akun sendiri."}), 403

        current_status = user.get("is_locked", False)
        new_status = not current_status
        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_locked": new_status}}
        )
        status_text = "dikunci" if new_status else "dibuka"
        return jsonify({"success": True, "message": f"Akun user {user.get('username')} berhasil {status_text}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ══════════════════════════════════════════════════════════════════════════════
# AKTIVASI AKUN PENDING (oleh VP/GML)
# ══════════════════════════════════════════════════════════════════════════════
@csrf.exempt
@app.route("/user/activate/<user_id>", methods=["POST"])
@login_required
@role_required("VP", "GML")
def user_activate(user_id):
    """Aktivasi akun karyawan yang baru registrasi mandiri (status: pending)."""
    try:
        data = request.get_json(silent=True) or {}
        new_role = data.get("role", "SF").strip()
        if new_role not in ROLE_LIST:
            new_role = "SF"

        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"success": False, "message": "User tidak ditemukan."}), 404

        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status":     "active",
                "role":       new_role,
                "jabatan":    new_role,
                "activated_by": session.get("name") or session.get("username", "?"),
                "activated_at": datetime.now()
            }}
        )
        return jsonify({"success": True, "message": f"Akun {user.get('nama')} berhasil diaktivasi sebagai {new_role}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/users/pending")
@login_required
@role_required("VP", "GML")
def user_pending_list():
    """Daftar akun pending yang menunggu aktivasi."""
    pending_users = list(mongo.db.users.find(
        {"status": "pending"},
        {"password": 0}
    ).sort("created_at", -1))
    return render_template("user_list.html",
        users=pending_users,
        role_list=ROLE_LIST,
        wok_list=WOK_LIST,
        search="",
        role_filter="",
        wok_filter="",
        show_pending=True,
        user=get_current_user()
    )

# ══════════════════════════════════════════════════════════════════════════════
# KPI — HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
 
def get_kpi_data_for_month(month, year, wok):
    filt = {"month": month, "year": year, "wok": wok}
    days = calendar.monthrange(year, month)[1]

    # ========== 1. AMBIL DATA DARI KOLEKSI ==========
    ps_docs = list(mongo.db.kpi_ps.find(filt, {"_id": 0}))
    djp_docs = list(mongo.db.kpi_djp.find(filt, {"_id": 0}))
    db_docs = list(mongo.db.kpi_database.find(filt, {"_id": 0}))   # ← selalu list, bisa kosong

    # ========== 2. METADATA UPLOAD ==========
    upload_info = mongo.db.kpi_uploads.find_one(filt, {"_id": 0})
    absensi_mb_count = upload_info.get("absensi_mb_count", 0) if upload_info else 0
    kpi_tl_count = upload_info.get("kpi_tl_count", 0) if upload_info else 0
    orbit_count = upload_info.get("orbit_count", 0) if upload_info else 0
    upsell_count = upload_info.get("upsell_count", 0) if upload_info else 0

    # ========== 3. PS – TOTAL & HARIAN ==========
    total_ps = len(ps_docs)
    total_arpu = sum(d.get("arpu", 0) for d in ps_docs)
    avg_arpu = round(total_arpu / total_ps, 0) if total_ps else 0

    ps_per_day = [0] * (days + 1)
    for d in ps_docs:
        t = int(d.get("tgl_ps") or 0)
        if 1 <= t <= days:
            ps_per_day[t] += 1

    # PS per TL
    tl_ps = {}
    for d in ps_docs:
        k = d.get("nama_tl", "—") or "—"
        tl_ps[k] = tl_ps.get(k, 0) + 1
    tl_ps_sorted = sorted(tl_ps.items(), key=lambda x: x[1], reverse=True)

    # Top SF
    sf_ps = {}
    for d in ps_docs:
        k = d.get("nama_sf", "—") or "—"
        sf_ps[k] = sf_ps.get(k, 0) + 1
    top_sf = sorted(sf_ps.items(), key=lambda x: x[1], reverse=True)[:15]

    # Distribusi paket & kategori
    paket_dist = {}
    for d in ps_docs:
        p = (d.get("paket") or "Lainnya")[:40]
        paket_dist[p] = paket_dist.get(p, 0) + 1
    kat_dist = {}
    for d in ps_docs:
        k = d.get("kategori") or "Lainnya"
        kat_dist[k] = kat_dist.get(k, 0) + 1

    # ========== 4. DJP – APPROVED & HARIAN ==========
    djp_approved = [d for d in djp_docs if d.get("status") == "APPROVED"]
    total_djp = len([d for d in djp_approved if d.get("category") == "DJP"])
    briefing_mb_count = upload_info.get("briefing_mb_count", 0) if upload_info else 0
    total_briefing = briefing_mb_count   # menggantikan perhitungan dari DJP

    djp_per_day = [0] * (days + 1)
    brief_per_day = [0] * (days + 1)
    for d in djp_approved:
        t = int(d.get("tgl") or 0)
        if 1 <= t <= days:
            if d.get("category") == "DJP":
                djp_per_day[t] += 1
            else:
                brief_per_day[t] += 1

    # DJP per TL (hitung dari supervisor_name)
    tl_djp = {}
    for d in djp_approved:
        if d.get("category") == "DJP":
            k = d.get("supervisor_name", "—") or "—"
            tl_djp[k] = tl_djp.get(k, 0) + 1
    tl_djp_sorted = sorted(tl_djp.items(), key=lambda x: x[1], reverse=True)
    total_briefing = len([d for d in djp_approved if d.get("category") == "BRIEFING"])
    
    # ========== 5. SF (DATABASE) – AKTIF / NONAKTIF ==========
    sf_active = len([d for d in db_docs if d.get("status_sf") == "ACTIVE"])
    sf_nonakt = len([d for d in db_docs if d.get("status_sf") in ("DELETED","IN ACTIVE")])
    sf_total = len(db_docs)

    # ========== 6. DAFTAR SF AKTIF & NON-AKTIF (untuk popup) ==========
    sf_aktif_list = []
    sf_nonaktif_list = []
    for d in db_docs:
        status = d.get("status_sf", "").upper()
        item = {
            "nama_sf": d.get("nama_sf", "?"),
            "kode_sf": d.get("kode_sf", "?"),
            "status_sf": d.get("status_sf", "?"),
            "nama_tl": d.get("nama_tl", "?") or d.get("team_leader", "?"),
            "kode_tl": d.get("kode_tl", "?"),
        }
        if status in ["ACTIVE", "AKTIF"]:
            sf_aktif_list.append(item)
        else:
            sf_nonaktif_list.append(item)

    # ========== 7. DETAIL TEAM LEADER (dari PS + DJP + SF) ==========
    tl_names = set()
    for d in ps_docs:
        tl = d.get("nama_tl")
        if tl:
            tl_names.add(tl)

    # Hitung PS per TL
    ps_per_tl = {}
    for d in ps_docs:
        tl = d.get("nama_tl")
        if tl:
            ps_per_tl[tl] = ps_per_tl.get(tl, 0) + 1

    # Hitung DJP per TL (hanya kategori DJP)
    djp_per_tl = {}
    for d in djp_approved:
        if d.get("category") == "DJP":
            tl = d.get("supervisor_name")
            if tl:
                djp_per_tl[tl] = djp_per_tl.get(tl, 0) + 1

    # Hitung jumlah SF per TL
    sf_per_tl = {}
    for d in db_docs:
        tl = d.get("nama_tl")
        if tl:
            sf_per_tl[tl] = sf_per_tl.get(tl, 0) + 1

    tl_details = []
    for tl in sorted(tl_names):
        tl_details.append({
            "nama": tl,
            "ps": ps_per_tl.get(tl, 0),
            "djp": djp_per_tl.get(tl, 0),
            "sf": sf_per_tl.get(tl, 0)
        })
    tl_details.sort(key=lambda x: x["ps"], reverse=True)

    # ========== 8. HITUNG JUMLAH TL AKTIF (BERDASARKAN PS) ==========
    total_tl_ps = len(tl_details)   # ini akan menghasilkan angka 5 (atau sesuai data PS)

    # ========== 9. TABEL HARIAN UNTUK MODAL ==========
    labels = [str(d) for d in range(1, days + 1)]
    ps_harian_table = []
    djp_harian_table = []
    for i in range(days):
        tgl = i + 1
        ps_val = ps_per_day[tgl]
        if ps_val > 0:
            ps_harian_table.append({"tanggal": tgl, "ps": ps_val})
        djp_val = djp_per_day[tgl] if tgl < len(djp_per_day) else 0
        brief_val = brief_per_day[tgl] if tgl < len(brief_per_day) else 0
        if djp_val > 0 or brief_val > 0:
            djp_harian_table.append({"tanggal": tgl, "djp": djp_val, "briefing": brief_val})

    # ========== 10. RETURN ==========
    return {
        "bulan_label": BULAN_NAMA[month - 1],
        "year": year, "month": month, "wok": wok,
        "last_update": upload_info.get("last_update", "—") if upload_info else "—",
        "months_list": MONTHS_LIST,
        "wok_list": WOK_LIST,
        "total_ps": total_ps,
        "total_arpu": int(total_arpu),
        "avg_arpu": int(avg_arpu),
        "total_djp": total_djp,
        "total_briefing": total_briefing,
        "sf_aktif": sf_active,
        "sf_nonaktif": sf_nonakt,
        "sf_total": sf_total,
        "total_tl": total_tl_ps,                  # ← sekarang pakai total_tl_ps (5)
        "ps_harian_labels": labels,
        "ps_harian_values": ps_per_day[1:days + 1],
        "djp_harian_labels": labels,
        "djp_harian_values": djp_per_day[1:days + 1],
        "brief_harian_values": brief_per_day[1:days + 1],
        "tl_ps_labels": [x[0] for x in tl_ps_sorted],
        "tl_ps_values": [x[1] for x in tl_ps_sorted],
        "tl_djp_labels": [x[0] for x in tl_djp_sorted],
        "tl_djp_values": [x[1] for x in tl_djp_sorted],
        "top_sf_labels": [x[0] for x in top_sf],
        "top_sf_values": [x[1] for x in top_sf],
        "paket_labels": list(paket_dist.keys()),
        "paket_values": list(paket_dist.values()),
        "kat_labels": list(kat_dist.keys()),
        "kat_values": list(kat_dist.values()),
        "uploaded_by": upload_info.get("uploaded_by", "—") if upload_info else "—",
        "upload_at": upload_info.get("upload_at", "—") if upload_info else "—",
        "is_locked": upload_info is not None,
        "ps_harian_table": ps_harian_table,
        "djp_harian_table": djp_harian_table,
        "absensi_mb_count": absensi_mb_count,
        "kpi_tl_count": kpi_tl_count,
        "orbit_count": orbit_count,
        "upsell_count": upsell_count,
        "sf_aktif_list": sf_aktif_list,
        "sf_nonaktif_list": sf_nonaktif_list,
        "tl_details": tl_details,
        "total_tl_ps": total_tl_ps,              # ← tambahkan untuk stat card baru
    } 
 
def _empty_kpi_data(month, year, wok):
    days   = calendar.monthrange(year, month)[1]
    labels = [str(d) for d in range(1, days + 1)]
    zeros  = [0] * days
    return {
        "bulan_label": BULAN_NAMA[month - 1],
        "year": year, "month": month, "wok": wok,
        "last_update": "—", "months_list": MONTHS_LIST, "wok_list": WOK_LIST,
        "flash_msg": "", "flash_type": "",
        "total_ps": 0, "total_arpu": 0, "avg_arpu": 0,
        "total_djp": 0, "total_briefing": 0,
        "sf_aktif": 0, "sf_nonaktif": 0, "sf_total": 0, "total_tl": 0,
        "ps_harian_labels": labels,    "ps_harian_values": zeros,
        "djp_harian_labels": labels,   "djp_harian_values": zeros,
        "brief_harian_values": zeros,
        "tl_ps_labels": [],  "tl_ps_values": [],
        "tl_djp_labels": [], "tl_djp_values": [],
        "top_sf_labels": [], "top_sf_values": [],
        "paket_labels": [],  "paket_values": [],
        "kat_labels": [],    "kat_values": [],
        "ps_harian_table": [],          # <-- TAMBAHKAN
        "djp_harian_table": [],         # <-- TAMBAHKAN
        "uploaded_by": "—", "upload_at": "—", "is_locked": False,
        "absensi_mb_count": 0,
        "kpi_tl_count": 0,
        "orbit_count": 0,
        "upsell_count": 0,
        "sf_nonaktif_list":[],"total_tl": 0,
        "total_tl_ps": 0,
        "tl_details": [],
        "sf_aktif_list": [],
        "sf_nonaktif_list": [],
        
    }
 
@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    user = get_current_user()
    if request.method == "POST":
        old = request.form.get("old_password")
        new = request.form.get("new_password")
        confirm = request.form.get("confirm_password")

        if not check_password_hash(user.get("password", ""), old):
            flash("Password lama salah.", "danger")
            return redirect(url_for("change_password"))

        if len(new) < 8:
            flash("Password baru minimal 8 karakter.", "danger")
            return redirect(url_for("change_password"))

        if new != confirm:
            flash("Konfirmasi password tidak cocok.", "danger")
            return redirect(url_for("change_password"))

        hashed = generate_password_hash(new)
        mongo.db.users.update_one({"_id": user["_id"]}, {"$set": {"password": hashed}})
        flash("Password berhasil diubah. Silakan login kembali.", "success")
        session.clear()
        return redirect(url_for("login"))

    return render_template("change_password.html")
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# KPI ROUTES  (direct @app.route — no Blueprint)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/kpi")
@app.route("/kpi/dashboard")
@login_required
@role_required('VP','GML')
def kpi():
    today = date.today()
    month = int(request.args.get("month", today.month))
    year  = int(request.args.get("year",  today.year))
    wok   = request.args.get("wok", session.get("wok", "JAKTIM") or "JAKTIM").upper()

    has_data = mongo.db.kpi_ps.count_documents({"month": month, "year": year, "wok": wok}) > 0

    if has_data:
        ctx = get_kpi_data_for_month(month, year, wok)
    else:
        ctx = _empty_kpi_data(month, year, wok)

    return render_template("kpi.html",
        user = get_current_user(),
        **ctx,
    )
# /debug-templates dihapus — tidak boleh ada di production
@app.route("/kpi/upload", methods=["GET", "POST"])
@login_required
@role_required("VP", "GML", "MANAGER_WOK")
def kpi_upload():
    if request.method == "POST":
        month = int(request.form.get("month"))
        year = int(request.form.get("year"))
        wok = request.form.get("wok").upper()
        f = request.files.get("file")
        if not f:
            return jsonify({"success": False, "message": "File tidak ditemukan"}), 400

        file_bytes = f.read()
        filename = f.filename
        task_id = str(uuid.uuid4())

        upload_progress[task_id] = {
            "status": "processing",
            "percent": 0,
            "message": "Memulai proses upload..."
        }

        # Jalankan background thread
        thread = threading.Thread(
            target=process_kpi_upload_background,
            args=(task_id, file_bytes, filename, month, year, wok,
                  session.get("name", "?"), session.get("user_id", ""))
        )
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "task_id": task_id})

    # GET: tampilkan form upload
    today = date.today()
    month = int(request.args.get("month", today.month))
    year  = int(request.args.get("year",  today.year))
    wok   = request.args.get("wok", session.get("wok", "JAKTIM") or "JAKTIM").upper()

    upload_history = list(mongo.db.kpi_uploads.find({}, {"_id": 0}).sort("upload_at_dt", -1).limit(20))

    return render_template("kpi_upload.html",
        user           = get_current_user(),
        month          = month,
        year           = year,
        wok            = wok,
        bulan_label    = BULAN_NAMA[month-1],
        months_list    = MONTHS_LIST,
        wok_list       = WOK_LIST,
        upload_history = upload_history,
    )
@app.route("/kpi/upload-progress/<task_id>")
@login_required

@role_required('VP', 'GML', 'MANAGER_WOK')
def kpi_upload_progress(task_id):
    data = upload_progress.get(task_id)
    if not data:
        return jsonify({"status": "not_found"}), 404
    return jsonify(data)

@app.route("/kpi/unlock", methods=["POST"])
@login_required
@role_required("VP", "GML")
def kpi_unlock():
    data  = request.get_json(silent=True) or {}
    month = int(data.get("month", 0))
    year  = int(data.get("year",  0))
    wok   = str(data.get("wok",  "")).upper()
    if not (month and year and wok):
        return jsonify({"success": False, "message": "Parameter tidak lengkap."})
    filt = {"month": month, "year": year, "wok": wok}
    mongo.db.kpi_uploads.delete_one(filt)
    mongo.db.kpi_ps.delete_many(filt)
    mongo.db.kpi_djp.delete_many(filt)
    mongo.db.kpi_database.delete_many(filt)
    mongo.db.kpi_excel_data.delete_many(filt)
    return jsonify({"success": True, "message": "Data berhasil dihapus dan kunci dibuka."})

@app.route("/kpi/data")
@login_required
@role_required('VP','GML')
def kpi_data():
    sheet = request.args.get("sheet", "list")
    month = int(request.args.get("month", date.today().month))
    year = int(request.args.get("year", date.today().year))
    wok = request.args.get("wok", session.get("wok", "JAKTIM")).upper()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(200, int(request.args.get("per_page", 50)))
    search = request.args.get("search", "").strip()

    if sheet == "list":
        sheets_cursor = mongo.db.kpi_excel_data.find(
            {"month": month, "year": year, "wok": wok},
            {"_id": 0, "sheet_name": 1, "total_rows": 1, "total_cols": 1}
        ).sort("sheet_name", 1)
        sheets = list(sheets_cursor)
        return render_template("kpi_data_list.html",
            user=get_current_user(),
            month=month, year=year, wok=wok,
            sheets=sheets,
            months_list=MONTHS_LIST,
            wok_list=WOK_LIST,
            bulan_label=BULAN_NAMA[month-1]
        )

    doc = mongo.db.kpi_excel_data.find_one({"month": month, "year": year, "wok": wok, "sheet_name": sheet})
    if not doc:
        flash(f"Sheet '{sheet}' tidak ditemukan untuk periode {BULAN_NAMA[month-1]} {year} - {wok}", "danger")
        return redirect(url_for("kpi_data", month=month, year=year, wok=wok))

    headers = doc.get("headers", [])
    all_rows = doc.get("data", [])

    if search:
        filtered_rows = []
        for row in all_rows:
            if any(search.lower() in str(cell).lower() for cell in row):
                filtered_rows.append(row)
        rows = filtered_rows
        total = len(rows)
    else:
        rows = all_rows
        total = len(rows)

    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    page_rows = rows[start:start+per_page]

    return render_template("kpi_data_sheet.html",
        user=get_current_user(),
        sheet=sheet,
        month=month, year=year, wok=wok,
        headers=headers,
        rows=page_rows,
        page=page, pages=pages, total=total,
        per_page=per_page,
        search=search,
        months_list=MONTHS_LIST,
        wok_list=WOK_LIST,
        bulan_label=BULAN_NAMA[month-1]
    )

# ── Notifications routes (missing from original) ───────────────────────────
@app.route("/notifikasi")
@login_required
def notifications_list():
    uid  = session["user_id"]
    page = max(1, int(request.args.get("page", 1)))
    per  = 20
    skip = (page - 1) * per

    q = {"$or": [{"target_ids": uid}, {"target_all": True}]}
    total = mongo.db.notifications.count_documents(q)
    pages = max(1, (total + per - 1) // per)

    raw = list(
        mongo.db.notifications.find(q)
            .sort("created_at", -1)
            .skip(skip)
            .limit(per)
    )

    # Mark as read
    notif_ids = [n["_id"] for n in raw]
    if notif_ids:
        mongo.db.notifications.update_many(
            {"_id": {"$in": notif_ids}, "reads.user_id": {"$ne": uid}},
            {"$push": {"reads": {"user_id": uid, "read_at": datetime.now()}}}
        )

    notifs = []
    for n in raw:
        reads  = [r.get("user_id") for r in n.get("reads", [])]
        is_read = uid in reads
        n["is_read"]  = is_read
        n["time_fmt"] = n["created_at"].strftime("%d %b %Y %H:%M") if n.get("created_at") else "—"
        n["judul"]    = n.get("title") or n.get("judul") or "(tanpa judul)"
        n["isi"]      = n.get("body")  or n.get("isi")   or ""
        n["prioritas"]= n.get("priority") or n.get("prioritas") or "normal"
        notifs.append(n)

    return render_template("notifications.html",
        user    = get_current_user(),
        notifs  = notifs,
        total   = total,
        page    = page,
        pages   = pages,
    )


@app.route("/notifikasi/kirim", methods=["GET", "POST"])
@login_required
@role_required("VP", "GML")
def notifications_send():
    if request.method == "POST":
        judul    = request.form.get("judul", "").strip()
        isi      = request.form.get("isi", "").strip()
        prioritas= request.form.get("prioritas", "normal")
        target   = request.form.get("target", "all")

        if target == "all":
            target_all  = True
            target_ids  = []
        else:
            target_all  = False
            target_ids  = request.form.getlist("target_ids")

        sender = get_current_user()
        mongo.db.notifications.insert_one({
            "title":       judul,
            "judul":       judul,
            "body":        isi,
            "isi":         isi,
            "priority":    prioritas,
            "prioritas":   prioritas,
            "from_id":     str(sender["_id"]) if sender else "",
            "from_nama":   sender.get("nama", "?") if sender else "?",
            "target_all":  target_all,
            "target_ids":  target_ids,
            "reads":       [],
            "created_at":  datetime.now(),
        })
        flash("Notifikasi berhasil dikirim.", "success")
        return redirect(url_for("notifications_list"))

    all_users = list(mongo.db.users.find({}, {"nama": 1, "role": 1}).sort("nama", 1))
    return render_template("notifications.html",
        user      = get_current_user(),
        notifs    = [],
        total     = 0,
        page      = 1,
        pages     = 1,
        show_form = True,
        all_users = all_users,
    )


# ── Internal Excel parser (single canonical version) ───────────────────────

@app.context_processor
def inject_globals():
    uid = session.get("user_id")
    msg_unread = notif_unread = 0
    if uid:
        try:
            msg_unread = mongo.db.messages.count_documents(
                {"to_id": uid, "is_read": False, "deleted_by_receiver": {"$ne": True}}
            )
            notif_unread = mongo.db.notifications.count_documents({
                "$or": [{"target_ids": uid}, {"target_all": True}],
                "reads": {"$not": {"$elemMatch": {"user_id": uid}}}
            })
        except Exception:
            pass
    return {"g_msg_unread": msg_unread, "g_notif_unread": notif_unread,"wok_list": WOK_LIST}
 
@app.route("/api/excel/data")
@login_required
def api_excel_data():
    """API untuk mendapatkan data Excel yang sudah diupload dengan pagination"""
    sheet_name = request.args.get("sheet", "")
    page = max(1, int(request.args.get("page", 1)))
    rows_per_page = min(200, max(10, int(request.args.get("rows", 50))))
    search = request.args.get("search", "").strip()
    
    # Ambil data dari MongoDB
    sheet_data = mongo.db.kpi_excel_data.find_one({"sheet_name": sheet_name})
    
    if not sheet_data:
        return jsonify({"success": False, "message": f"Sheet '{sheet_name}' tidak ditemukan"}), 404
    
    headers = sheet_data.get("headers", [])
    rows = sheet_data.get("data", [])
    
    # Filter berdasarkan search
    if search:
        filtered_rows = []
        for row in rows:
            row_str = " ".join(str(cell).lower() for cell in row)
            if search.lower() in row_str:
                filtered_rows.append(row)
        rows = filtered_rows
    else:
        filtered_rows = rows
    
    total_rows = len(filtered_rows)
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page
    
    start_idx = (page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    page_rows = filtered_rows[start_idx:end_idx]
    
    return jsonify({
        "success": True,
        "sheet_name": sheet_name,
        "headers": headers,
        "rows": page_rows,
        "page": page,
        "totalPages": total_pages,
        "totalRows": total_rows,
        "rowsPerPage": rows_per_page,
        "startRow": start_idx,
        "endRow": end_idx - 1 if end_idx > 0 else 0
    })
# ══════════════════════════════════════════════════════════════════════════════
# MONGODB INDEXES — jalankan sekali saat startup
# ══════════════════════════════════════════════════════════════════════════════
def setup_indexes():
    db = mongo.db
    # Users
    db.users.create_index("username", unique=True)
    # Kasbon
    db.kasbon.create_index([("user_id",1),("status",1)])
    db.kasbon.create_index([("bulan",1),("tahun",1)])
    # Absensi
    db.absensi.create_index([("user_id",1),("tanggal",1)], unique=True)
    db.absensi.create_index("tanggal")
    # KPI
    db.kpi_uploads.create_index([("month",1),("year",1),("wok",1)], unique=True)
    db.kpi_ps.create_index([("month",1),("year",1),("wok",1)])
    db.kpi_djp.create_index([("month",1),("year",1),("wok",1)])
    db.kpi_database.create_index([("month",1),("year",1),("wok",1)])
    # Messages
    db.messages.create_index([("to_id",1),("is_read",1)])
    db.messages.create_index([("from_id",1),("created_at",-1)])
    db.messages.create_index("starred_by")
    # Notifications
    db.notifications.create_index("target_ids")
    db.notifications.create_index("target_all")
    db.notifications.create_index([("from_id",1),("created_at",-1)])
    db.notifications.create_index("reads.user_id")
    print("✅ MongoDB indexes ready")
    # Di dalam setup_indexes(), tambahkan:
    db.password_resets.create_index("expires_at", expireAfterSeconds=3600)  # Auto-delete after 1 hour
    db.password_resets.create_index("token")
    db.password_resets.create_index("user_id")
 
 
# ── API unread counts ──────────────────────────────────────────────────────────
@app.route("/api/unread-counts")
@login_required
def api_unread_counts():
    uid = session["user_id"]
    try:
        msg_unread   = mongo.db.messages.count_documents({"to_id": uid, "is_read": False, "deleted_by_receiver": {"$ne": True}})
        notif_unread = mongo.db.notifications.count_documents({
            "$or": [{"target_ids": uid}, {"target_all": True}],
            "reads": {"$not": {"$elemMatch": {"user_id": uid}}}
        })
    except Exception:
        msg_unread = notif_unread = 0
    return jsonify({
        "messages": msg_unread,
        "notifications": notif_unread,
        # Dipertahankan untuk kompatibilitas mundur jika ada caller lain
        "msg_unread": msg_unread,
        "notif_unread": notif_unread,
    })
 
 
@app.route('/laporan/harian')
@login_required
@role_required('VP','GML')
def report_harian():
    today_str = date.today().strftime('%Y-%m-%d')

    # ── Ambil parameter filter ────────────────────────────
    # Support param lama (date) dan baru (date_from / date_to)
    date_from  = request.args.get('date_from') or request.args.get('date', today_str)
    date_to    = request.args.get('date_to',   date_from)   # default = hari yg sama
    wok_filter = request.args.get('wok',   '').strip()
    search     = request.args.get('search','').strip()

    # Normalisasi urutan kalau user iseng balik
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # ── Query absensi ─────────────────────────────────────
    q_abs = {'tanggal': {'$gte': date_from, '$lte': date_to}}
    if wok_filter:
        q_abs['area'] = wok_filter
    if search:
        q_abs['nama'] = {'$regex': search, '$options': 'i'}

    absensi_raw = list(mongo.db.absensi.find(q_abs).sort('tanggal', 1))

    # Normalisasi field untuk template
    absensi_hari = []
    for a in absensi_raw:
        a['nama_karyawan'] = a.get('nama_karyawan','?')
        a['nik']           = a.get('nik') or a.get('user_id', '')
        a['jam_masuk']     = a.get('jam_masuk',  '')
        a['jam_keluar']    = a.get('jam_keluar', '')
        a['area']          = a.get('area') or a.get('wok', '')
        absensi_hari.append(a)

    # ── Query kasbon ──────────────────────────────────────
    try:
        dt_from = datetime.strptime(date_from, '%Y-%m-%d')
        dt_to   = datetime.strptime(date_to,   '%Y-%m-%d')
        dt_to_end = datetime(dt_to.year, dt_to.month, dt_to.day, 23, 59, 59)
    except ValueError:
        dt_from = dt_to_end = datetime.now()

    q_kas = {'created_at': {'$gte': dt_from, '$lte': dt_to_end}}
    if wok_filter:
        q_kas['$or'] = [{'area': wok_filter}, {'wok': wok_filter}]
    if search:
        q_kas['nama'] = {'$regex': search, '$options': 'i'}

    kasbon_raw = list(mongo.db.kasbon.find(q_kas).sort('created_at', -1))

    kasbon_hari = []
    for k in kasbon_raw:
        tgl = k.get('created_at')
        k['nama_karyawan'] = k.get('nama_karywan') or k.get('nama')
        k['nik']           = k.get('nik') or k.get('user_id', '')
        k['jumlah']        = k.get('nominal', 0) or 0
        k['keperluan']     = k.get('keterangan', '') or k.get('keperluan', '')
        k['area']          = k.get('area') or k.get('wok', '')
        k['tanggal_str']   = tgl.strftime('%Y-%m-%d') if hasattr(tgl, 'strftime') else str(tgl or '')
        kasbon_hari.append(k)

    # ── Hitung ringkasan absensi ──────────────────────────
    abs_sum = {
        'hadir':  sum(1 for a in absensi_hari if a.get('status') == 'hadir'),
        'izin':   sum(1 for a in absensi_hari if a.get('status') == 'izin_kegiatan'),
        'sakit':  sum(1 for a in absensi_hari if a.get('status') == 'izin_sakit'),
        'alpha':  sum(1 for a in absensi_hari if a.get('status') not in
                      ['hadir', 'izin_kegiatan', 'izin_sakit']),
    }

    # ── Hitung ringkasan kasbon ───────────────────────────
    approved_statuses = {'approved', 'disetujui'}
    rejected_statuses = {'rejected', 'ditolak'}
    kas_sum = {
        'total':    len(kasbon_hari),
        'approved': sum(1 for k in kasbon_hari if k.get('status') in approved_statuses),
        'rejected': sum(1 for k in kasbon_hari if k.get('status') in rejected_statuses),
        'pending':  sum(1 for k in kasbon_hari if k.get('status') == 'pending'),
        'amount':   sum(k['jumlah'] for k in kasbon_hari
                        if k.get('status') in approved_statuses),
    }

    # ── Daftar WOK untuk dropdown ─────────────────────────
    wok_list = ['JAKTIM','JAKUT','JAKBAR','JAKSEL','JAKPUS',
                'BEKASI','DEPOK','TANGERANG']

    # ── current_user & profile (compat template lama) ─────
    _role    = session.get('role', '')
    _uid     = session.get('user_id', '')
    CurrentUser = type('U', (), {'role': _role, 'id': _uid})()
    Profile     = type('P', (), {'user_id': _uid})()

    return render_template('report.html',
        # Filter aktif
        date_from    = date_from,
        date_to      = date_to,
        wok_filter   = wok_filter,
        wok_list     = wok_list,
        search       = search,
        # Data
        absensi_hari = absensi_hari,
        kasbon_hari  = kasbon_hari,
        abs_sum      = abs_sum,
        kas_sum      = kas_sum,
        # Compat
        date         = date_from,   # supaya filter lama tidak error
        user         = get_current_user(),
        current_user = CurrentUser,
        profile      = Profile,
    )
# ═══════════════════════════════════════════════════════════════════
# KPI EXPORT ROUTES & HELPER (Tambahkan ini ke app.py)
# ═══════════════════════════════════════════════════════════════════

def get_kpi_context(month: int, year: int, wok: str) -> dict:
    """Ambil semua data KPI untuk export (sesuai koleksi di app.py)"""
    from collections import defaultdict, Counter
    import calendar

    q_base = {"month": month, "year": year, "wok": wok}

    # Meta info (koleksi kpi_uploads)
    meta = mongo.db.kpi_uploads.find_one(q_base) or {}
    is_locked   = bool(meta)
    uploaded_by = meta.get("uploaded_by", "—")
    upload_at   = meta.get("upload_at", "—")
    last_update = meta.get("last_update", "")
    version     = meta.get("version", "1.0")

    # PS sheet
    ps_docs = list(mongo.db.kpi_ps.find(q_base, {"_id": 0}))
    total_ps   = len(ps_docs)
    total_arpu = sum(d.get("arpu", 0) or 0 for d in ps_docs)
    avg_arpu   = total_arpu / total_ps if total_ps else 0

    # PS harian
    ps_by_day = defaultdict(int)
    for d in ps_docs:
        tgl = d.get("tgl_ps") or d.get("tanggal_ps", "")
        try:
            if "-" in str(tgl):
                day = int(str(tgl).split("-")[-1])
            else:
                day = int(tgl)
            ps_by_day[day] += 1
        except (ValueError, TypeError):
            pass
    days = list(range(1, 32))
    ps_harian_labels = [str(d) for d in days]
    ps_harian_values = [ps_by_day.get(d, 0) for d in days]
    ps_harian_table = [{"tanggal": d, "ps": ps_by_day.get(d, 0)} for d in days if ps_by_day.get(d, 0) > 0]

    # Kategori & Paket
    kat_counter = Counter(d.get("kategori", "Lainnya") or "Lainnya" for d in ps_docs)
    kat_labels, kat_values = list(kat_counter.keys()), list(kat_counter.values())
    paket_counter = Counter(d.get("paket", "Lainnya") or "Lainnya" for d in ps_docs)
    paket_labels, paket_values = list(paket_counter.keys()), list(paket_counter.values())

    # PS per TL
    tl_ps = defaultdict(int)
    for d in ps_docs:
        tl = d.get("nama_tl", "Unknown") or "Unknown"
        tl_ps[tl] += 1
    tl_ps_sorted = sorted(tl_ps.items(), key=lambda x: x[1], reverse=True)
    tl_ps_labels, tl_ps_values = zip(*tl_ps_sorted) if tl_ps_sorted else ([], [])

    # Top SF
    sf_ps = defaultdict(int)
    for d in ps_docs:
        sf = d.get("nama_sf", "Unknown") or "Unknown"
        sf_ps[sf] += 1
    top_sf = sorted(sf_ps.items(), key=lambda x: x[1], reverse=True)[:15]
    top_sf_labels, top_sf_values = zip(*top_sf) if top_sf else ([], [])

    # DJP sheet
    djp_docs = list(mongo.db.kpi_djp.find(q_base, {"_id": 0}))
    total_djp     = len(djp_docs)
    total_briefing = sum(1 for d in djp_docs if "briefing" in str(d.get("category", "")).lower())

    djp_by_day = defaultdict(int)
    brief_by_day = defaultdict(int)
    for d in djp_docs:
        tgl = d.get("tgl") or d.get("tanggal", "")
        try:
            day = int(str(tgl).split("-")[-1]) if "-" in str(tgl) else int(tgl)
            djp_by_day[day] += 1
            if "briefing" in str(d.get("category", "")).lower():
                brief_by_day[day] += 1
        except (ValueError, TypeError):
            pass
    djp_harian_values  = [djp_by_day.get(d, 0) for d in days]
    brief_harian_values = [brief_by_day.get(d, 0) for d in days]
    djp_harian_table = [{"tanggal": d, "djp": djp_by_day.get(d,0), "briefing": brief_by_day.get(d,0)} for d in days if djp_by_day.get(d,0) > 0 or brief_by_day.get(d,0) > 0]

    # DJP per TL
    tl_djp = defaultdict(int)
    for d in djp_docs:
        tl = d.get("supervisor_name", "Unknown") or "Unknown"
        tl_djp[tl] += 1
    tl_djp_sorted = sorted(tl_djp.items(), key=lambda x: x[1], reverse=True)
    tl_djp_labels, tl_djp_values = zip(*tl_djp_sorted) if tl_djp_sorted else ([], [])

    # TL summary
    all_tl = set(tl_ps.keys()) | set(tl_djp.keys())
    tl_summary_table = sorted([{"nama": tl, "ps": tl_ps.get(tl,0), "djp": tl_djp.get(tl,0)} for tl in all_tl], key=lambda x: x["ps"], reverse=True)

    # Database SF sheet
    sf_docs = list(mongo.db.kpi_database.find(q_base, {"_id": 0}))
    sf_total    = len(sf_docs)
    sf_aktif    = sum(1 for d in sf_docs if str(d.get("status_sf", "")).lower() in ["aktif", "active"])
    sf_nonaktif = sf_total - sf_aktif
    total_tl    = len(set(d.get("kode_tl", "") for d in sf_docs if d.get("kode_tl")))
    db_sf_list  = sf_docs

    bulan_label = BULAN_NAMA[month-1] if 1 <= month <= 12 else str(month)

    return {
        "is_locked": is_locked, "uploaded_by": uploaded_by, "upload_at": upload_at,
        "last_update": last_update, "version": version, "wok": wok, "month": month,
        "year": year, "bulan_label": bulan_label,
        "total_ps": total_ps, "total_djp": total_djp, "total_briefing": total_briefing,
        "total_arpu": total_arpu, "avg_arpu": avg_arpu,
        "sf_aktif": sf_aktif, "sf_nonaktif": sf_nonaktif, "sf_total": sf_total, "total_tl": total_tl,
        "ps_harian_labels": ps_harian_labels, "ps_harian_values": ps_harian_values,
        "djp_harian_labels": ps_harian_labels, "djp_harian_values": djp_harian_values,
        "brief_harian_values": brief_harian_values,
        "kat_labels": kat_labels, "kat_values": kat_values,
        "paket_labels": paket_labels, "paket_values": paket_values,
        "tl_ps_labels": list(tl_ps_labels), "tl_ps_values": list(tl_ps_values),
        "tl_djp_labels": list(tl_djp_labels), "tl_djp_values": list(tl_djp_values),
        "top_sf_labels": list(top_sf_labels), "top_sf_values": list(top_sf_values),
        "ps_harian_table": ps_harian_table, "djp_harian_table": djp_harian_table,
        "tl_summary_table": tl_summary_table, "db_sf_list": db_sf_list
    }


@app.route('/kpi/export', methods=['POST'])
@login_required
@role_required('VP','GML')
def kpi_export():
    data = request.get_json(force=True)
    fmt = data.get('format', 'html')
    month = int(data.get('month', datetime.now().month))
    year = int(data.get('year', datetime.now().year))
    wok = data.get('wok', '')
    chart_images = data.get('chart_images', {})

    ctx = get_kpi_context(month, year, wok)
    ctx.update({
        'chart_images': chart_images,
        'export_mode': fmt,
        'generated_at': datetime.now().strftime('%d %B %Y, %H:%M WIB'),
        'months_list': MONTHS_LIST,
        'wok_list': WOK_LIST,
    })

    html_content = render_template('kpi_export.html', **ctx)

    if fmt == 'html':
        resp = make_response(html_content)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename="KPI_{wok}_{ctx["bulan_label"]}_{year}.html"'
        return resp
    elif fmt == 'pdf':
        # Kirim HTML dengan auto-print browser
        resp = make_response(html_content)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp
    else:
        return jsonify({"error": "Format tidak dikenal"}), 400

def update_progress(task_id, percent, message):
    upload_progress[task_id] = {
        "status": "processing",
        "percent": percent,
        "message": message,
        "updated_at": datetime.now().isoformat()
    }
def process_kpi_upload_background(task_id, file_bytes, filename, month, year, wok, uploader_name, uploader_id):
    """Proses file Excel KPI dengan update progress real-time (menggunakan iterrows)."""

    try:
        # ========== DEKLARASI COUNTER ==========
        absensi_mb_count = 0
        kpi_tl_count = 0
        orbit_count = 0
        upsell_count = 0
        briefing_mb_count = 0 
        # 1. Baca file
        update_progress(task_id, 5, "Membaca file Excel...")
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = xls.sheet_names
        print(f"[DEBUG] Sheet ditemukan: {sheet_names}")

        # 2. Hapus data lama
        update_progress(task_id, 10, "Menghapus data lama...")
        filt = {"month": month, "year": year, "wok": wok}
        for coll in ("kpi_ps", "kpi_djp", "kpi_database", "kpi_uploads"):
            mongo.db[coll].delete_many(filt)

        ps_records, djp_records, db_records = [], [], []
            # ===================== SHEET ABSENSI MB (BRIEFING DARI KOLOM AL) =====================
        briefing_mb_count = 0
        if "Absensi MB" in sheet_names:
            df_absen = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Absensi MB")
            # Cari kolom yang bernama "AL" (case-insensitive)
            col_al = None
            for col in df_absen.columns:
                if str(col).strip().upper() == "AL":
                    col_al = col
                    break
            if col_al is not None:
                # Hitung jumlah baris yang kolom AL-nya tidak kosong (atau berisi nilai tertentu)
                # Misal: anggap briefing jika kolom AL tidak kosong
                briefing_mb_count = df_absen[col_al].notna().sum()
                print(f"[DEBUG] Briefing dari Absensi MB (kolom AL): {briefing_mb_count}")
            else:
                print("[WARN] Kolom 'AL' tidak ditemukan di sheet Absensi MB")

        # ===================== SHEET KPI TL (Shift TL) =====================
        kpi_tl_count = 1
        if "KPI TL" in sheet_names:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="KPI TL")
            kpi_tl_count = len(df) - 1 if len(df) > 0 else 0
            print(f"[DEBUG] KPI TL: jumlah baris data = {kpi_tl_count}")
        else:
            print("[WARN] Sheet 'KPI TL' tidak ditemukan!")

        # ===================== SHEET ORBIT =====================
        orbit_count = 1
        if "Orbit" in sheet_names:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Orbit")
            orbit_count = len(df) - 1 if len(df) > 0 else 0
            print(f"[DEBUG] Orbit: jumlah baris data = {orbit_count}")
        else:
            print("[WARN] Sheet 'Orbit' tidak ditemukan!")

        # ===================== SHEET UPSELL =====================
        upsell_count = 1
        if "Upsell" in sheet_names:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Upsell")
            upsell_count = len(df) - 1 if len(df) > 0 else 0
            print(f"[DEBUG] Upsell: jumlah baris data = {upsell_count}")
        else:
            print("[WARN] Sheet 'Upsell' tidak ditemukan!")

        # ===================== SHEET PS =====================
        if "PS" in sheet_names:
            update_progress(task_id, 15, "Membaca sheet PS...")
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="PS")
            df.columns = [str(c).strip() for c in df.columns]
            total_rows = len(df)
            print(f"[DEBUG] PS: kolom = {list(df.columns)}")
            print(f"[DEBUG] PS: jumlah baris = {total_rows}")

            for idx, (_, row) in enumerate(df.iterrows()):
                if idx % 500 == 0:
                    percent = 15 + int((idx / total_rows) * 30)
                    update_progress(task_id, percent, f"Memproses PS: baris {idx}/{total_rows}")

                no = row.get('No')
                nama_sf = row.get('Nama SF')
                if pd.isna(no) or pd.isna(nama_sf):
                    continue

                ps_records.append({
                    **filt,
                    "nama_sf":   str(row.get('Nama SF', '')),
                    "kode_sf":   str(row.get('Kode SF', '')),
                    "nama_tl":   str(row.get('Nama TL', '')),
                    "kode_tl":   str(row.get('Kode TL', '')),
                    "paket":     str(row.get('Paket', '')),
                    "kategori":  str(row.get('Kategori', '')),
                    "arpu":      float(row.get('ARPU', 0) or 0),
                    "tgl_ps":    int(row.get('Tgl PS', 0) or 0),
                    "tanggal_ps": str(row.get('Tanggal PS', '')),
                    "uploaded_by": uploader_name,
                    "upload_at": datetime.now().strftime("%d %b %Y %H:%M WIB"),
                })
            update_progress(task_id, 45, f"Selesai PS ({len(ps_records)} record)")
            print(f"[DEBUG] PS: {len(ps_records)} record")
        else:
            print("[WARN] Sheet PS tidak ditemukan!")

        # ===================== SHEET DJP =====================
        if "DJP Approve" in sheet_names:
            update_progress(task_id, 50, "Membaca sheet DJP Approve...")
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="DJP Approve")
            df.columns = [str(c).strip() for c in df.columns]
            total_rows = len(df)
            print(f"[DEBUG] DJP: kolom = {list(df.columns)}")
            print(f"[DEBUG] DJP: jumlah baris = {total_rows}")

            for idx, (_, row) in enumerate(df.iterrows()):
                if idx % 500 == 0:
                    percent = 50 + int((idx / total_rows) * 15)
                    update_progress(task_id, percent, f"Memproses DJP: baris {idx}/{total_rows}")

                schedule_id = row.get('SCHEDULE ID')
                if pd.isna(schedule_id):
                    continue

                djp_records.append({
                    **filt,
                    "schedule_id":     str(row.get('SCHEDULE ID', '')),
                    "user_name":       str(row.get('USER NAME', '')),
                    "supervisor_name": str(row.get('SUPERVISOR NAME', '')),
                    "category":        str(row.get('SCHEDULE CATEGORY', '')),
                    "status":          str(row.get('STATUS', '')),
                    "tgl":             int(row.get('Tgl', 0) or 0),
                    "uploaded_by": uploader_name,
                    "upload_at": datetime.now().strftime("%d %b %Y %H:%M WIB"),
                })
            update_progress(task_id, 65, f"Selesai DJP ({len(djp_records)} record)")
            print(f"[DEBUG] DJP: {len(djp_records)} record")
        else:
            print("[WARN] Sheet DJP Approve tidak ditemukan!")
        if "KPI TL" in sheet_names:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="KPI TL", header=0)
            # Hapus baris yang semua kolomnya kosong
            df = df.dropna(how='all')
            kpi_tl_count = len(df)
            print(f"[DEBUG] KPI TL: jumlah baris data valid = {kpi_tl_count}")

        # ===================== SHEET DATABASE =====================
        if "Database" in sheet_names:
            update_progress(task_id, 70, "Membaca sheet Database...")
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Database")
            df.columns = [str(c).strip() for c in df.columns]
            total_rows = len(df)
            print(f"[DEBUG] Database: kolom = {list(df.columns)}")
            print(f"[DEBUG] Database: jumlah baris = {total_rows}")

            for idx, (_, row) in enumerate(df.iterrows()):
                if idx % 500 == 0:
                    percent = 70 + int((idx / total_rows) * 10)
                    update_progress(task_id, percent, f"Memproses SF: baris {idx}/{total_rows}")

                no = row.get('No')
                sales_force = row.get('Sales Force')
                if pd.isna(no) or pd.isna(sales_force):
                    continue

                db_records.append({
                    **filt,
                    "nama_sf":   str(row.get('Sales Force', '')),
                    "nama_tl":   str(row.get('Team Leader', '')),
                    "kode_tl":   str(row.get('Kode Team Leader', '')),
                    "status_sf": str(row.get('Status SF', 'ACTIVE')),
                    "status_tl": str(row.get('Status TL', 'ACTIVE')),
                    "uploaded_by": uploader_name,
                    "upload_at": datetime.now().strftime("%d %b %Y %H:%M WIB"),
                })
            update_progress(task_id, 80, f"Selesai SF ({len(db_records)} record)")
            print(f"[DEBUG] Database: {len(db_records)} record")
        else:
            print("[WARN] Sheet Database tidak ditemukan!")

        # Validasi
        if not ps_records and not djp_records and not db_records:
            raise ValueError("Tidak ada data yang valid di file Excel. Periksa nama sheet, kolom, dan isi data.")
                # ========== SIMPAN SEMUA SHEET (RAW) UNTUK VIEWER ==========
        update_progress(task_id, 82, "Menyimpan raw data semua sheet...")
        for sname in sheet_names:
            df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sname, header=None)
            headers = df_raw.iloc[0].fillna("").astype(str).tolist() if len(df_raw) > 0 else []
            data_raw = df_raw.iloc[1:].fillna("").astype(str).values.tolist() if len(df_raw) > 1 else []
            mongo.db.kpi_excel_data.update_one(
                {"month": month, "year": year, "wok": wok, "sheet_name": sname},
                {"$set": {
                    "sheet_name": sname,
                    "headers": headers,
                    "data": data_raw,
                    "total_rows": len(data_raw),
                    "total_cols": len(headers)
                }},
                upsert=True
            )
        print("[DEBUG] Semua sheet raw telah disimpan ke kpi_excel_data")

        # Simpan ke MongoDB
        update_progress(task_id, 85, "Menyimpan data PS...")
        if ps_records:
            mongo.db.kpi_ps.insert_many(ps_records)
        update_progress(task_id, 90, "Menyimpan data DJP...")
        if djp_records:
            mongo.db.kpi_djp.insert_many(djp_records)
        update_progress(task_id, 95, "Menyimpan data SF...")
        if db_records:
            mongo.db.kpi_database.insert_many(db_records)

        # Metadata
        update_progress(task_id, 98, "Menyimpan metadata...")
        mongo.db.kpi_uploads.update_one(
            filt,
            {"$set": {
                **filt,
                "filename": filename,
                "uploaded_by": uploader_name,
                "uploaded_by_id": uploader_id,
                "upload_at": datetime.now().strftime("%d %b %Y %H:%M WIB"),
                "upload_at_dt": datetime.now(),
                "ps_count": len(ps_records),
                "djp_count": len(djp_records),
                "sf_count": len(db_records),
                # METADATA BARU
                "absensi_mb_count": absensi_mb_count,
                "briefing_mb_count": briefing_mb_count,
                "kpi_tl_count": kpi_tl_count,
                "orbit_count": orbit_count,
                "upsell_count": upsell_count,
            }},
            upsert=True
        )

        # Selesai
        upload_progress[task_id] = {
            "status": "completed",
            "percent": 100,
            "message": "Upload dan pemrosesan berhasil!",
            "result": {
                "ps_count": len(ps_records),
                "djp_count": len(djp_records),
                "sf_count": len(db_records),
                "sheets": sheet_names,
            }
        }
        print("[DEBUG] Proses upload selesai.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        upload_progress[task_id] = {
            "status": "error",
            "percent": 0,
            "message": str(e)
        }
        print(f"[ERROR] Upload gagal: {e}")

@app.route("/api/kpi-check")
@login_required
def api_kpi_check():
    month = int(request.args.get("month", 5))
    year = int(request.args.get("year", 2026))
    wok = request.args.get("wok", "JAKTIM")
    filt = {"month": month, "year": year, "wok": wok}
    return jsonify({
        "ps": mongo.db.kpi_ps.count_documents(filt),
        "djp": mongo.db.kpi_djp.count_documents(filt),
        "sf": mongo.db.kpi_database.count_documents(filt),
        "sample_ps": list(mongo.db.kpi_ps.find(filt, {"_id":0, "nama_sf":1, "tgl_ps":1}).limit(2))
    })

if __name__ == '__main__':
    with app.app_context():
        try: setup_indexes()
        except Exception as e: print(e)
    app.run(debug=False, host='0.0.0.0', port=5000)
