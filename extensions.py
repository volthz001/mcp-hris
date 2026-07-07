# extensions.py
from flask_pymongo import PyMongo

mongo = PyMongo()

def get_current_user():
    """Ambil dokumen user aktif dari MongoDB (diakses melalui session)."""
    from flask import session
    from bson.objectid import ObjectId
    
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        # Menggunakan mongo yang sudah di-import dari extensions
        return mongo.db.users.find_one({"_id": ObjectId(uid)})
    except Exception:
        return None
