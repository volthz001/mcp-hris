# payroll/routes/payroll.py
# Blueprint Flask untuk modul Payroll MCP-HRIS

from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime
import io

# Import dari app utama — sesuaikan dengan struktur project kamu
# from app import db  ← uncomment jika db didefinisikan di app.py
# Atau gunakan pattern lazy import:
def get_db():
    from app import db
    return db

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')

ALLOWED_ROLES_MANAGE = ['VP', 'GML']
ALLOWED_ROLES_VIEW   = ['VP', 'GML', 'Manager WOK', 'TS']


# ---------------------------------------------------------------------------
# Helper: Build satu slip gaji untuk satu karyawan
# ---------------------------------------------------------------------------
def _build_slip(karyawan: dict, periode: str, period_id, db) -> dict:
    from payroll.calculator.pph21 import hitung_pph21_nett
    from payroll.calculator.bpjs import hitung_bpjs
    from payroll.calculator.overtime import hitung_lembur

    uid = karyawan['_id']
    gaji_pokok     = float(karyawan.get('gaji_pokok', 0))
    tunjangan      = float(karyawan.get('tunjangan_tetap', 0))
    status_ptkp    = karyawan.get('status_ptkp', 'TK0')
    risiko_kerja   = karyawan.get('risiko_kerja', 'sangat_rendah')

    tahun, bulan = periode.split('-')

    # 1. Ambil data lembur dari absensi bulan ini
    absensi_bulan = list(db.absensi.find({
        'user_id': uid,
        'bulan': int(bulan),
        'tahun': int(tahun),
    }))
    total_jam_lembur = sum(float(a.get('lembur_jam', 0)) for a in absensi_bulan)
    lembur = hitung_lembur(gaji_pokok, total_jam_lembur)

    # 2. Ambil kasbon yang sudah disetujui dan belum dipotong
    kasbon_list = list(db.kasbon.find({
        'user_id': uid,
        'status': 'approved',
        'terpotong': {'$ne': True},
    }))
    total_kasbon = sum(float(k.get('jumlah', 0)) for k in kasbon_list)

    # 3. Hitung BPJS
    bpjs = hitung_bpjs(gaji_pokok, tunjangan, risiko_kerja)

    # 4. Total pendapatan bruto karyawan
    total_pendapatan = gaji_pokok + tunjangan + lembur['total_lembur']

    # 5. Hitung PPh 21 (Nett — ditanggung perusahaan)
    pph = hitung_pph21_nett(total_pendapatan, status_ptkp)

    # 6. Potongan karyawan
    total_potongan = (
        total_kasbon
        + bpjs['jht_karyawan']
        + bpjs['jp_karyawan']
        + bpjs['kes_karyawan']
    )

    gaji_bersih = total_pendapatan - total_potongan

    # 7. Total cost perusahaan
    total_cost = (
        total_pendapatan
        + pph['pph21_bulanan']
        + bpjs['total_bpjs_perusahaan']
    )

    # 8. Tandai kasbon sebagai terpotong
    kasbon_ids = [k['_id'] for k in kasbon_list]
    if kasbon_ids:
        db.kasbon.update_many(
            {'_id': {'$in': kasbon_ids}},
            {'$set': {'terpotong': True, 'potong_periode': periode}}
        )

    return {
        'periode_id':       period_id,
        'user_id':          uid,
        'nama':             karyawan.get('nama', ''),
        'jabatan':          karyawan.get('jabatan', ''),
        'departemen':       karyawan.get('departemen', ''),
        'status_ptkp':      status_ptkp,

        # Pendapatan
        'gaji_pokok':       gaji_pokok,
        'tunjangan_tetap':  tunjangan,
        'uang_lembur':      lembur['total_lembur'],
        'lembur_jam':       total_jam_lembur,
        'thr_bonus':        0,
        'total_pendapatan': total_pendapatan,

        # Potongan karyawan
        'potongan_kasbon':      total_kasbon,
        'bpjs_jht_karyawan':    bpjs['jht_karyawan'],
        'bpjs_jp_karyawan':     bpjs['jp_karyawan'],
        'bpjs_kes_karyawan':    bpjs['kes_karyawan'],
        'total_potongan':       total_potongan,

        # Take-home
        'gaji_bersih': gaji_bersih,

        # PPh 21 (tanggungan perusahaan)
        'pph21':        pph['pph21_bulanan'],
        'ter_rate':     pph['ter_rate'],
        'ter_persen':   pph['ter_persen'],

        # BPJS perusahaan
        'bpjs_jht_perusahaan': bpjs['jht_perusahaan'],
        'bpjs_jp_perusahaan':  bpjs['jp_perusahaan'],
        'bpjs_jkk':            bpjs['jkk'],
        'bpjs_jkm':            bpjs['jkm'],
        'bpjs_kes_perusahaan': bpjs['kes_perusahaan'],

        # Total cost
        'total_cost_perusahaan': total_cost,

        'status':     'draft',
        'created_at': datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@payroll_bp.route('/')
@login_required
def index():
    """Daftar periode penggajian."""
    if current_user.role not in ALLOWED_ROLES_VIEW:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('index'))

    db = get_db()
    periods = list(db.payroll_periods.find().sort('periode', -1).limit(24))
    return render_template('payroll/list.html', periods=periods)


