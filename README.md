# AyokBelajar
[![Version](https://img.shields.io/badge/version-0.0.4--vercel-blue)](https://github.com/areybra/ayokbelajar/releases)

Aplikasi belajar interaktif berbasis **Django 5.2** yang mengubah materi belajar (teks, PDF, YouTube)
menjadi paket belajar lengkap: **rangkuman, peta pikiran, peta belajar (roadmap), kartu belajar, dan latihan soal** —
semuanya dihasilkan oleh **Google Gemini API**. Plus **chat dengan dokumen** untuk bertanya langsung tentang materi.

> Status: **Development** — Versi 0.0.4 (fix warning Vercel `unused-build-settings`: `vercel.json` modern tanpa `builds`/`routes`, entrypoint `api/index.py`, fallback `PyMySQL` untuk MySQL di serverless).

## Fitur

- 📄 **3 sumber materi**: tempel teks, URL YouTube (transkrip otomatis), atau unggah PDF (maks 20 MB).
- 🧠 **Study kit otomatis** via Gemini: rangkuman markdown, peta pikiran, roadmap bertahap, kartu belajar, dan sumber belajar tambahan.
- 📝 **Latihan soal** 20 soal pilihan ganda (dibuat AI saat diminta), lengkap timer + skor & pembahasan.
- ✏️ **Edit rangkuman** — hasil tersimpan ke dokumen.
- 🎨 **Preferensi akun** tersimpan di profil: jenjang pendidikan, kelas/semester. Gaya belajar (Visual, ELI5, Detailed, Socratic) dipilih saat membuat study kit baru di dashboard.
- 💬 **Chat dengan dokumen**: tanya jawab kontekstual tanpa vector database (zero-RAG).
- 📤 **Export**: Markdown & Anki CSV (client-side Blob), cetak PDF.
- 🔥 **Perlengkapan motivasi**: statistik materi, sisa kredit bulanan, dan streak hari belajar.
- 🔐 **Autentikasi**: email/password Django native (tanpa Supabase/OAuth — simpel untuk VPS/shared hosting).

## Teknologi

| Komponen | Pilihan |
|---|---|
| Backend | Django 5.2, Python 3.12+ |
| AI | Google Gemini (`google-genai`), fallback multi-model |
| UI | Django Templates + Tailwind CSS + Alpine.js + HTMX |
| Auth | Django Auth native (email/password, tanpa OAuth) |
| Database | SQLite (dev) → MySQL 8.x (produksi) |
| Server | gunicorn + whitenoise (static files) |

## Cara Kerja

1. Login/daftar → isi preferensi akun (jenjang, kelas). Gaya belajar dipilih saat membuat study kit.
2. Masukkan materi (teks / YouTube / PDF) di Dashboard → klik *Generate Study Kit*.
3. Gemini memproses materi dan menghasilkan rangkuman, peta pikiran, roadmap, kartu belajar, dan sumber belajar.
4. Buka workspace → minta *Latihan Soal* (20 soal) — timer, skor, & pembahasan otomatis.
5. Di workspace, kamu juga bisa edit rangkuman, export, atau bertanya ke AI tentang materi.

## Prasyarat

- Python 3.12+
- Git
- API key **Google Gemini** (`GOOGLE_API_KEY` — dapat dari https://aistudio.google.com/apikey)
- Dev lokal: cukup SQLite (tanpa MySQL)
- Produksi: MySQL 8.x + `DATABASE_URL=mysql://...` (lihat [Deployment Produksi](#deployment-produksi))

---

## Setup Development (Lokal)

Prinsip: `DEBUG=True` + `DATABASE_URL` dikosongkan → otomatis SQLite. Tanpa MySQL, tanpa Nginx.

### A. Windows (PowerShell)

```powershell
git clone https://github.com/areybra/ayokbelajar.git
cd ayokbelajar

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

Copy-Item .env.example .env
# edit .env: isi GOOGLE_API_KEY, biarkan DATABASE_URL= kosong, DEBUG=True

python manage.py migrate
python manage.py createsuperuser   # opsional, untuk /admin/
python manage.py runserver
```

Buka `http://localhost:8000` dan `http://localhost:8000/admin/`.

> `mysqlclient` di Windows kadang gagal build. Untuk dev lokal boleh hapus baris
> `mysqlclient==2.2.7` dari install sementara (`pip install` paket lain tetap jalan),
> atau install via wheel: `pip install --only-binary :all: mysqlclient==2.2.7`.
> Saat deploy ke Linux/VPS/shared hosting, `mysqlclient` tetap dibutuhkan.

### B. Linux / macOS / WSL

```bash
git clone https://github.com/areybra/ayokbelajar.git
cd ayokbelajar

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit .env: isi GOOGLE_API_KEY, biarkan DATABASE_URL= kosong, DEBUG=True

python manage.py migrate
python manage.py createsuperuser   # opsional
python manage.py runserver
```

### C. Contoh `.env` development

```ini
SECRET_KEY=django-insecure-dev-only-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_API_KEY=isi-api-key-gemini-disini
GEMINI_MODEL=gemini-flash-latest
GEMINI_FALLBACK_MODELS=gemini-2.5-flash,gemini-2.5-flash-lite
FREE_MONTHLY_DOCUMENT_LIMIT=5
DATABASE_URL=
```

### D. Verifikasi development

```bash
python manage.py check          # harus: System check identified no issues
python manage.py migrate        # pastikan migrasi terpasang
python manage.py test core      # unit test (74 test)
python manage.py runserver      # http://localhost:8000
```

Verifikasi manual: register → login → isi preferensi → proses materi (teks/YouTube/PDF) → buka workspace → generate latihan soal → chat → export.

### Troubleshooting development

| Gejala | Solusi |
|---|---|
| `GOOGLE_API_KEY` kosong / AI 400 | Isi key asli di `.env`, jangan pakai placeholder |
| `YouTubeTranscriptApi.list_transcripts` error | Sudah fix: pakai instance `.list(video_id)`, jangan kembalikan ke API lama |
| `mysqlclient` gagal install di Windows | Wajar untuk dev SQLite; install ulang saat deploy Linux atau pakai `--only-binary` |
| Port 8000 dipakai | `python manage.py runserver 8001` |

### Environment Variables (`.env`)

| Variabel | Keterangan |
|---|---|
| `SECRET_KEY` | Secret key Django. Dev boleh default; produksi wajib generate baru (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `GOOGLE_API_KEY` | API key Google Gemini (wajib untuk fitur AI) |
| `GEMINI_MODEL` | Model Gemini, mis. `gemini-flash-latest` |
| `GEMINI_FALLBACK_MODELS` | Model cadangan (dipisah koma), mis. `gemini-2.5-flash,gemini-2.5-flash-lite` (opsional) |
| `FREE_MONTHLY_DOCUMENT_LIMIT` | Kuota study kit per bulan paket Free (default `3`, opsional) |
| `DATABASE_URL` | Kosongkan untuk SQLite dev (`DEBUG=True`); isi di produksi MySQL: `mysql://user:password@host:3306/dbname` |
| `DEBUG` | `True` lokal, `False` di semua hosting produksi (VPS/shared/Vercel) |
| `ALLOWED_HOSTS` | Host yang diizinkan, pisah koma. Mis. lokal `localhost,127.0.0.1`, produksi `yourdomain.com,www.yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | **Wajib** saat `DEBUG=False` + HTTPS: `https://yourdomain.com,https://www.yourdomain.com` |
| `BEHIND_PROXY` | Set `True` bila di belakang Nginx/Cloudflare/Vercel agar `request.is_secure()` benar |

> ⚠️ Jangan pernah commit `.env`. File ini sudah ada di `.gitignore`. Commit hanya `.env.example`.

---

## Deployment Produksi

Prinsip produksi (berlaku untuk **semua** hosting):

1. `DEBUG=False`
2. `DATABASE_URL=mysql://user:password@host:3306/dbname` (MySQL 8.x, bukan SQLite)
3. `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
4. `CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com` (wajib bila HTTPS)
5. `SECRET_KEY` baru yang panjang
6. Jalankan `python manage.py migrate && python manage.py collectstatic --noinput`

### 0. Siapkan database MySQL + SECRET_KEY (sekali saja)

```sql
CREATE DATABASE ayokbelajar_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ayokbelajar_user'@'localhost' IDENTIFIED BY 'password-kuat-disini';
GRANT ALL PRIVILEGES ON ayokbelajar_db.* TO 'ayokbelajar_user'@'localhost';
FLUSH PRIVILEGES;
```

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Contoh `.env` produksi (VPS/shared):

```ini
SECRET_KEY=isi-secret-key-baru-yang-panjang
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
BEHIND_PROXY=True
DATABASE_URL=mysql://ayokbelajar_user:password-kuat-disini@localhost:3306/ayokbelajar_db
GOOGLE_API_KEY=isi-api-key-gemini-disini
GEMINI_MODEL=gemini-flash-latest
GEMINI_FALLBACK_MODELS=gemini-2.5-flash,gemini-2.5-flash-lite
FREE_MONTHLY_DOCUMENT_LIMIT=5
```

### 1. VPS (Ubuntu/Debian + Nginx + systemd + gunicorn) — direkomendasikan

```bash
# 1. Paket sistem
sudo apt update && sudo apt install -y python3.12-venv default-libmysqlclient-dev gcc pkg-config nginx

# 2. Clone
git clone https://github.com/areybra/ayokbelajar.git
cd ayokbelajar

# 3. Venv + deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Env produksi (lihat contoh di atas)
cp .env.example .env
nano .env

# 5. Migrasi + static
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# 6. Tes gunicorn
gunicorn ayokbelajar_proj.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Systemd `/etc/systemd/system/ayokbelajar.service`:

```ini
[Unit]
Description=AyokBelajar Django
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=/var/www/ayokbelajar
EnvironmentFile=/var/www/ayokbelajar/.env
ExecStart=/var/www/ayokbelajar/.venv/bin/gunicorn ayokbelajar_proj.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ayokbelajar
sudo systemctl status ayokbelajar
```

Nginx `/etc/nginx/sites-available/ayokbelajar`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /var/www/ayokbelajar/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ayokbelajar /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# HTTPS gratis:
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

> `Procfile` sudah ada (`web: gunicorn ayokbelajar_proj.wsgi:application`) untuk PaaS yang pakai buildpack.

### 2. Shared Hosting (cPanel / DirectAdmin — Python App)

1. Di cPanel → **Setup Python App** → Python **3.12** → application root `ayokbelajar` → startup file `ayokbelajar_proj/wsgi.py` → callable `application` (alias `app` sudah tersedia di `wsgi.py`).
2. Upload/clone repo ke application root, atau hubungkan via Git di cPanel.
3. Install `requirements.txt` lewat panel (tombol *Run pip install*). `mysqlclient` butuh lib MySQL — di kebanyakan shared hosting sudah tersedia; jika gagal, minta aktifkan `default-libmysqlclient-dev` ke support atau pakai hosting yang izinkan compiler.
4. Buat database MySQL via **MySQL Databases** + user, lalu isi **Environment Variables** di panel Python App (jangan mengandalkan file `.env` bila panel tidak membacanya):
   `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS=yourdomain.com`, `CSRF_TRUSTED_ORIGINS=https://yourdomain.com`, `DATABASE_URL=mysql://user:pass@localhost:3306/dbname`, `GOOGLE_API_KEY`, `BEHIND_PROXY=True`.
5. Di terminal hosting (cPanel Terminal / SSH):
   ```bash
   source ~/virtualenv/ayokbelajar/3.12/bin/activate
   cd ~/ayokbelajar
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```
6. **Restart** Python App dari panel. Buka `https://yourdomain.com`.

Troubleshooting shared hosting: 500 setelah deploy → cek log Python App (biasanya `stderr.log`): 90% karena `DATABASE_URL` salah, `ALLOWED_HOSTS` belum termasuk domain, atau `CSRF_TRUSTED_ORIGINS` belum `https://`.

### 3. Vercel (opsional — butuh MySQL eksternal)

Vercel filesystem read-only/ephemeral → **jangan pakai SQLite**. Gunakan MySQL eksternal (PlanetScale / Railway / Aiven) yang reachable dari internet.

1. `vercel.json` modern (tanpa `builds`/`routes` lawas) + entrypoint `api/index.py` sudah tersedia di repo — diabaikan di VPS/shared. Format baru memakai `buildCommand` + `functions` + `rewrites`, sehingga **warning `unused-build-settings` hilang** dan setting di Vercel Dashboard kembali berlaku.
2. Import repo GitHub di Vercel → Framework **Other** → Build Command dikunci dari `vercel.json` (`python manage.py collectstatic --noinput`), Output Directory `staticfiles`.
3. Isi **Environment Variables** di Vercel (Production + Preview):
   `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS=.vercel.app,yourdomain.com`, `CSRF_TRUSTED_ORIGINS=https://yourdomain.com`, `DATABASE_URL=mysql://user:pass@host:3306/dbname`, `GOOGLE_API_KEY`, `BEHIND_PROXY=True`.
   Vercel otomatis set `VERCEL=1` dan `VERCEL_URL`, sehingga `settings.py` auto-append `.vercel.app`.
4. MySQL di Vercel: `mysqlclient` butuh lib sistem yang tidak ada di serverless → repo sudah menyertakan fallback murni-Python `PyMySQL==1.1.1` + shim `pymysql.install_as_MySQLdb()` di `ayokbelajar_proj/__init__.py`, jadi backend Django `mysql` tetap jalan tanpa compiler. Di VPS/shared, `mysqlclient` biner tetap dipakai (lebih cepat).
5. Deploy. Batasan: cold start + `maxDuration: 60` — untuk trafik produksi serius, VPS tetap disarankan.

### 4. PaaS / Docker (Render / Railway / Fly / VPS-Docker)

- Buildpack (Render/Railway): start command `gunicorn ayokbelajar_proj.wsgi:application --bind 0.0.0.0:$PORT`, set env vars sama seperti produksi, tambahkan MySQL managed dari provider yang sama.
- Docker (contoh minimal):
  ```dockerfile
  FROM python:3.12-slim
  RUN apt-get update && apt-get install -y default-libmysqlclient-dev gcc pkg-config && rm -rf /var/lib/apt/lists/*
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn ayokbelajar_proj.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
  ```

### Checklist produksi (semua hosting)

- [ ] `DEBUG=False`, `SECRET_KEY` baru
- [ ] `DATABASE_URL` MySQL valid + `migrate` sukses
- [ ] `ALLOWED_HOSTS` berisi domain asli
- [ ] `CSRF_TRUSTED_ORIGINS` berisi `https://` domain asli
- [ ] `collectstatic` sukses, `/static/` ter-load, `/admin/` bisa login
- [ ] Register → login → generate study kit → workspace → chat jalan
- [ ] Log dicek (`journalctl -u ayokbelayar` / cPanel log / `vercel logs`)

> ⚠️ Dev tetap SQLite lokal: kosongkan `DATABASE_URL` + `DEBUG=True`. Produksi MySQL: selalu isi `DATABASE_URL`.

---

## Menjalankan Test

```bash
python manage.py check        # health check
python manage.py migrate      # pastikan migrasi terpasang
python manage.py test core    # unit test
```

## Struktur Proyek

```
ayokbelajar_proj/
├── core/                 # Aplikasi utama (views, services, models, forms)
│   ├── services.py       # Logika bisnis + integrasi Gemini
│   └── templates/core/   # Template halaman (dashboard, workspace, library, dst.)
├── templates/            # Base layout & auth
├── static/core/js/       # JS client (export, flashcards, ujian, chat, editor)
├── requirements.txt      # Dependency (mysqlclient + fallback PyMySQL untuk MySQL)
├── rules.md              # Pedoman UI/UX proyek
├── Procfile              # gunicorn (VPS/PaaS)
├── vercel.json           # deploy Vercel modern: buildCommand+functions+rewrites (diabaikan di VPS/shared)
├── api/index.py          # entrypoint serverless Vercel → import wsgi.application
└── .env                  # Rahasia — JANGAN di-commit
```

## Lisensi

Belum ditentukan.
