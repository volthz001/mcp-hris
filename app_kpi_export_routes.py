"""
app_kpi_export_routes.py
════════════════════════
Tambahkan / merge kode ini ke app.py Anda.

Berisi:
  1. Helper parse_kpi_csv()    — baca MongoDB → dict lengkap semua sheet
  2. Route GET  /kpi            — render kpi.html (sudah ada, update context-nya)
  3. Route POST /kpi/export     — terima chart images dari browser, render kpi_export.html,
                                   kirim balik sebagai .html download ATAU render halaman
                                   untuk browser-print → PDF
  4. Route GET  /kpi/export/preview — preview export di browser (untuk test)
"""

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, jsonify, Response, make_response
)
from datetime import datetime
import json

# ── Jika pakai Blueprint, ganti nama sesuai app Anda ──
# kpi_bp = Blueprint('kpi', __name__)
# Atau langsung pakai @app.route jika tidak pakai Blueprint


# ══════════════════════════════════════════════════════
#   HELPER — ambil semua data KPI dari MongoDB
# ══════════════════════════════════════════════════════

def get_kpi_context(db, month: int, year: int, wok: str) -> dict:
    """
    Ambil semua data KPI dari MongoDB dan kembalikan sebagai dict
    yang siap dilempar ke template kpi.html / kpi_export.html.

    Koleksi MongoDB yang dipakai:
      - kpi_meta    : info upload (locked, uploaded_by, upload_at, version)
      - kpi_ps      : data sheet PS   (tgl_ps, nama_sf, kode_sf, nama_tl, kode_tl,
                                       paket, kategori, arpu, wok)
      - kpi_djp     : data sheet DJP  (tgl, user_code, user_name, supervisor_code,
                                       supervisor_name, schedule_category, status, wok)
      - kpi_sf      : data sheet DB   (nama_sf, kode_sf, team_leader, kode_tl,
                                       wok, status_sf, status_tl)
    """
    from collections import defaultdict, Counter

    q_base = {"month": month, "year": year, "wok": wok}

    # ── Meta info ──────────────────────────────────────────
    meta = db.kpi_meta.find_one(q_base) or {}
    is_locked   = bool(meta)
    uploaded_by = meta.get("uploaded_by", "—")
    upload_at   = meta.get("upload_at", "—")
    last_update = meta.get("upload_at", "")
    version     = meta.get("version", "1.0")

    # ── Sheet PS ───────────────────────────────────────────
    ps_docs = list(db.kpi_ps.find(q_base, {"_id": 0}))

    total_ps   = len(ps_docs)
    total_arpu = sum(d.get("arpu", 0) or 0 for d in ps_docs)
    avg_arpu   = total_arpu / total_ps if total_ps else 0

    # PS Harian
    ps_by_day = defaultdict(int)
    for d in ps_docs:
        tgl = d.get("tgl_ps") or d.get("tanggal_ps", "")
        try:
            day = int(str(tgl).split("-")[-1]) if "-" in str(tgl) else int(tgl)
            ps_by_day[day] += 1
        except (ValueError, TypeError):
            pass

    days = list(range(1, 32))
    ps_harian_labels = [str(d) for d in days]
    ps_harian_values = [ps_by_day.get(d, 0) for d in days]

    # PS Harian table (hanya hari > 0)
    ps_harian_table = [
        {"tanggal": d, "ps": ps_by_day.get(d, 0)}
        for d in days if ps_by_day.get(d, 0) > 0
    ]

    # Kategori
    kat_counter = Counter(d.get("kategori", "Lainnya") or "Lainnya" for d in ps_docs)
    kat_labels  = list(kat_counter.keys())
    kat_values  = list(kat_counter.values())

    # Paket
    paket_counter = Counter(d.get("paket", "Lainnya") or "Lainnya" for d in ps_docs)
    paket_labels  = list(paket_counter.keys())
    paket_values  = list(paket_counter.values())

    # PS per TL
    tl_ps = defaultdict(int)
    for d in ps_docs:
        tl = d.get("nama_tl", "Unknown") or "Unknown"
        tl_ps[tl] += 1
    tl_ps_sorted = sorted(tl_ps.items(), key=lambda x: x[1], reverse=True)
    tl_ps_labels = [t[0] for t in tl_ps_sorted]
    tl_ps_values = [t[1] for t in tl_ps_sorted]

    # Top SF
    sf_ps = defaultdict(int)
    for d in ps_docs:
        sf = d.get("nama_sf", "Unknown") or "Unknown"
        sf_ps[sf] += 1
    top_sf = sorted(sf_ps.items(), key=lambda x: x[1], reverse=True)[:15]
    top_sf_labels = [t[0] for t in top_sf]
    top_sf_values = [t[1] for t in top_sf]

    # ── Sheet DJP Approve ─────────────────────────────────
    djp_docs = list(db.kpi_djp.find(q_base, {"_id": 0}))

    total_djp     = len(djp_docs)
    total_briefing = sum(
        1 for d in djp_docs
        if "briefing" in str(d.get("schedule_category", "")).lower()
    )

    # DJP Harian
    djp_by_day     = defaultdict(int)
    brief_by_day   = defaultdict(int)
    for d in djp_docs:
        tgl = d.get("tgl") or d.get("tanggal", "")
        try:
            day = int(str(tgl).split("-")[-1]) if "-" in str(tgl) else int(tgl)
        except (ValueError, TypeError):
            day = 0
        if day:
            djp_by_day[day] += 1
            if "briefing" in str(d.get("schedule_category", "")).lower():
                brief_by_day[day] += 1

    djp_harian_labels  = [str(d) for d in days]
    djp_harian_values  = [djp_by_day.get(d, 0)   for d in days]
    brief_harian_values= [brief_by_day.get(d, 0)  for d in days]

    # DJP Harian table
    djp_harian_table = [
        {"tanggal": d, "djp": djp_by_day.get(d,0), "briefing": brief_by_day.get(d,0)}
        for d in days if djp_by_day.get(d,0) > 0 or brief_by_day.get(d,0) > 0
    ]

    # DJP per TL
    tl_djp = defaultdict(int)
    for d in djp_docs:
        tl = d.get("supervisor_name", "Unknown") or "Unknown"
        tl_djp[tl] += 1
    tl_djp_sorted = sorted(tl_djp.items(), key=lambda x: x[1], reverse=True)
    tl_djp_labels = [t[0] for t in tl_djp_sorted]
    tl_djp_values = [t[1] for t in tl_djp_sorted]

    # TL summary table
    all_tl = set(tl_ps.keys()) | set(tl_djp.keys())
    tl_summary_table = sorted([
        {"nama": tl, "ps": tl_ps.get(tl, 0), "djp": tl_djp.get(tl, 0)}
        for tl in all_tl
    ], key=lambda x: x["ps"], reverse=True)

    # ── Sheet Database (SF) ───────────────────────────────
    sf_docs = list(db.kpi_sf.find(q_base, {"_id": 0}))
    sf_total    = len(sf_docs)
    sf_aktif    = sum(1 for d in sf_docs if str(d.get("status_sf","")).lower() in ["aktif","active"])
    sf_nonaktif = sf_total - sf_aktif
    total_tl    = len(set(d.get("kode_tl","") for d in sf_docs if d.get("kode_tl")))
    db_sf_list  = sf_docs  # pass full list to template

    # ── Bulan label ───────────────────────────────────────
    BULAN = ["","Januari","Februari","Maret","April","Mei","Juni",
             "Juli","Agustus","September","Oktober","November","Desember"]
    bulan_label = BULAN[month] if 1 <= month <= 12 else str(month)

    return dict(
        # meta
        is_locked=is_locked, uploaded_by=uploaded_by,
        upload_at=upload_at, last_update=last_update, version=version,
        wok=wok, month=month, year=year, bulan_label=bulan_label,

        # ringkasan
        total_ps=total_ps, total_djp=total_djp,
        total_briefing=total_briefing,
        total_arpu=total_arpu, avg_arpu=avg_arpu,
        sf_aktif=sf_aktif, sf_nonaktif=sf_nonaktif,
        sf_total=sf_total, total_tl=total_tl,

        # chart data
        ps_harian_labels=ps_harian_labels,
        ps_harian_values=ps_harian_values,
        djp_harian_labels=djp_harian_labels,
        djp_harian_values=djp_harian_values,
        brief_harian_values=brief_harian_values,
        kat_labels=kat_labels, kat_values=kat_values,
        paket_labels=paket_labels, paket_values=paket_values,
        tl_ps_labels=tl_ps_labels, tl_ps_values=tl_ps_values,
        tl_djp_labels=tl_djp_labels, tl_djp_values=tl_djp_values,
        top_sf_labels=top_sf_labels, top_sf_values=top_sf_values,

        # tabel data
        ps_harian_table=ps_harian_table,
        djp_harian_table=djp_harian_table,
        tl_summary_table=tl_summary_table,
        db_sf_list=db_sf_list,
    )


