# payroll/migrate_users.py
# Jalankan SEKALI untuk menambahkan field gaji ke dokumen users yang sudah ada.
# Cara pakai:
#   cd /path/to/mcp-hris
#   python payroll/migrate_users.py

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mcp_hris')
client = MongoClient(MONGO_URI)
db = client.get_default_database()


def migrate():
    # Field baru yang ditambahkan ke semua user yang belum punya
    new_fields = {
        'gaji_pokok':      0,
        'tunjangan_tetap': 0,
        'status_ptkp':     'TK0',   # TK0 | TK1 | TK2 | TK3 | K0 | K1 | K2 | K3
        'risiko_kerja':    'sangat_rendah',
        'masa_kerja_bulan': 0,
    }

    result = db.users.update_many(
        {'gaji_pokok': {'$exists': False}},
        {'$set': new_fields}
    )
    print(f"[migrate_users] Updated {result.modified_count} dokumen user.")

    # Index untuk performa query payroll
    db.payroll_slips.create_index([('user_id', 1), ('periode_id', 1)], unique=True)
    db.payroll_slips.create_index([('periode_id', 1)])
    db.payroll_periods.create_index([('periode', 1)], unique=True)
    db.absensi.create_index([('user_id', 1), ('bulan', 1), ('tahun', 1)])
    print("[migrate_users] Index berhasil dibuat.")


if __name__ == '__main__':
    migrate()
