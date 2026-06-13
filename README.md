```markdown
# 🏢 MCP HRIS – Sistem Informasi Manajemen Karyawan  
**PT. Mega Creative Promosindo**

**Laporan Kerja Praktek**  
Diajukan sebagai salah satu syarat penyelesaian mata kuliah Kerja Praktek  
Program Studi Teknik Informatika – Universitas Pamulang
---

**Disusun oleh:**  
- **Hizkia Siallagan** (NIM: **********)  
- **Sebastianus Efraye Galdin** (NIM: **********)  

**Program Studi Teknik Informatika**  
**Fakultas Ilmu Komputer**  
**Universitas Pamulang**  

**Tahun Akademik 2025/2026**


## 📌 Abstrak

PT. Mega Creative Promosindo masih mengelola proses administrasi kepegawaian seperti pengajuan kasbon, absensi harian, dan monitoring kinerja secara manual menggunakan spreadsheet dan komunikasi via WhatsApp. Hal ini menyebabkan keterlambatan persetujuan, kesulitan dalam pelacakan riwayat, dan tidak adanya dashboard terpusat.

**MCP HRIS** hadir sebagai solusi berbasis web yang mengintegrasikan:
- Pengajuan kasbon dengan kuota rolling 30 hari
- Absensi harian (check‑in/out, izin, sakit, auto-alpha)
- Dashboard KPI (upload Excel, grafik interaktif, export laporan)
- Pesan internal dan notifikasi broadcast

Sistem dibangun menggunakan **Flask** (backend), **MongoDB** (database), dan **Chart.js** (visualisasi). Dengan role-based access (VP, GML, Manager WOK, TL, SF), sistem ini berhasil meningkatkan efisiensi dan transparansi data di perusahaan.

**Kata kunci:** Kasbon, Absensi, KPI, Flask, MongoDB, HRIS.

---
## 📸 Tampilan Sistem (Screenshot)

### Dashboard Utama
![Dashboard](images/dashboard.png)

### Manajemen Kasbon – Admin
![Kasbon Admin](images/kasbon_admin.png)

### Kasbon Saya (User)
![Kasbon User](images/kasbon_user.png)

### Form Pengajuan Kasbon
![Form Kasbon](images/kasbon_form.png)

### Absensi Harian
![Absensi](images/absensi.png)

### Riwayat Absensi
![Riwayat Absensi](images/absensi_history.png)

### KPI Dashboard
![KPI Dashboard](images/kpi_dashboard.png)

### Upload Data KPI (Excel)
![KPI Upload](images/kpi_upload.png)

### Export Laporan KPI
![KPI Export](images/kpi_export.png)

### Kotak Pesan Internal
![Pesan](images/messages.png)

### Notifikasi Broadcast
![Notifikasi](images/notifications.png)

### Laporan Harian (Absensi + Kasbon)
![Laporan Harian](images/report.png)

### Manajemen Pengguna
![User Management](images/user_management.png)

### Profil & Ganti Password
![Profil](images/profile.png)

### Multi‑Theme (7 tema gelap)
![Theme Switcher](images/themes.png)## ✨ Fitur Lengkap

| Modul          | Fitur                                                                 |
|----------------|-----------------------------------------------------------------------|
| **Kasbon**     | Rolling limit 30 hari (Rp500.000), min Rp50.000, status pending/approved/rejected, riwayat lengkap, validasi otomatis |
| **Absensi**    | Check‑in (08:00‑08:30), check‑out (17:00‑18:30 + keterangan), izin/sakit (08:00‑10:00), auto‑alpha setelah 18:30 |
| **KPI**        | Upload Excel multipage (PS, DJP, Database, Absensi MB, KPI TL, Orbit, Upsell), progress real‑time, chart.js, export HTML/PDF |
| **Pesan**      | Kirim ke user lain, tanda bintang, hapus permanen (soft delete), mark unread, priority (normal/penting/mendesak) |
| **Notifikasi** | Broadcast ke semua user atau pilih user tertentu, prioritas, read receipt |
| **Laporan**    | Filter tanggal range + WOK + nama, tampilkan tabel absensi dan kasbon sekaligus |
| **Manajemen User** | Ubah role (hanya VP), kunci/buka kunci akun, filter by role/WOK |
| **Profil**     | Edit data diri, ganti password (min 8 karakter + simbol) |
| **Tema**       | 7 tema gelap, persistensi ke localStorage |

---

## 🛠 Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client)                        │
│  • HTML5, CSS3 (custom variables)                          │
│  • Chart.js untuk grafik interaktif                         │
│  • JavaScript (fetch API, polling upload)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / HTTPS
┌─────────────────────────▼───────────────────────────────────┐
│                  Flask Application (Python)                 │
│  • Session‑based authentication (tanpa Flask‑Login)        │
│  • CSRF protection (Flask‑WTF)                             │
│  • Rate limiting (Flask‑Limiter)                           │
└─────────────────────────┬───────────────────────────────────┘
                          │ PyMongo
┌─────────────────────────▼───────────────────────────────────┐
│                    MongoDB Database                         │
│  Collections: users, kasbon, absensi, messages,            │
│  notifications, kpi_ps, kpi_djp, kpi_database, kpi_uploads │
└─────────────────────────────────────────────────────────────┘
```

### Stack Teknologi