# ══════════════════════════════════════════════════════
#   ROUTE — GET /kpi
# ══════════════════════════════════════════════════════

@app.route('/kpi')
@login_required
def kpi():
    now   = datetime.now()
    month = int(request.args.get('month', now.month))
    year  = int(request.args.get('year',  now.year))
    wok   = request.args.get('wok', session.get('wok', wok_list[0]))

    ctx = get_kpi_context(mongo.db, month, year, wok)

    ctx.update(
        wok_list=wok_list,
        months_list=months_list,
        flash_msg=session.pop('flash_msg', None),
        flash_type=session.pop('flash_type', 'info'),
    )
    return render_template('kpi.html', **ctx)


# ══════════════════════════════════════════════════════
#   ROUTE — POST /kpi/export
#   Body JSON:
#     { format: 'html'|'pdf',
#       wok, month, year,
#       chart_images: { psHarian, djpHarian, kategori,
#                       tlPs, tlDjp, topSf, paket } }
# ══════════════════════════════════════════════════════

@app.route('/kpi/export', methods=['POST'])
@login_required
def kpi_export():
    data   = request.get_json(force=True)
    fmt    = data.get('format', 'html')   # 'html' or 'pdf'
    month  = int(data.get('month', datetime.now().month))
    year   = int(data.get('year',  datetime.now().year))
    wok    = data.get('wok', '')
    chart_images = data.get('chart_images', {})

    ctx = get_kpi_context(mongo.db, month, year, wok)
    ctx.update(
        chart_images=chart_images,
        export_mode=fmt,
        generated_at=datetime.now().strftime('%d %B %Y, %H:%M WIB'),
    )

    html_content = render_template('kpi_export.html', **ctx)

    if fmt == 'html':
        # Kirim sebagai file download .html
        resp = make_response(html_content)
        resp.headers['Content-Type']        = 'text/html; charset=utf-8'
        resp.headers['Content-Disposition'] = (
            f'attachment; filename="KPI_{wok}_{ctx["bulan_label"]}_{year}.html"'
        )
        return resp

    elif fmt == 'pdf':
        # ── Opsi A: Kirim HTML dengan auto-print (browser jadi PDF printer) ──
        # User akan diminta Save As PDF di dialog print browser.
        resp = make_response(html_content)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        # Tidak set Content-Disposition agar browser render & auto-print
        return resp

        # ── Opsi B: Server-side PDF dengan WeasyPrint (uncomment jika terinstall) ──
        # from weasyprint import HTML as WP_HTML
        # pdf_bytes = WP_HTML(string=html_content).write_pdf()
        # resp = make_response(pdf_bytes)
        # resp.headers['Content-Type']        = 'application/pdf'
        # resp.headers['Content-Disposition'] = (
        #     f'attachment; filename="KPI_{wok}_{ctx["bulan_label"]}_{year}.pdf"'
        # )
        # return resp

    return jsonify({"error": "format tidak dikenal"}), 400


