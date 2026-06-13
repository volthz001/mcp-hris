```markdown
# 🏢 MCP HRIS – Human Resource Information System

**Sistem Manajemen Karyawan Terpadu**  
Kasbon | Absensi | KPI Dashboard | Pesan Internal | Notifikasi Broadcast

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3+-black?logo=flask)
![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green?logo=mongodb)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📌 Tentang Aplikasi

**MCP HRIS** adalah sistem informasi sumber daya manusia yang dikembangkan khusus untuk **PT. Mega Creative Promosindo**.  
Aplikasi ini menggantikan proses manual dalam pengelolaan:

- 💰 **Kasbon karyawan** dengan kuota rolling 30 hari  
- 📅 **Absensi harian** (check‑in/out, izin, sakit, auto‑alpha)  
- 📊 **KPI monitoring** (upload Excel, chart interaktif, export laporan)  
- ✉️ **Pesan internal** antar pengguna  
- 🔔 **Notifikasi broadcast** dari manajemen  

Dibangun dengan **Flask**, **MongoDB**, dan **Chart.js**, serta mendukung **role‑based access** (VP, GML, Manager WOK, TL, SF) dan **7 tema gelap**.

---

## 📸 Tampilan Sistem (Screenshot)

> Semua gambar berikut disimpan dalam folder `/images` di repository ini.

### 🔹 Dashboard Utama  
Menu ringkasan statistik dan akses cepat ke semua modul.

![Dashboard](images/dashboard.png)

### 🔹 Manajemen Kasbon (Admin View)  
Lihat semua pengajuan, setujui/tolak, filter status.

![Kasbon Admin](images/kasbon_admin.png)

### 🔹 Kasbon Saya (User View)  
Riwayat pengajuan dan sisa kuota rolling 30 hari.

![Kasbon Saya](images/kasbon_user.png)

### 🔹 Form Pengajuan Kasbon  
Validasi nominal, keterangan, dan preview nominal.

![Form Kasbon](images/kasbon_form.png)

### 🔹 Absensi Harian  
Check‑in/out, izin, sakit dengan batas waktu, serta keterangan wajib.

![Absensi](images/absensi.png)

### 🔹 Riwayat Absensi  
Filter per tanggal, status, dan pagination.

![Riwayat Absensi](images/absensi_history.png)

### 🔹 KPI Dashboard  
Grafik PS harian, DJP, performa TL, top SF, distribusi paket.

![KPI Dashboard](images/kpi_dashboard.png)

### 🔹 Upload Data KPI (Excel)  
Progres real‑time, validasi sheet, dan riwayat upload.

![KPI Upload](images/kpi_upload.png)

### 🔹 Export Laporan KPI  
Ke HTML atau PDF, dengan capture chart otomatis.

![KPI Export](images/kpi_export.png)

### 🔹 Kotak Pesan Internal  
Tabs (masuk, terkirim, berbintang), search, dan action (bintang, hapus).

![Pesan](images/messages.png)

### 🔹 Notifikasi Broadcast  
Kirim ke semua user atau target spesifik, dengan prioritas.

![Notifikasi](images/notifications.png)

### 🔹 Laporan Harian (Absensi + Kasbon)  
Rekap gabungan per tanggal filter.

![Laporan Harian](images/report.png)

### 🔹 Manajemen Pengguna (Role & Lock)  
Admin (VP/GML) dapat mengubah role dan mengunci akun.

![User Management](images/user_management.png)

### 🔹 Profil & Ganti Password  
Setiap user dapat mengedit profil dan mengganti password.

![Profil](images/profile.png)

### 🔹 Multi‑Theme (7 tema gelap)  
Pilih tema sesuai preferensi: Amber, Forest, Ocean, Lavender, Rose, Slate, Coffee.

![Theme Switcher](images/themes.png)

---

## ✨ Fitur Lengkap

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

## 🛠 Arsitektur & Teknologi

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
│  • Blueprint routing (opsional, dipisah per modul)         │
└─────────────────────────┬───────────────────────────────────┘
                          │ PyMongo
┌─────────────────────────▼───────────────────────────────────┐
│                    MongoDB Database                         │
│  Collections: users, kasbon, absensi, messages,            │
│  notifications, kpi_ps, kpi_djp, kpi_database, kpi_uploads │
└─────────────────────────────────────────────────────────────┘
```

### Stack Detail

- **Backend:** Python 3.10+, Flask 2.3, PyMongo, Pandas (Excel parser)
- **Database:** MongoDB Atlas atau local
- **Frontend:** Jinja2 templates, CSS Grid/Flexbox, Chart.js
- **Security:** CSRF token, HMAC for password reset, HTTP‑only cookie, SameSite=Lax
- **Deployment:** PythonAnywhere, Railway, atau VPS dengan Gunicorn + Nginx