| Komponen       | Teknologi                               |
|----------------|-----------------------------------------|
| Backend        | Python 3.10+, Flask, Flask-PyMongo      |
| Database       | MongoDB (Atlas / local)                 |
| Frontend       | HTML5, CSS3 (Grid/Flexbox), Jinja2      |
| Visualisasi    | Chart.js                                |
| Excel Processing| Pandas, openpyxl                       |
| Keamanan       | CSRFProtect, HMAC, HTTP‑only cookie     |

---

## 🚀 Instalasi & Menjalankan

### Prasyarat
- Python 3.10+
- MongoDB (local / Atlas)
- Git

### Langkah Instalasi

```bash
# 1. Clone repository
git clone https://github.com/username/mcp-hris.git
cd mcp-hris

# 2. Buat virtual environment
python -m venv venv
source venv/bin/activate     # Linux/Mac
# atau
venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Buat file .env (isi sesuai)
# .env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
SECRET_KEY=your-super-secret-key-min-32-characters
SESSION_COOKIE_SECURE=False   # set True jika pakai HTTPS

# 5. Jalankan aplikasi
python app.py
```

Buka http://localhost:5000

> **Login awal:** Tidak ada user default. Registrasi melalui `/register` (role default **TL**).  
> Untuk role VP atau GML, ubah manual di MongoDB.

---

## 📦 Deployment ke Production

- **PythonAnywhere:** Set environment variables, aktifkan HTTPS, `SESSION_COOKIE_SECURE=True`.
- **VPS (Ubuntu + Nginx + Gunicorn):**  
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 127.0.0.1:5000 app:app
  ```
- **Docker:**  
  ```bash
  docker build -t mcp-hris .
  docker run -p 5000:5000 --env-file .env mcp-hris
  ```

---

## 🧪 Hasil Pengujian dan Evaluasi

| Modul        | Skenario                                      | Hasil                                  |
|--------------|-----------------------------------------------|----------------------------------------|
| Kasbon       | Ajukan > Rp500.000                            | Ditolak sistem (validasi)              |
| Kasbon       | Ajukan Rp200.000, pending, lalu approve       | Status berubah menjadi approved        |
| Absensi      | Check‑in pukul 08:15, check‑out 17:20         | Tercatat sukses                        |
| Absensi      | Tidak check‑in hingga 18:31                   | Otomatis status alpha                  |
| KPI Upload   | Upload Excel dengan sheet lengkap             | Data tersimpan dan grafik muncul       |
| KPI Export   | Klik export PDF                               | Muncul dialog print, bisa save as PDF  |
| Pesan        | Kirim pesan dari user A ke B                  | B mendapat notifikasi dan pesan masuk  |
| Role         | User TL tidak bisa melihat menu admin         | Redirect ke dashboard                  |

**Kesimpulan:** Seluruh fungsi berjalan sesuai spesifikasi. Sistem siap digunakan di lingkungan produksi PT. Mega Creative Promosindo.

---

## 📄 Kesimpulan dan Saran

### Kesimpulan
- Aplikasi MCP HRIS berhasil mengotomatisasi pengelolaan kasbon, absensi, dan KPI.
- Mengurangi waktu persetujuan kasbon dari rata‑rata 2 hari menjadi < 1 jam.
- Manajemen dapat memantau kinerja SF secara real‑time melalui dashboard KPI.
- Karyawan memiliki transparansi penuh terhadap riwayat kasbon dan absensi mereka.

### Saran Pengembangan
1. **Integrasi dengan mesin absensi RFID** untuk check‑in/out otomatis.
2. **Notifikasi WhatsApp Gateway** untuk pengajuan kasbon dan pengumuman.
3. **Mobile responsive lebih optimal** (saat ini masih baik di desktop).
4. **Export ke Excel untuk laporan kasbon dan absensi**.
5. **Sistem log activity** untuk audit trail.

---

## 👨‍💻 Identitas Penulis

|                       |                                 |
|-----------------------|---------------------------------|
| **Nama 1**            | Hizkia Siallagan                |
| **NIM**               |                                 |
| **Email**             |                                 |   
| **Nama 2**            | Sebastianus Efraye Galdin       |
| **NIM**               |                                 |
| **Email**             |                                 |

**Program Studi:** Teknik Informatika  
**Fakultas:** Ilmu Komputer  
**Universitas:** Universitas Pamulang  
**Tahun:** 2025/2026

**Dosen Pembimbing:** 
**Ahmad Nursodiq** 

---

## 🙏 Ucapan Terima Kasih

- **PT. Mega Creative Promosindo** – atas kesempatan dan data yang diberikan.
- **Dosen Pembimbing** – atas bimbingan selama pelaksanaan kerja praktek.
- **Seluruh staf dan karyawan PT. MCP** – atas kerja sama dan masukan.
- **Tim open source** – Flask, MongoDB, Chart.js, dan seluruh pustaka yang digunakan.

---

## 📄 Lisensi

Kode sumber dilisensikan di bawah **MIT License**.  
Dokumen laporan kerja praktek ini adalah hak cipta Universitas Pamulang dan PT. Mega Creative Promosindo.

---

> Repository ini merupakan hasil **Kerja Praktek** yang disusun untuk memenuhi salah satu syarat kelulusan.  
> Dilarang menyalin atau menyebarluaskan tanpa izin tertulis dari penulis dan universitas.

**Terakhir diperbarui:** Juni 2026  
**Versi Aplikasi:** 1.0.0
```

