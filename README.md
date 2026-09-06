# AyokBelajar
[![Version](https://img.shields.io/badge/version-0.0.2--patch-blue)](https://github.com/areybra/ayokbelajar/releases)

Aplikasi belajar interaktif berbasis **Django 5.2** yang mengubah materi belajar (teks, PDF, YouTube)
menjadi paket belajar lengkap: **rangkuman, peta pikiran, peta belajar (roadmap), kartu belajar, dan latihan soal** —
semuanya dihasilkan oleh **Google Gemini API**. Plus **chat dengan dokumen** untuk bertanya langsung tentang materi.

> Status: **Development** — fitur aktif dikembangkan. Versi 0.0.2 (patch — fix OAuth Supabase 500 di Vercel/VPS/shared hosting: universal `ALLOWED_HOSTS/CSRF/BEHIND_PROXY/DATABASE_URL`, `vercel.json`, proxy HTTPS, dan deployment docs).

## Fitur

- 📄 **3 sumber materi**: tempel teks, URL YouTube (transkrip otomatis), atau unggah PDF (maks 20 MB).
- 🧠 **Study kit otomatis** via Gemini: rangkuman markdown, peta pikiran, roadmap bertahap, kartu belajar, dan sumber belajar tambahan.
- 📝 **Latihan soal** 20 soal pilihan ganda (dibuat AI saat diminta), lengkap timer + skor & pembahasan.
- ✏️ **Edit rangkuman** — hasil tersimpan ke dokumen.
- 🎨 **Preferensi akun** tersimpan di profil: jenjang pendidikan, kelas/semester. Gaya belajar (Visual, ELI5, Detailed, Socratic) dipilih saat membuat study kit baru di dashboard.
- 💬 **Chat dengan dokumen**: tanya jawab kontekstual tanpa vector database (zero-RAG).
- 📤 **Export**: Markdown & Anki CSV (client-side Blob), cetak PDF.
- 🔥 **Perlengkapan motivasi**: statistik materi, sisa kredit bulanan, dan streak hari belajar.
- 🔐 **Autentikasi**: email/password + OAuth Google & GitHub via Supabase Auth (PKCE).

## Teknologi

| Komponen | Pilihan |
|---|---|
| Backend | Django 5.2, Python 3.12+ |
| AI | Google Gemini (`google-genai`), fallback multi-model |
| UI | Django Templates + Tailwind CSS + Alpine.js + HTMX |
| Auth | Supabase Auth (email/password, Google, GitHub) |
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
- API key **Google Gemini** (`GOOGLE_API_KEY`)
- (Opsional) Supabase project untuk Auth, `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- (Opsional) MySQL server 8.x bila deploy ke produksi (lihat [Deployment](#deployment))

## Setup Development

```bash
# 1. Clone & masuk direktori
git clone https://github.com/areybra/ayokbelajar.git
cd ayokbelajar

# 2. Virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Buat .env dari template
#    (duplikat .env.example bila ada, atau buat manual sesuai tabel di bawah)

# 5. Migrasi & jalankan
python manage.py migrate
python manage.py runserver
```

Buka `http://localhost:8000`.

### Environment Variables (`.env`)

| Variabel | Keterangan |
|---|---|
| `SECRET_KEY` | Secret key Django (generate baru di produksi) |
| `GOOGLE_API_KEY` | API key Google Gemini |
| `GEMINI_MODEL` | Model Gemini, mis. `gemini-flash-latest` |
| `GEMINI_FALLBACK_MODELS` | Model cadangan (dipisah koma), mis. `gemini-2.5-flash,gemini-2.5-flash-lite` (opsional) |
| `FREE_MONTHLY_DOCUMENT_LIMIT` | Kuota study kit per bulan untuk paket Free (default `3`, opsional) |
| `SUPABASE_URL` | Base URL project Supabase |
| `SUPABASE_ANON_KEY` | Anon/public key Supabase |
| `SUPABASE_CLIENT_ID` | OAuth client id Google (opsional, via Supabase) |
| `SUPABASE_GITHUB_CLIENT_ID` | OAuth client id GitHub (opsional) |
| `DATABASE_URL` | Kosongkan untuk SQLite dev (`DEBUG=True`); isi di produksi: `mysql://...` (VPS/shared hosting) atau `postgres://...` (Supabase/Vercel) |
| `DEBUG` | `True` lokal, `False` di semua hosting produksi (VPS/Vercel/shared) |
| `ALLOWED_HOSTS` | Host yang diizinkan, pisah koma. Mis. VPS: `yourdomain.com,www.yourdomain.com` · Vercel: `.vercel.app,yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | **Wajib** saat `DEBUG=False` + HTTPS: `https://yourdomain.com,https://www.yourdomain.com` |
| `BEHIND_PROXY` | Set `True` bila di belakang Nginx/Cloudflare/Vercel agar `request.build_absolute_uri()` jadi `https://` (penting untuk OAuth Supabase) |

> ⚠️ Jangan pernah commit `.env`. File ini sudah ada di `.gitignore`.

## Menjalankan Test

```bash
python manage.py check        # health check
python manage.py migrate      # pastikan migrasi terpasang
python manage.py test core    # unit test
```

## Deployment — Universal (VPS / Shared Hosting / Vercel / PaaS)

Proyek **tidak hardcode untuk Vercel** — satu codebase jalan di semua hosting via env vars.
`vercel.json` + `build_files.sh` hanya dipakai Vercel; di VPS/shared hosting diabaikan.

### 1. Database produksi (wajib saat `DEBUG=False`)
SQLite hanya untuk dev lokal. Di hosting manapun, set `DATABASE_URL`:
- **VPS / shared hosting (MySQL 8.x)**: `mysql://user:password@db-host:3306/nama_database`
- **Supabase / Vercel Postgres**: `postgres://user:password@db-host:5432/postgres?sslmode=require`
> Engine dipilih otomatis `dj-database-url` (`mysql://` → `mysql`, `postgres://` → `postgres`).
> Jika `DATABASE_URL` kosong saat `DEBUG=False`, app akan 500 (`attempt to write a readonly database` di Vercel/PaaS).

### 2. VPS (Ubuntu/Debian + Nginx + systemd + gunicorn)

```bash
sudo apt update && sudo apt install python3.12-venv default-libmysqlclient-dev gcc pkg-config nginx
git clone https://github.com/areybra/ayokbelajar.git && cd ayokbelajar
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# .env produksi
cp .env.example .env  # lalu isi: DEBUG=False, SECRET_KEY, ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,
                      # CSRF_TRUSTED_ORIGINS=https://yourdomain.com, BEHIND_PROXY=True, DATABASE_URL=mysql://..., dll.

python manage.py migrate
python manage.py collectstatic --noinput
# test gunicorn
gunicorn ayokbelajar_proj.wsgi:application --bind 127.0.0.1:8000
```
Systemd unit `/etc/systemd/system/ayokbelajar.service` → `ExecStart=/path/.venv/bin/gunicorn ayokbelajar_proj.wsgi:application --bind 127.0.0.1:8000 --workers 3`
Nginx reverse proxy → `proxy_pass http://127.0.0.1:8000;` + `proxy_set_header X-Forwarded-Proto $scheme;` (wajib agar OAuth Supabase dapat `https://`)
`Procfile` sudah ada: `web: gunicorn ayokbelajar_proj.wsgi:application --bind 0.0.0.0:$PORT` (dipakai juga di PaaS).

### 3. Shared Hosting (cPanel / DirectAdmin Python App)
- Buat **Python App** (3.12) → point ke repo, `requirements.txt` auto-install.
- **Application startup file**: `ayokbelajar_proj/wsgi.py`, callable `application` (sudah ada alias `app`).
- Set **Environment Variables** di panel (bukan `.env` file bila hosting tidak baca): `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `SUPABASE_*`, dll.
- Jalankan di terminal hosting: `python manage.py migrate && python manage.py collectstatic --noinput`
- Passenger/Nginx hosting otomatis set `X-Forwarded-Proto`; bila tidak, set `BEHIND_PROXY=True`.

### 4. Vercel
- Import GitHub repo → Framework: **Other**, Build Command kosong (pakai `vercel.json`).
- Set **Environment Variables** di Vercel Dashboard (Production + Preview + Development):
  `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS=.vercel.app,yourdomain.com`, `CSRF_TRUSTED_ORIGINS=https://yourdomain.com` (Vercel auto-append `VERCEL_URL`), `DATABASE_URL=postgres://...` (Supabase pooler), `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GOOGLE_API_KEY`, `BEHIND_PROXY=True` (opsional, auto-detect via `VERCEL=1`).
- Deploy — `vercel.json` + `build_files.sh` urus `collectstatic`.
- Pastikan DB Postgres reachable dari Vercel (Supabase → allow all IPs atau pakai pooler).

### 5. OAuth Supabase (wajib untuk semua hosting)
Di **Supabase Dashboard → Authentication → URL Configuration → Redirect URLs** daftarkan **semua**:
```
http://localhost:8000/oauth/callback/
https://yourdomain.com/oauth/callback/
https://www.yourdomain.com/oauth/callback/
https://<project>.vercel.app/oauth/callback/
https://<project>-<preview>.vercel.app/oauth/callback/  # untuk preview deploy
```
Tanpa ini, `/oauth/<provider>/` akan 400/500 (`redirect_to` mismatch → `exchange_code` gagal).
Pastikan `GOOGLE_API_KEY` + `SUPABASE_*` terisi di hosting; jika kosong, login OAuth redirect ke `/accounts/login/` dengan pesan "belum dikonfigurasi" (bukan 500).

> ⚠️ Dev tetap SQLite lokal: kosongkan `DATABASE_URL` + `DEBUG=True`. Produksi: selalu isi `DATABASE_URL`.

## Struktur Proyek

```
ayokbelajar_proj/
├── core/                 # Aplikasi utama (views, services, models, forms)
│   ├── services.py       # Logika bisnis + integrasi Gemini
│   ├── supabase_auth.py  # PKCE / OAuth Supabase
│   └── templates/core/   # Template halaman (dashboard, workspace, library, dst.)
├── templates/            # Base layout & auth
 ├── static/core/js/       # JS client (export, flashcards, ujian, chat, editor)
 ├── requirements.txt      # Dependency (UTF-8 BOM, CRLF)
 ├── rules.md              # Pedoman UI/UX proyek
 ├── Procfile
 └── .env                  # Rahasia — JANGAN di-commit
```

## Lisensi

Belum ditentukan.
