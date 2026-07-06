# payroll/utils/pdf_generator.py
# Generate slip gaji PDF menggunakan ReportLab

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io

# Warna tema
COLOR_PRIMARY   = colors.HexColor('#1a3c5e')  # biru tua
COLOR_SECONDARY = colors.HexColor('#2e7d32')  # hijau
COLOR_LIGHT     = colors.HexColor('#f5f7fa')
COLOR_BORDER    = colors.HexColor('#dce3ea')
COLOR_RED       = colors.HexColor('#c62828')
COLOR_TEXT      = colors.HexColor('#1a1a2e')


def _rupiah(value) -> str:
    """Format angka ke format Rupiah."""
    try:
        return f"Rp {int(value):,.0f}".replace(',', '.')
    except (ValueError, TypeError):
        return "Rp 0"


def _persen(value) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (ValueError, TypeError):
        return "0%"


def generate_slip_pdf(slip: dict) -> bytes:
    """
    Generate slip gaji PDF dari dict slip MongoDB.
    Returns: bytes PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Style definitions ---
    style_title = ParagraphStyle(
        'SlipTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=COLOR_PRIMARY,
        spaceAfter=2,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    style_subtitle = ParagraphStyle(
        'SlipSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=2,
        alignment=TA_CENTER,
    )
    style_section = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
    )
    style_normal = ParagraphStyle(
        'SlipNormal',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=COLOR_TEXT,
    )
    style_bold = ParagraphStyle(
        'SlipBold',
        parent=styles['Normal'],
        fontSize=8.5,
        fontName='Helvetica-Bold',
        textColor=COLOR_TEXT,
    )
    style_right = ParagraphStyle(
        'SlipRight',
        parent=styles['Normal'],
        fontSize=8.5,
        alignment=TA_RIGHT,
        textColor=COLOR_TEXT,
    )
    style_total = ParagraphStyle(
        'SlipTotal',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=COLOR_PRIMARY,
        alignment=TA_RIGHT,
    )

    W = A4[0] - 30 * mm  # lebar konten

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    story.append(Paragraph("PT MEGA CREATIVE PROMOSINDO", style_title))
    story.append(Paragraph("Graha Raya Bintaro, BSD City, Tangerang Selatan", style_subtitle))
    story.append(Paragraph("SLIP GAJI KARYAWAN", ParagraphStyle(
        'SlipGajiTitle',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=COLOR_PRIMARY,
        spaceAfter=4,
        alignment=TA_CENTER,
    )))

    story.append(HRFlowable(width=W, thickness=2, color=COLOR_PRIMARY, spaceAfter=6))

    # -----------------------------------------------------------------------
    # Info Karyawan
    # -----------------------------------------------------------------------
    # Ambil periode dari periode_id (ObjectId → str 7 karakter jika YYYY-MM disimpan)
    # Jika periode disimpan di field periode, gunakan itu
    periode_str = slip.get('periode', str(slip.get('periode_id', ''))[:7])

    info_data = [
        ['Nama Karyawan', ':', slip.get('nama', '-'),
         'Periode', ':', periode_str],
        ['Jabatan', ':', slip.get('jabatan', '-'),
         'Status PTKP', ':', slip.get('status_ptkp', 'TK0')],
        ['Departemen', ':', slip.get('departemen', '-'),
         'Tarif TER', ':', _persen(slip.get('ter_rate', 0))],
    ]

    col_widths = [25 * mm, 4 * mm, 55 * mm, 25 * mm, 4 * mm, 40 * mm]
    info_table = Table(info_data, colWidths=col_widths)
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [COLOR_LIGHT, colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # Helper: buat tabel section
    # -----------------------------------------------------------------------
    def section_header(label: str, color=COLOR_PRIMARY):
        tbl = Table([[Paragraph(f"  {label}", style_section)]], colWidths=[W])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return tbl

    def row_data(label, amount, bold=False, color=colors.white):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        return [
            Paragraph(f"  {label}", ParagraphStyle('r', parent=styles['Normal'],
                       fontSize=8.5, fontName=fn, textColor=COLOR_TEXT)),
            Paragraph(_rupiah(amount), ParagraphStyle('rv', parent=styles['Normal'],
                       fontSize=8.5, fontName=fn, textColor=COLOR_TEXT,
                       alignment=TA_RIGHT)),
        ]

    def build_section_table(rows: list):
        """rows = list of [label, amount, bold?, bg_color?]"""
        data = []
        row_colors = []
        for i, r in enumerate(rows):
            label, amount = r[0], r[1]
            bold = r[2] if len(r) > 2 else False
            data.append(row_data(label, amount, bold))
            row_colors.append(COLOR_LIGHT if i % 2 == 0 else colors.white)

        tbl = Table(data, colWidths=[W * 0.65, W * 0.35])
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, COLOR_BORDER),
        ]
        for i, bg in enumerate(row_colors):
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
        tbl.setStyle(TableStyle(style_cmds))
        return tbl

    # -----------------------------------------------------------------------
    # Section: Pendapatan
    # -----------------------------------------------------------------------
    story.append(section_header("PENDAPATAN"))
    pendapatan_rows = [
        ['Gaji Pokok', slip.get('gaji_pokok', 0)],
        ['Tunjangan Tetap', slip.get('tunjangan_tetap', 0)],
        ['Uang Lembur', slip.get('uang_lembur', 0)],
        ['THR / Bonus', slip.get('thr_bonus', 0)],
        ['TOTAL PENDAPATAN', slip.get('total_pendapatan', 0), True],
    ]
    story.append(build_section_table(pendapatan_rows))
    story.append(Spacer(1, 4))

    # -----------------------------------------------------------------------
    # Section: Potongan Karyawan
    # -----------------------------------------------------------------------
    story.append(section_header("POTONGAN KARYAWAN", color=COLOR_RED))
    potongan_rows = [
        ['BPJS JHT (2%)', slip.get('bpjs_jht_karyawan', 0)],
        ['BPJS JP (1%)', slip.get('bpjs_jp_karyawan', 0)],
        ['BPJS Kesehatan (1%)', slip.get('bpjs_kes_karyawan', 0)],
        ['Cicilan Kasbon', slip.get('potongan_kasbon', 0)],
        ['TOTAL POTONGAN', slip.get('total_potongan', 0), True],
    ]
    story.append(build_section_table(potongan_rows))
    story.append(Spacer(1, 4))

    # -----------------------------------------------------------------------
    # Section: Tanggungan Perusahaan
    # -----------------------------------------------------------------------
    story.append(section_header("TANGGUNGAN PERUSAHAAN", color=COLOR_SECONDARY))
    perusahaan_rows = [
        ['BPJS JHT (3.7%)', slip.get('bpjs_jht_perusahaan', 0)],
        ['BPJS JP (2%)', slip.get('bpjs_jp_perusahaan', 0)],
        ['BPJS JKK', slip.get('bpjs_jkk', 0)],
        ['BPJS JKM (0.3%)', slip.get('bpjs_jkm', 0)],
        ['BPJS Kesehatan (4%)', slip.get('bpjs_kes_perusahaan', 0)],
        [f"PPh 21 Nett (TER {_persen(slip.get('ter_rate', 0))})",
         slip.get('pph21', 0)],
        ['TOTAL TANGGUNGAN PERUSAHAAN', slip.get('total_cost_perusahaan', 0), True],
    ]
    story.append(build_section_table(perusahaan_rows))
    story.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # Take-home summary
    # -----------------------------------------------------------------------
    takehome_data = [[
        Paragraph("GAJI BERSIH DITERIMA", ParagraphStyle(
            'th', parent=styles['Normal'], fontSize=11,
            fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph(_rupiah(slip.get('gaji_bersih', 0)), ParagraphStyle(
            'thv', parent=styles['Normal'], fontSize=13,
            fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_RIGHT)),
    ]]
    takehome_tbl = Table(takehome_data, colWidths=[W * 0.5, W * 0.5])
    takehome_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(takehome_tbl)
    story.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # Footer: Tanda tangan
    # -----------------------------------------------------------------------
    ttd_data = [[
        Paragraph("Diterima oleh,", style_normal),
        Paragraph("", style_normal),
        Paragraph("Disetujui oleh,", style_normal),
    ]]
    ttd_tbl = Table(ttd_data, colWidths=[W * 0.35, W * 0.3, W * 0.35])
    ttd_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(ttd_tbl)
    story.append(Spacer(1, 20 * mm))

    ttd_nama = [[
        Paragraph(f"({slip.get('nama', '________________')})", style_normal),
        Paragraph("", style_normal),
        Paragraph("(                              )", style_normal),
    ]]
    ttd_nama_tbl = Table(ttd_nama, colWidths=[W * 0.35, W * 0.3, W * 0.35])
    ttd_nama_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEABOVE', (0, 0), (0, 0), 0.5, COLOR_BORDER),
        ('LINEABOVE', (2, 0), (2, 0), 0.5, COLOR_BORDER),
    ]))
    story.append(ttd_nama_tbl)

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_BORDER))
    story.append(Paragraph(
        "Slip gaji ini diterbitkan secara otomatis oleh sistem MCP-HRIS. "
        "Dokumen ini sah tanpa tanda tangan basah apabila disetujui secara digital.",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.grey, alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(story)
    return buffer.getvalue()
