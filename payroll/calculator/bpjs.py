# payroll/calculator/bpjs.py
# Kalkulasi iuran BPJS Ketenagakerjaan & BPJS Kesehatan
# Referensi: PP 44/2015 (JHT/JKK/JKM), PP 45/2015 (JP), Perpres 82/2018 (Kes)

# Batas atas penghasilan (upah) untuk JP — diperbarui Kemnaker 2024
BATAS_ATAS_JP = 10_042_300
# Batas atas upah untuk BPJS Kesehatan
BATAS_ATAS_KES = 12_000_000

# Iuran JKK berdasarkan risiko pekerjaan (pilih sesuai jenis usaha)
JKK_RATES = {
    'sangat_rendah': 0.0024,   # 0.24%
    'rendah':        0.0054,   # 0.54%
    'sedang':        0.0089,   # 0.89%
    'tinggi':        0.0127,   # 1.27%
    'sangat_tinggi': 0.0174,   # 1.74%
}


def hitung_bpjs(
    gaji_pokok: float,
    tunjangan_tetap: float = 0,
    risiko_kerja: str = 'sangat_rendah'
) -> dict:
    """
    Hitung iuran BPJS Ketenagakerjaan dan Kesehatan.

    Basis iuran = gaji pokok + tunjangan tetap.
    Batas atas JP dan Kes diterapkan sesuai regulasi.

    Args:
        gaji_pokok: Gaji pokok bulanan
        tunjangan_tetap: Total tunjangan tetap (transport, makan, dll)
        risiko_kerja: Kategori risiko JKK ('sangat_rendah' default)

    Returns:
        Dict berisi semua komponen iuran karyawan dan perusahaan
    """
    basis = gaji_pokok + tunjangan_tetap
    basis_jp = min(basis, BATAS_ATAS_JP)
    basis_kes = min(basis, BATAS_ATAS_KES)
    jkk_rate = JKK_RATES.get(risiko_kerja, JKK_RATES['sangat_rendah'])

    # --- BPJS Ketenagakerjaan ---
    jht_perusahaan = round(basis * 0.037)   # 3.7%
    jht_karyawan   = round(basis * 0.02)    # 2.0%
    jp_perusahaan  = round(basis_jp * 0.02) # 2.0%
    jp_karyawan    = round(basis_jp * 0.01) # 1.0%
    jkk            = round(basis * jkk_rate)
    jkm            = round(basis * 0.003)   # 0.3%

    # --- BPJS Kesehatan ---
    kes_perusahaan = round(basis_kes * 0.04) # 4.0%
    kes_karyawan   = round(basis_kes * 0.01) # 1.0%

    # Total tanggungan
    total_perusahaan = jht_perusahaan + jp_perusahaan + jkk + jkm + kes_perusahaan
    total_karyawan   = jht_karyawan + jp_karyawan + kes_karyawan

    return {
        'basis': basis,
        'basis_jp': basis_jp,
        'basis_kes': basis_kes,

        # Tanggungan perusahaan
        'jht_perusahaan': jht_perusahaan,
        'jp_perusahaan':  jp_perusahaan,
        'jkk':            jkk,
        'jkk_rate':       jkk_rate,
        'jkm':            jkm,
        'kes_perusahaan': kes_perusahaan,
        'total_bpjs_perusahaan': total_perusahaan,

        # Potongan karyawan
        'jht_karyawan':   jht_karyawan,
        'jp_karyawan':    jp_karyawan,
        'kes_karyawan':   kes_karyawan,
        'total_bpjs_karyawan': total_karyawan,
    }