# ══════════════════════════════════════════════════════
#   ROUTE — GET /kpi/export/preview  (test/debug)
# ══════════════════════════════════════════════════════

@app.route('/kpi/export/preview')
@login_required
def kpi_export_preview():
    now   = datetime.now()
    month = int(request.args.get('month', now.month))
    year  = int(request.args.get('year',  now.year))
    wok   = request.args.get('wok', session.get('wok', wok_list[0]))

    ctx = get_kpi_context(mongo.db, month, year, wok)
    ctx.update(
        chart_images={},   # kosong → template tampilkan placeholder
        export_mode='preview',
        generated_at=datetime.now().strftime('%d %B %Y, %H:%M WIB'),
    )
    return render_template('kpi_export.html', **ctx)


# ══════════════════════════════════════════════════════
#   ROUTE — POST /kpi/unlock  (sudah ada di app.py Anda,
#   ini hanya referensi agar versi konsisten)
# ══════════════════════════════════════════════════════

@app.route('/kpi/unlock', methods=['POST'])
@login_required
def kpi_unlock():
    if session.get('role') not in ['VP', 'GML']:
        return jsonify({"success": False, "message": "Tidak punya akses"}), 403
    data  = request.get_json(force=True)
    month = int(data.get('month', 0))
    year  = int(data.get('year', 0))
    wok   = data.get('wok', '')
    q     = {"month": month, "year": year, "wok": wok}
    mongo.db.kpi_meta.delete_one(q)
    mongo.db.kpi_ps.delete_many(q)
    mongo.db.kpi_djp.delete_many(q)
    mongo.db.kpi_sf.delete_many(q)
    return jsonify({"success": True, "message": "Data berhasil dihapus dan dikunci dibuka."})