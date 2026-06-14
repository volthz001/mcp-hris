# 🏢 MCP HRIS — Sistem Informasi Manajemen Karyawan

> **Kelola Karyawan Lebih Cerdas, Efisien, dan Transparan**  
> Solusi terpadu untuk Absensi, Kasbon, KPI, dan Komunikasi Internal berbasis web.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%2FLocal-green?logo=mongodb)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 Tentang Proyek

**MCP HRIS** adalah sistem informasi manajemen karyawan berbasis web yang menggantikan proses manual (spreadsheet & WhatsApp) dengan satu platform terpadu, aman, dan mudah digunakan.

Dibangun untuk membantu perusahaan dengan tim lapangan yang dinamis — khususnya di kawasan BSD City dan Tangerang Selatan — agar dapat mengelola:

- ✅ **Absensi** harian dengan timestamp otomatis dan anti-manipulasi
- ✅ **Kasbon** digital dengan approval berjenjang secara real-time
- ✅ **KPI Dashboard** dari upload Excel yang langsung menjadi grafik interaktif
- ✅ **Pesan Internal** terstruktur dengan prioritas dan read receipt

---

## 📸 Tampilan Sistem

### 🖥️ Dashboard KPI
![KPI Dashboard](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kpi_dashboard.png)

*Dashboard KPI menampilkan metrik performa tim secara real-time: Total PS, Briefing, ARPH, SF Aktif, dan grafik tren harian.*

---

### 📋 Absensi Harian
![Absensi](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/absensi.png)

*Halaman absensi dengan check-in/out berdasarkan waktu. Status otomatis: Hadir, Izin, Sakit, atau Alpha jika tidak ada aktivitas hingga 18:30.*

---

### 📜 Riwayat Absensi Karyawan
![Riwayat Absensi](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/absensi_history.png)

*Riwayat kehadiran lengkap per karyawan dengan filter tanggal & area. Dapat diekspor untuk keperluan payroll.*

---

### 💰 Form Pengajuan Kasbon
![Form Kasbon](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kasbon_form.png)

*Form pengajuan kasbon digital (Rp 50.000 – Rp 500.000) dengan kuota rolling 30 hari dan validasi otomatis.*

---

### 👤 Dashboard Kasbon User
![Kasbon User](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kasbon_user.png)

*Halaman pribadi karyawan untuk memantau sisa kuota, total pengajuan, dan riwayat transaksi kasbon.*

---

### 🛡️ Manajemen Kasbon — Admin
![Kasbon Admin](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kasbon_admin.png)

*Panel admin untuk approval/reject pengajuan kasbon dari seluruh karyawan secara real-time.*

---

### 📤 Upload Data KPI (Excel)
![KPI Upload](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kpi_upload.png)

*Interface upload file Excel (.xlsx) untuk data KPI harian. Sistem otomatis memvalidasi format sheet dan menyimpan metadata audit trail.*

---

### 📄 Export Laporan KPI
![KPI Export](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/kpi_export.png)

*Fitur export laporan KPI ke format PDF atau HTML dengan header resmi perusahaan dan grafik yang di-render ulang untuk print.*

---

### 💬 Pesan Internal
![Pesan](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/messages.png)

*Thread percakapan antar pengguna dengan label prioritas: Normal, Penting, Mendesak. Dilengkapi read receipt dan badge counter.*

---

### 🔔 Notifikasi Broadcast
![Notifikasi](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/notifications.png)

*Sistem notifikasi real-time. Atasan mendapat alert otomatis saat ada pengajuan baru. Broadcast bisa ditarget ke semua user atau user tertentu.*

---

### 📊 Laporan Harian Terpadu
![Laporan Harian](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/report.png)

*Ringkasan absensi dan kasbon dalam satu halaman. Tabel detail per karyawan lengkap dengan NIK & Area untuk rekapitulasi HR.*

---

### 👥 Manajemen Pengguna
![User Management](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/user_management.png)

*Panel admin untuk mengelola pengguna: filter by role/WOK/nama, kunci/buka akun, reset password. Mendukung 6 level role dengan hak akses terpisah.*

---

### 🎨 Multi-Theme (7 Tema Gelap)
![Theme Switcher](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/themes.png)

*7 pilihan tema warna termasuk dark mode untuk kenyamanan mata saat bekerja malam. Preferensi tersimpan di profil masing-masing user.*

---

