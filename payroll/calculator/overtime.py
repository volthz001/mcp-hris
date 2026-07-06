# payroll/calculator/overtime.py
# Kalkulasi uang lembur sesuai PP No. 35 Tahun 2021
# Upah per jam = 1/173 x gaji sebulan

# Multiplier lembur hari kerja (PP 35/2021 Pasal 31)
MULTIPLIER_HARI_KERJA = [
    (1, 1.5),   # jam ke-1: 1.5x
    (float('inf'), 2.0),  # jam ke-2 dst: 2x
]

# Multiplier lembur hari libur/minggu (5 hari kerja/minggu)
MULTIPLIER_HARI_LIBUR_5 = [
    (8, 2.0),   # 8 jam pertama: 2x
    (1, 3.0),   # jam ke-9: 3x
    (float('inf'), 4.0),  # jam ke-10 dst: 4x
]

# Multiplier lembur hari libur/minggu (6 hari kerja/minggu)
MULTIPLIER_HARI_LIBUR_6 = [
    (7, 2.0),   # 7 jam pertama: 2x
    (1, 3.0),   # jam ke-8: 3x
    (float('inf'), 4.0),  # jam ke-9 dst: 4x
]


def _hitung_dengan_tier(upah_per_jam: float, total_jam: float, tiers: list) -> float:
    """Hitung upah lembur berdasarkan tier multiplier."""
    total = 0.0
    sisa = total_jam
    for batas, multiplier in tiers:
        if sisa <= 0:
            break
        jam_tier = min(sisa, batas)
        total += jam_tier * multiplier * upah_per_jam
        sisa -= jam_tier
    return total


def hitung_lembur(
    gaji_pokok: float,
    total_jam_lembur: float,
    tipe: str = 'hari_kerja'
) -> dict:
    """
    Hitung uang lembur berdasarkan PP No. 35 Tahun 2021.

    Args:
        gaji_pokok: Gaji pokok bulanan (basis perhitungan)
        total_jam_lembur: Total jam lembur dalam sebulan
        tipe: 'hari_kerja' | 'hari_libur_5' | 'hari_libur_6'

    Returns:
        Dict berisi upah per jam, total lembur, dan breakdown
    """
    if total_jam_lembur <= 0:
        return {
            'upah_per_jam': 0,
            'total_jam': 0,
            'total_lembur': 0,
            'tipe': tipe,
        }

    upah_per_jam = gaji_pokok / 173

    if tipe == 'hari_libur_5':
        tiers = MULTIPLIER_HARI_LIBUR_5
    elif tipe == 'hari_libur_6':
        tiers = MULTIPLIER_HARI_LIBUR_6
    else:
        tiers = MULTIPLIER_HARI_KERJA

    total = _hitung_dengan_tier(upah_per_jam, total_jam_lembur, tiers)

    return {
        'upah_per_jam': round(upah_per_jam),
        'total_jam': total_jam_lembur,
        'total_lembur': round(total),
        'tipe': tipe,
    }


def hitung_thr(gaji_pokok: float, tunjangan_tetap: float, masa_kerja_bulan: int) -> dict:
    """
    Hitung THR sesuai PP No. 36 Tahun 2021.
    - Masa kerja >= 12 bulan: 1 bulan gaji (pokok + tunjangan tetap)
    - Masa kerja < 12 bulan: proporsional (masa_kerja/12 x 1 bulan gaji)

    Args:
        gaji_pokok: Gaji pokok
        tunjangan_tetap: Total tunjangan tetap
        masa_kerja_bulan: Masa kerja dalam bulan

    Returns:
        Dict berisi detail THR
    """
    gaji_bulanan = gaji_pokok + tunjangan_tetap

    if masa_kerja_bulan >= 12:
        thr = gaji_bulanan
        proporsional = False
    else:
        thr = round((masa_kerja_bulan / 12) * gaji_bulanan)
        proporsional = True

    return {
        'gaji_bulanan': gaji_bulanan,
        'masa_kerja_bulan': masa_kerja_bulan,
        'thr': thr,
        'proporsional': proporsional,
    }