---

## 🚀 Instalasi & Menjalankan Lokal

### Prasyarat
- Python 3.10 atau lebih tinggi
- MongoDB (local / Docker / Atlas)
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

# 4. Buat file .env (lihat contoh di bawah)
# .env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database_name
SECRET_KEY=your-super-secret-key-min-32-characters
SESSION_COOKIE_SECURE=False   # set True jika pakai HTTPS

# 5. Jalankan aplikasi
python app.py
```

Buka http://localhost:5000

> **Catatan Login:**  
> Tidak ada akun default. Registrasi melalui `/register` (role default **TL**).  
> Untuk membuat akun dengan role **VP** atau **GML**, Anda perlu menambah/mengubah role langsung di database MongoDB.

---

## 📦 Deployment ke Production

### Menggunakan PythonAnywhere (PaaS)
1. Upload kode ke PythonAnywhere (via Git atau manual).
2. Set environment variables di tab **Web** → **Environment variables**.
3. Konfigurasi `MONGO_URI` dengan MongoDB Atlas.
4. Atur `SESSION_COOKIE_SECURE=True`.
5. Reload aplikasi.

### Menggunakan VPS (Ubuntu + Nginx + Gunicorn)
```bash
# Install gunicorn
pip install gunicorn

# Jalankan dengan gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app

# Konfigurasi Nginx sebagai reverse proxy
```

### Menggunakan Docker (opsional)
```bash
docker build -t mcp-hris .
docker run -p 5000:5000 --env-file .env mcp-hris
```

---

## 🔧 Panduan Pengguna Singkat

| Role       | Hak Akses                                                                 |
|------------|---------------------------------------------------------------------------|
| **VP**     | Semua: manajemen user (role & lock), lihat semua kasbon, approve/reject, upload KPI, broadcast notifikasi, laporan harian |
| **GML**    | Sama seperti VP (kecuali manajemen user mungkin dibatasi)                 |
| **Manager WOK** | Lihat kasbon & absensi di WOK-nya sendiri, approve kasbon level area |
| **TL**     | Lihat kasbon sendiri, lihat data SF di timnya (fitur tambahan)            |
| **SF / TS / TC** | Hanya akses: kasbon sendiri, absensi sendiri, pesan, notifikasi, profil |

---

## 🧪 Testing (Opsional)

Belum disediakan test otomatis secara built‑in. Namun Anda dapat menguji secara manual dengan:

1. Registrasi 2 user (misal: `vptest` dengan role VP di DB, `user1` dengan role TL).
2. Login sebagai `user1`, ajukan kasbon.
3. Login sebagai `vptest`, setujui kasbon.
4. Coba upload file Excel KPI (format sesuai template).
5. Cek grafik di `/kpi`.
6. Kirim pesan dan notifikasi.

---

## ❓ Troubleshooting Umum

| Masalah                                 | Solusi                                                                 |
|-----------------------------------------|------------------------------------------------------------------------|
| `MONGO_URI` not set                     | Pastikan `.env` berisi variabel tersebut. Aplikasi akan error jika kosong. |
| `SECRET_KEY` tidak konsisten setelah restart (development) | Set `SECRET_KEY` statis di `.env` untuk session persist. |
| Upload KPI gagal "sheet tidak ditemukan" | Pastikan file Excel memiliki sheet: `PS`, `DJP Approve`, `Database`, `Absensi MB`, `KPI TL`, `Orbit`, `Upsell`. |
| Check‑out tidak muncul                  | Hanya tersedia pukul 17:00‑18:30 waktu server (Asia/Jakarta). |
| Notifikasi tidak muncul                 | Cek polling `/api/unread-counts` di console browser. Pastikan user login. |
| Tema tidak berubah                      | Hapus localStorage `mcp-theme` atau cek console error. |

---

## 🤝 Kontribusi

Kami menerima kontribusi berupa:

- Laporan bug (via **Issues**)
- Permintaan fitur (via **Issues**)
- Pull request untuk perbaikan atau peningkatan

Untuk perubahan besar, harap diskusikan terlebih dahulu di issue.

---

## 📄 Lisensi

Distribusikan di bawah lisensi **MIT**.  
Lihat file [LICENSE](LICENSE) untuk informasi lebih lanjut.

---

## 👨‍💻 Author & Tim

Dikembangkan oleh tim internal **PT. Mega Creative Promosindo**.  
Untuk keperluan dukungan, hubungi: [it@megacreative.co.id](mailto:it@megacreative.co.id) (contoh).

---

## 🙏 Ucapan Terima Kasih

- **Flask** dan komunitas open‑source.
- **MongoDB** untuk database fleksibel.
- **Chart.js** untuk visualisasi data.

---

> Terakhir diperbarui: Juni 2026  
> Versi Aplikasi: 1.0.0
```
