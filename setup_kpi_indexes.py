"""
=============================================================
  setup_kpi_indexes.py  —  Jalankan SEKALI untuk buat index
  $ python setup_kpi_indexes.py
=============================================================
"""
from app import mongo  # import app yang sudah ada

def setup_indexes():
    db = mongo.db

    # kpi_ps indexes
    db.kpi_ps.create_index([("bulan_str", 1), ("wok", 1)])
    db.kpi_ps.create_index([("kode_sf", 1), ("bulan_str", 1)])
    db.kpi_ps.create_index([("nama_tl", 1), ("bulan_str", 1)])
    db.kpi_ps.create_index([("hari", 1), ("bulan_str", 1)])
    print("✅ kpi_ps indexes created")

    # kpi_djp indexes
    db.kpi_djp.create_index([("bulan_str", 1), ("wok", 1)])
    db.kpi_djp.create_index([("kategori", 1), ("bulan_str", 1)])
    db.kpi_djp.create_index([("kode_tl", 1), ("bulan_str", 1)])
    print("✅ kpi_djp indexes created")

    # kpi_database indexes
    db.kpi_database.create_index([("wok", 1)])
    db.kpi_database.create_index([("kode_sf", 1)], unique=True, sparse=True)
    db.kpi_database.create_index([("status_sf", 1)])
    print("✅ kpi_database indexes created")

    # kpi_uploads indexes
    db.kpi_uploads.create_index([("upload_at", -1)])
    db.kpi_uploads.create_index([("wok", 1), ("bulan_str", 1)])
    print("✅ kpi_uploads indexes created")

    print("\n🎉 Semua index berhasil dibuat!")

if __name__ == "__main__":
    setup_indexes()