### 👤 Profil & Pengaturan Akun
![Profil](https://raw.githubusercontent.com/volthz001/mcp-hris/main/images/profile.png)

*Halaman profil untuk edit data pribadi, ganti password, dan pengaturan akun. Setiap karyawan bisa mandiri mengelola informasi mereka.*

---

## ✨ Fitur Lengkap

| Modul | Fitur |
|---|---|
| **Kasbon** | Rolling limit 30 hari (maks Rp 500.000), min Rp 50.000, approval berjenjang VP/GML/Manager, status real-time, riwayat transparan |
| **Absensi** | Check-in (08:00–08:30), check-out (17:00–18:30 + keterangan), izin/sakit (08:00–10:00), auto-alpha setelah 18:30 |
| **KPI** | Upload Excel multipage (PS, DJP, Database, Absensi MB, KPI TL, Orbit, Upsell), grafik interaktif Chart.js, export HTML/PDF |
| **Pesan** | Thread per user, label prioritas, mark unread, soft delete, badge counter di header |
| **Notifikasi** | Broadcast ke semua user atau target tertentu, read receipt, alert otomatis pengajuan baru |
| **Laporan** | Filter tanggal range + WOK + nama, gabungkan tabel absensi & kasbon dalam satu halaman |
| **Manajemen User** | 6 level role (VP, GML, Manager WOK, TL, TC, TS), filter by role/WOK, kunci/buka akun |
| **Profil** | Edit data diri, ganti password (min 8 karakter + simbol) |
| **Tema** | 7 tema gelap, preferensi tersimpan per user |

---

## 🏗️ Arsitektur & Teknologi

```
┌─────────────────────────────────────────┐
│         Browser (Client)                │
│   HTML5 · CSS3 · Jinja2 · Chart.js      │
└──────────────────┬──────────────────────┘
                   │ HTTP / HTTPS
┌──────────────────▼──────────────────────┐
│       Flask Application (Python)        │
│   Session Auth · CSRFProtect · Limiter  │
└──────────────────┬──────────────────────┘
                   │ PyMongo
┌──────────────────▼──────────────────────┐
│           MongoDB Database              │
│  users · kasbon · absensi · messages    │
│  notifications · kpi_ps · kpi_uploads   │
└─────────────────────────────────────────┘
```

| Komponen | Teknologi |
|---|---|
| Backend | Python 3.10+, Flask, Flask-PyMongo, Flask-Limiter |
| Database | MongoDB (Atlas cloud / lokal) |
| Frontend | HTML5, CSS3 (Grid/Flexbox), Jinja2 Templates |
| Visualisasi | Chart.js |
| Pemrosesan Excel | Pandas, openpyxl |
| Keamanan | CSRFProtect, HMAC, HTTP-only cookie, Session Auth |
| Deployment | PythonAnywhere / VPS (Nginx + Gunicorn) / Docker |

---

## 🚀 Instalasi & Menjalankan

### Prasyarat
- Python 3.10+
- MongoDB (lokal atau Atlas)
- Git

### Langkah Instalasi

```bash
# 1. Clone repository
git clone https://github.com/volthz001/mcp-hris.git
cd mcp-hris

# 2. Buat virtual environment
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Buat file .env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
SECRET_KEY=your-super-secret-key-min-32-characters
SESSION_COOKIE_SECURE=False    # Ubah ke True jika pakai HTTPS

# 5. Jalankan aplikasi
python app.py
```

Buka `http://localhost:5000`

> **Catatan:** Tidak ada user default. Daftar melalui `/register` (role default: TL).  
> Untuk mengubah role ke VP atau GML, ubah langsung di MongoDB.

---

## 📦 Deployment Production

**PythonAnywhere**
Set environment variables, aktifkan HTTPS, `SESSION_COOKIE_SECURE=True`.

**VPS (Ubuntu + Nginx + Gunicorn)**
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

**Docker**
```bash
docker build -t mcp-hris .
docker run -p 5000:5000 --env-file .env mcp-hris
```

---

## 🧪 Hasil Pengujian

| Modul | Skenario | Hasil |
|---|---|---|
| Kasbon | Ajukan > Rp 500.000 | ✅ Ditolak sistem (validasi) |
| Kasbon | Approve pengajuan pending | ✅ Status berubah ke approved |
| Absensi | Check-in 08:15, check-out 17:20 | ✅ Tercatat sukses |
| Absensi | Tidak check-in hingga 18:31 | ✅ Otomatis status alpha |
| KPI Upload | Upload Excel sheet lengkap | ✅ Data tersimpan, grafik muncul |
| KPI Export | Klik export PDF | ✅ Dialog print muncul |
| Pesan | Kirim pesan dari user A ke B | ✅ Notifikasi dan pesan masuk |
| Role | TL akses menu admin | ✅ Redirect ke dashboard |

---

## 🗺️ Roadmap

- [ ] Integrasi mesin absensi RFID
- [ ] Notifikasi via WhatsApp Gateway
- [ ] Mobile responsive yang lebih optimal
- [ ] Export laporan kasbon & absensi ke Excel
- [ ] Sistem log activity untuk audit trail lengkap

---

## 👨‍💻 Developer

**Hizkia Siallagan** — Full-Stack Developer  
📧 hizkiasiallagan5@gmail.com  
📱 0821-7573-3644 (WA/Telepon)  
📍 BSD City, Tangerang Selatan  
🔗 [github.com/volthz001](https://github.com/volthz001)

---

## 📄 Lisensi

Kode sumber dilisensikan di bawah [MIT License](LICENSE).

---

> *Versi 1.0.0 · Juni 2026 · BSD City, Tangerang Selatan*
