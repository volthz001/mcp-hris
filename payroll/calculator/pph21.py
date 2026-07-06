# payroll/calculator/pph21.py
# PPh 21 menggunakan metode TER (PMK 168/2023) berlaku 2024
# Metode: NETT — perusahaan menanggung pajak, take-home karyawan fixed

# ---------------------------------------------------------------------------
# Tabel TER Kategori A (TK/0) — s.d. kategori sesuai PMK 168/2023
# Format: (batas_atas_bruto, tarif)
# ---------------------------------------------------------------------------
TER_KATEGORI_A = [
    (5_400_000, 0.000),
    (5_650_000, 0.0025),
    (6_950_000, 0.005),
    (9_650_000, 0.0075),
    (10_050_000, 0.01),
    (10_350_000, 0.0125),
    (10_700_000, 0.015),
    (11_050_000, 0.0175),
    (11_600_000, 0.02),
    (12_500_000, 0.025),
    (13_750_000, 0.03),
    (15_100_000, 0.035),
    (16_950_000, 0.04),
    (19_750_000, 0.045),
    (24_150_000, 0.05),
    (26_450_000, 0.055),
    (28_000_000, 0.06),
    (30_050_000, 0.065),
    (32_400_000, 0.07),
    (35_400_000, 0.075),
    (39_100_000, 0.08),
    (43_850_000, 0.085),
    (47_800_000, 0.09),
    (51_400_000, 0.095),
    (56_300_000, 0.10),
    (62_200_000, 0.105),
    (68_600_000, 0.11),
    (77_500_000, 0.115),
    (89_000_000, 0.12),
    (103_000_000, 0.125),
    (125_000_000, 0.13),
    (157_000_000, 0.135),
    (206_000_000, 0.14),
    (337_000_000, 0.15),
    (454_000_000, 0.175),
    (550_000_000, 0.20),
    (695_000_000, 0.225),
    (910_000_000, 0.25),
    (float('inf'), 0.30),
]

# Kategori B: TK/1, TK/2, TK/3, K/0
TER_KATEGORI_B = [
    (6_200_000, 0.000),
    (6_500_000, 0.0025),
    (6_850_000, 0.005),
    (7_800_000, 0.0075),
    (8_850_000, 0.01),
    (9_800_000, 0.0125),
    (10_950_000, 0.015),
    (11_200_000, 0.0175),
    (12_050_000, 0.02),
    (12_950_000, 0.025),
    (14_150_000, 0.03),
    (15_550_000, 0.035),
    (17_050_000, 0.04),
    (19_500_000, 0.045),
    (22_700_000, 0.05),
    (26_600_000, 0.055),
    (28_100_000, 0.06),
    (30_100_000, 0.065),
    (32_600_000, 0.07),
    (35_600_000, 0.075),
    (39_100_000, 0.08),
    (43_950_000, 0.085),
    (47_800_000, 0.09),
    (51_400_000, 0.095),
    (56_300_000, 0.10),
    (62_200_000, 0.105),
    (68_600_000, 0.11),
    (77_500_000, 0.115),
    (89_000_000, 0.12),
    (103_000_000, 0.125),
    (125_000_000, 0.13),
    (157_000_000, 0.135),
    (206_000_000, 0.14),
    (337_000_000, 0.15),
    (454_000_000, 0.175),
    (550_000_000, 0.20),
    (695_000_000, 0.225),
    (910_000_000, 0.25),
    (float('inf'), 0.30),
]

# Kategori C: K/1, K/2, K/3
TER_KATEGORI_C = [
    (6_600_000, 0.000),
    (6_950_000, 0.0025),
    (7_350_000, 0.005),
    (9_050_000, 0.0075),
    (9_950_000, 0.01),
    (10_350_000, 0.0125),
    (10_700_000, 0.015),
    (11_050_000, 0.0175),
    (11_600_000, 0.02),
    (13_150_000, 0.025),
    (14_550_000, 0.03),
    (15_950_000, 0.035),
    (17_550_000, 0.04),
    (19_700_000, 0.045),
    (22_700_000, 0.05),
    (26_600_000, 0.055),
    (28_100_000, 0.06),
    (30_100_000, 0.065),
    (32_600_000, 0.07),
    (35_600_000, 0.075),
    (39_100_000, 0.08),
    (43_950_000, 0.085),
    (47_800_000, 0.09),
    (51_400_000, 0.095),
    (56_300_000, 0.10),
    (62_200_000, 0.105),
    (68_600_000, 0.11),
    (77_500_000, 0.115),
    (89_000_000, 0.12),
    (103_000_000, 0.125),
    (125_000_000, 0.13),
    (157_000_000, 0.135),
    (206_000_000, 0.14),
    (337_000_000, 0.15),
    (454_000_000, 0.175),
    (550_000_000, 0.20),
    (695_000_000, 0.225),
    (910_000_000, 0.25),
    (float('inf'), 0.30),
]

# Mapping status PTKP ke kategori TER
KATEGORI_MAP = {
    'TK0': TER_KATEGORI_A,
    'TK1': TER_KATEGORI_B,
    'TK2': TER_KATEGORI_B,
    'TK3': TER_KATEGORI_B,
    'K0':  TER_KATEGORI_B,
    'K1':  TER_KATEGORI_C,
    'K2':  TER_KATEGORI_C,
    'K3':  TER_KATEGORI_C,
}

PTKP_TAHUNAN = {
    'TK0': 54_000_000,
    'TK1': 58_500_000,
    'TK2': 63_000_000,
    'TK3': 67_500_000,
    'K0':  58_500_000,
    'K1':  63_000_000,
    'K2':  67_500_000,
    'K3':  72_000_000,
}


def _get_ter_rate(bruto_bulanan: float, status_ptkp: str) -> float:
    """Ambil tarif TER dari tabel sesuai kategori dan penghasilan bruto."""
    table = KATEGORI_MAP.get(status_ptkp, TER_KATEGORI_A)
    for batas, rate in table:
        if bruto_bulanan <= batas:
            return rate
    return 0.30


def hitung_pph21_nett(gaji_bruto_bulanan: float, status_ptkp: str = 'TK0') -> dict:
    """
    Hitung PPh 21 metode NETT menggunakan TER (PMK 168/2023).

    Metode NETT: perusahaan menanggung seluruh PPh 21.
    Take-home karyawan = gaji_bruto_bulanan (tidak berkurang pajak).

    Gross-up formula:
        Bruto gross-up = Nett / (1 - TER)
        PPh 21 ditanggung perusahaan = Bruto gross-up - Nett

    Returns dict berisi semua komponen kalkulasi.
    """
    ter = _get_ter_rate(gaji_bruto_bulanan, status_ptkp)

    if ter > 0:
        bruto_grossup = round(gaji_bruto_bulanan / (1 - ter))
    else:
        bruto_grossup = gaji_bruto_bulanan

    pph21 = bruto_grossup - gaji_bruto_bulanan

    return {
        'gaji_nett': gaji_bruto_bulanan,
        'bruto_grossup': bruto_grossup,
        'ter_rate': ter,
        'ter_persen': f"{ter * 100:.2f}%",
        'pph21_bulanan': pph21,
        'pph21_tahunan': pph21 * 12,
        'status_ptkp': status_ptkp,
        'ptkp_tahunan': PTKP_TAHUNAN.get(status_ptkp, 54_000_000),
    }
