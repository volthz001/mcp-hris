```markdown
# MCP HRIS - Sistem Manajemen Karyawan

Sistem informasi terpadu untuk manajemen **Kasbon**, **Absensi**, **KPI**, **Pesan Internal**, dan **Notifikasi** berbasis Flask + MongoDB.

## ✨ Fitur Utama

- **👤 Autentikasi & Role**  
  Login/Register dengan session-based auth, role-based access (VP, GML, Manager WOK, TL, SF, dll).

- **💳 Manajemen Kasbon**  
  - Pengajuan kasbon dengan kuota rolling 30 hari (maks Rp500rb).  
  - Approve/reject oleh atasan.  
  - Riwayat lengkap dan ringkasan per user.

- **📅 Absensi**  
  - Check-in / check-out dengan jadwal (08:00–08:30 & 17:00–18:30).  
  - Izin / sakit dengan upload nomor surat.  
  - Auto-alpha jika tidak absen hingga 18:30.

- **📊 KPI Dashboard**  
  - Upload file Excel (PS, DJP, Database) secara asynchronous dengan progress.  
  - Visualisasi chart (PS harian, DJP, kategori, paket, performa TL & SF).  
  - Export laporan ke HTML/PDF (dengan capture chart otomatis).

- **✉️ Pesan Internal**  
  - Kirim pesan antar pengguna, bintang, hapus, mark as read/unread.  
  - Notifikasi real-time.

- **🔔 Notifikasi**  
  - Broadcast oleh VP/GML ke semua user atau target spesifik.  
  - Badge unread count.

- **📈 Laporan Harian**  
  - Ringkasan absensi dan kasbon per tanggal.

- **🎨 Multi-theme**  
  - 7 tema gelap (Amber, Forest, Ocean, Lavender, Rose, Slate, Coffee).

## 🛠 Tech Stack

| Komponen       | Teknologi                               |
|----------------|-----------------------------------------|
| Backend        | Python 3.10+, Flask                     |
| Database       | MongoDB (via Flask-PyMongo)             |
| Frontend       | HTML, CSS (custom), Chart.js            |
| Authentication | Session-based (tanpa Flask-Login)       |
| Excel Processing| Pandas, openpyxl                       |
| Security       | CSRFProtect, HMAC token reset password  |

## 📁 Struktur Proyek (simplifikasi)

```
.
├── app.py                 # Main aplikasi
├── requirements.txt       # Dependencies
├── .env                   # Environment variables (MONGO_URI, SECRET_KEY)
├── templates/             # Template HTML
│   ├── base.html
│   ├── dashboard.html
│   ├── kasbon*.html
│   ├── absensi*.html
│   ├── kpi*.html
│   ├── messages.html
│   ├── notifications.html
│   └── ...
└── static/
    ├── js/chart.umd.min.js
    └── img/logo_mcp.png
```

## 🚀 Instalasi & Menjalankan Lokal

### Prasyarat
- Python 3.10+
- MongoDB (lokal atau Atlas)
- Git

### Langkah-langkah

```bash
# Clone repo
git clone https://github.com/username/mcp-hris.git
cd mcp-hris

# Buat virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Buat file .env (lihat contoh di bawah)
# .env
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
SECRET_KEY=your-random-secret-key
# SESSION_COOKIE_SECURE=True   # jika pakai HTTPS
```

**Jalankan aplikasi:**
```bash
python app.py
```
Buka http://localhost:5000

### Login Default
> Sistem tidak menyediakn user default. Harus registrasi dulu di `/register` (boleh siapa saja, namun role di-hardcode TL di register). Untuk role VP/GML perlu dimasukkan manual via MongoDB.

## 📦 Deployment ke Production (Contoh: PythonAnywhere / Railway)

1. **MongoDB Atlas** – sudah disiapkan URI.
2. **Set environment variables** di platform hosting.
3. **Pastikan** `SECRET_KEY` statis dan panjang, `MONGO_URI` benar.
4. **Untuk HTTPS** – aktifkan `SESSION_COOKIE_SECURE=True`.
5. **Setup indexes** – kode sudah memanggil `setup_indexes()` saat startup.

## 🔧 Catatan Penting

- **Upload file KPI** membutuhkan sheet bernama: `PS`, `DJP Approve`, `Database`, `Absensi MB`, `KPI TL`, `Orbit`, `Upsell`.  
  Lihat fungsi `process_kpi_upload_background` untuk detail kolom yang dibaca.
- **Kuota kasbon** menggunakan rolling window 30 hari dengan status `approved` atau `pending`.
- **Absensi** otomatis menjadi `alpha` jika melewati pukul 18:30 tanpa check-in.

## 🤝 Kontribusi

Pull request dipersilakan. Untuk perubahan besar, buka issue terlebih dahulu.

## 📄 Lisensi

[MIT](LICENSE) © PT. Mega Creative Promosindo (contoh – sesuaikan dengan kebijakan perusahaan).

## 👨‍💻 Author

Dikembangkan untuk internal PT. Mega Creative Promosindo.
```

---

## File Pendukung yang Harus Disertakan

### 1. `.gitignore`
```
# Python
venv/
__pycache__/
*.pyc
.env
*.log
*.db
.DS_Store

# Flask
instance/

# IDE
.vscode/
.idea/
```

### 2. `requirements.txt`
Buat dengan `pip freeze > requirements.txt` setelah install semua modul yang digunakan. **Minimal harus ada**:
```
Flask==2.3.3
Flask-PyMongo==2.3.0
pandas==2.0.3
openpyxl==3.1.2
python-dotenv==1.0.0
pytz==2023.3
flask-wtf==1.1.1
flask-limiter==3.5.0
werkzeug==2.3.7
pymongo==4.5.0
```

### 3. `LICENSE` (contoh MIT)
```
MIT License

Copyright (c) 2025 PT. Mega Creative Promosindo

Permission is hereby granted...
```

### 4. `docker-compose.yml` (opsional)
```yaml
version: '3'
services:
  mongodb:
    image: mongo:6
    restart: always
    ports:
      - 27017:27017
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: secret
  app:
    build: .
    ports:
      - 5000:5000
    depends_on:
      - mongodb
    env_file:
      - .env
```

### 5. `Dockerfile` (opsional)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```