@payroll_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    """Generate payroll draft untuk seluruh karyawan aktif."""
    if current_user.role not in ALLOWED_ROLES_MANAGE:
        return jsonify({'error': 'Unauthorized'}), 403

    db = get_db()
    data   = request.get_json()
    periode = data.get('periode')  # format: "2025-07"

    if not periode:
        return jsonify({'error': 'Periode wajib diisi (format: YYYY-MM)'}), 400

    # Cegah duplikat
    if db.payroll_periods.find_one({'periode': periode}):
        return jsonify({'error': f'Payroll {periode} sudah pernah di-generate'}), 409

    period_doc = {
        'periode':    periode,
        'status':     'draft',
        'created_by': str(current_user.id),
        'created_at': datetime.utcnow(),
    }
    period_id = db.payroll_periods.insert_one(period_doc).inserted_id

    karyawans = list(db.users.find({'status': 'active', 'role': {'$ne': 'admin'}}))
    slips = []
    errors = []

    for k in karyawans:
        try:
            slip = _build_slip(k, periode, period_id, db)
            slips.append(slip)
        except Exception as e:
            errors.append({'user_id': str(k['_id']), 'nama': k.get('nama'), 'error': str(e)})

    if slips:
        db.payroll_slips.insert_many(slips)

    # Update total cost ke period doc
    total_cost = sum(s['total_cost_perusahaan'] for s in slips)
    db.payroll_periods.update_one(
        {'_id': period_id},
        {'$set': {'total_cost_perusahaan': total_cost, 'jumlah_karyawan': len(slips)}}
    )

    return jsonify({
        'success': True,
        'periode': periode,
        'period_id': str(period_id),
        'total_slip': len(slips),
        'total_cost': total_cost,
        'errors': errors,
    })


@payroll_bp.route('/period/<period_id>')
@login_required
def detail_period(period_id):
    """Detail semua slip dalam satu periode."""
    if current_user.role not in ALLOWED_ROLES_VIEW:
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('payroll.index'))

    db = get_db()
    period = db.payroll_periods.find_one({'_id': ObjectId(period_id)})
    if not period:
        flash('Periode tidak ditemukan.', 'warning')
        return redirect(url_for('payroll.index'))

    slips = list(db.payroll_slips.find({'periode_id': ObjectId(period_id)}).sort('nama', 1))
    return render_template('payroll/detail.html', period=period, slips=slips)


