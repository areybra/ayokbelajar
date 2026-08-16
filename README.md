# AyokBelajar
[![Version](https://img.shields.io/badge/version-0.0.1--minor-blue)](https://github.com/areybra/ayokbelajar/releases)

Aplikasi belajar interaktif berbasis **Django 5.2** yang mengubah materi belajar (teks, PDF, YouTube)
menjadi paket belajar lengkap: **rangkuman, peta pikiran, peta belajar (roadmap), kartu belajar, dan latihan soal** —
semuanya dihasilkan oleh **Google Gemini API**. Plus **chat dengan dokumen** untuk bertanya langsung tentang materi.

> Status: **Development** — fitur aktif dikembangkan. Versi 0.0.1 (minor release — perpindahan learning_style ke form study kit dan perbaikan terminologi Bahasa Indonesia).

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
| Database | SQLite (dev) → Supabase PostgreSQL + RLS (produksi) |
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
| `SECRET_KEY` | Secret key Django |
| `GOOGLE_API_KEY` | API key Google Gemini |
| `GEMINI_MODEL` | Model Gemini, mis. `gemini-flash-latest` |
| `GEMINI_FALLBACK_MODELS` | Model cadangan (dipisah koma), mis. `gemini-2.5-flash,gemini-2.5-flash-lite` (opsional) |
| `FREE_MONTHLY_DOCUMENT_LIMIT` | Kuota study kit per bulan untuk paket Free (default `3`, opsional) |
| `SUPABASE_URL` | Base URL project Supabase |
| `SUPABASE_ANON_KEY` | Anon/public key Supabase |
| `SUPABASE_CLIENT_ID` | OAuth client id Google (opsional) |
| `SUPABASE_GITHUB_CLIENT_ID` | OAuth client id GitHub (opsional) |
| `DATABASE_URL` | Kosongkan untuk SQLite dev; isi untuk PostgreSQL |
| `DEBUG` | `True` saat development |
| `ALLOWED_HOSTS` | Host yang diizinkan |

> ⚠️ Jangan pernah commit `.env`. File ini sudah ada di `.gitignore`.

## Menjalankan Test

```bash
python manage.py check        # health check
python manage.py migrate      # pastikan migrasi terpasang
python manage.py test core    # unit test
```

## Deployment

### Docker

```bash
docker build -t ayokbelajar .
docker run -d -p 8000:8000 --env-file .env ayokbelajar
```

### Manual (gunicorn)

```bash
python manage.py collectstatic --noinput
gunicorn ayokbelajar_proj.wsgi:application --bind 0.0.0.0:8000
```

> Catatan OAuth dev: daftarkan `http://localhost:8000/oauth/callback/` di
> Supabase Dashboard → Authentication → URL Configuration → Redirect URLs.

## Struktur Proyek

```
ayokbelajar_proj/
├── core/                 # Aplikasi utama (views, services, models, forms)
│   ├── services.py       # Logika bisnis + integrasi Gemini
│   ├── supabase_auth.py  # PKCE / OAuth Supabase
│   └── templates/core/   # Template halaman (dashboard, workspace, library, dst.)
├── templates/            # Base layout & auth
├── static/core/js/       # JS client (export, flashcards, ujian, chat, editor)
├── requirements.txt      # Dependency (UTF-16 BOM)
├── rules.md              # Pedoman UI/UX proyek
├── Dockerfile
├── Procfile
└── .env                  # Rahasia — JANGAN di-commit
```

## Lisensi

Belum ditentukan.