@payroll_bp.route('/approve/<period_id>', methods=['POST'])
@login_required
def approve_period(period_id):
    """Finalisasi periode payroll (VP only)."""
    if current_user.role != 'VP':
        return jsonify({'error': 'Hanya VP yang dapat menyetujui payroll'}), 403

    db = get_db()
    db.payroll_periods.update_one(
        {'_id': ObjectId(period_id)},
        {'$set': {
            'status':      'approved',
            'approved_by': str(current_user.id),
            'approved_at': datetime.utcnow(),
        }}
    )
    db.payroll_slips.update_many(
        {'periode_id': ObjectId(period_id)},
        {'$set': {'status': 'approved'}}
    )
    return jsonify({'success': True})


@payroll_bp.route('/slip/<slip_id>')
@login_required
def slip_detail(slip_id):
    """Halaman detail slip gaji."""
    db = get_db()
    slip = db.payroll_slips.find_one({'_id': ObjectId(slip_id)})
    if not slip:
        flash('Slip tidak ditemukan.', 'warning')
        return redirect(url_for('payroll.index'))

    # Karyawan hanya bisa lihat slip sendiri
    is_own = str(slip['user_id']) == str(current_user.id)
    is_manager = current_user.role in ALLOWED_ROLES_VIEW
    if not (is_own or is_manager):
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('index'))

    return render_template('payroll/slip.html', slip=slip)


@payroll_bp.route('/slip/<slip_id>/pdf')
@login_required
def export_slip_pdf(slip_id):
    """Export slip gaji sebagai PDF menggunakan ReportLab."""
    db = get_db()
    slip = db.payroll_slips.find_one({'_id': ObjectId(slip_id)})
    if not slip:
        return 'Slip tidak ditemukan', 404

    is_own = str(slip['user_id']) == str(current_user.id)
    is_manager = current_user.role in ALLOWED_ROLES_VIEW
    if not (is_own or is_manager):
        return 'Akses ditolak', 403

    from payroll.utils.pdf_generator import generate_slip_pdf
    pdf_bytes = generate_slip_pdf(slip)

    periode_str = str(slip.get('periode_id', ''))[:7] if slip.get('periode_id') else 'unknown'
    filename = f"slip_{slip['nama'].replace(' ', '_')}_{periode_str}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@payroll_bp.route('/my-slips')
@login_required
def my_slips():
    """Daftar slip gaji milik karyawan yang login."""
    db = get_db()
    slips = list(db.payroll_slips.find(
        {'user_id': current_user.id, 'status': 'approved'}
    ).sort('created_at', -1))
    return render_template('payroll/my_slips.html', slips=slips)


# ---------------------------------------------------------------------------
# API Endpoints (untuk VRIS Flutter)
# ---------------------------------------------------------------------------

@payroll_bp.route('/api/my-slips')
@login_required
def api_my_slips():
    """API: daftar slip approved milik karyawan."""
    db = get_db()
    slips = list(db.payroll_slips.find(
        {'user_id': current_user.id, 'status': 'approved'},
        {'_id': 1, 'periode_id': 1, 'gaji_bersih': 1, 'total_pendapatan': 1,
         'total_potongan': 1, 'pph21': 1, 'created_at': 1}
    ).sort('created_at', -1).limit(12))

    for s in slips:
        s['_id'] = str(s['_id'])
        s['periode_id'] = str(s['periode_id'])
        s['created_at'] = s['created_at'].isoformat() if s.get('created_at') else None

    return jsonify(slips)


@payroll_bp.route('/api/slip/<slip_id>')
@login_required
def api_slip_detail(slip_id):
    """API: detail slip gaji (untuk VRIS)."""
    db = get_db()
    slip = db.payroll_slips.find_one({'_id': ObjectId(slip_id)})
    if not slip:
        return jsonify({'error': 'Not found'}), 404

    is_own = str(slip['user_id']) == str(current_user.id)
    if not (is_own or current_user.role in ALLOWED_ROLES_VIEW):
        return jsonify({'error': 'Forbidden'}), 403

    slip['_id'] = str(slip['_id'])
    slip['user_id'] = str(slip['user_id'])
    slip['periode_id'] = str(slip['periode_id'])
    slip['created_at'] = slip['created_at'].isoformat() if slip.get('created_at') else None

    return jsonify(slip)
