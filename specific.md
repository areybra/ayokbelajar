# Spesifikasi Alat & Bahan untuk Membuat & Menjalankan AyokBelajar

## Perangkat Keras (Hardware)

| Komponen | Minimal | Direkomendasikan |
|---|---|---|
| **CPU** | Intel Core i5/AMD Ryzen 5 | Intel Core i7 atau AMD Ryzen 7 |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 500 MB (dev) / 1 GB (prod) | SSD 20 GB+ |
| **OS** | Windows 10/11, macOS 12+, Linux | Windows 11, macOS 14+, Ubuntu 22.04+ |
| **Browser** | Chrome 120+, Firefox 121+, Edge 120+ | Chrome 125+, Firefox 125+ |
| **Koneksi Internet** | 10 Mbps (dev) | 50 Mbps (prod) |

> **Catatan**: untuk pengembangan, Windows dengan PowerShell sudah cukup. Untuk produksi, disarankan Linux Server (Ubuntu/Debian) atau container Docker.

---

## Perangkat Lunak (Software)

### Lingkungan Pengembangan

| Komponen | Versi |
|---|---|
| **Python** | 3.12+ (dev: 3.14.6) |
| **pip** | 23.x+ |
| **Django** | 5.2.x |
| **virtualenv/virtualenvwrapper** | terbaru |
| **Git** | 2.30+ |
| **Editor/IDE** | VS Code, PyCharm, atau editor Python lain |
| **Node.js** | tidak wajib (Tailwind CSS CDN), optional: 20.x untuk development build |

### Dependencies (requirements.txt)

| Paket | Versi | Fungsi |
|---|---|---|
| Django | 5.2.17 | Framework utama |
| google-genai | 2.17.0 | SDK resmi Google Gemini API |
| google-generativeai | 0.8.6 | Library Gemini tambahan |
| pypdf | 6.15.0 | Ekstraksi teks PDF |
| youtube-transcript-api | 1.2.4 | Ambil transcript YouTube |
| httpx | 0.28.1 | HTTP client async |
| python-dotenv | 1.2.2 | Load environment variables |
| psycopg | 3.3.4 | PostgreSQL adapter |
| whitenoise | 6.12.0 | Static files CDN |
| gunicorn | 26.0.0 | WSGI server production |

### Frontend (CDN)

| Komponen | Versi | CDN |
|---|---|---|
| **Tailwind CSS** | 3.x | `https://cdn.tailwindcss.com` |
| **Alpine.js** | 3.14.9 | `https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js` |
| **HTMX** | 2.0.4 | `https://unpkg.com/htmx.org@2.0.4` |
| **marked.js** | 15.0.4 | `https://cdn.jsdelivr.net/npm/marked@15.0.4/marked.min.js` |

### API Eksternal

| Layanan | Tipe | Penggunaan |
|---|---|---|
| **Google Gemini API** | REST/SDK | Generate ringkasan, roadmap, flashcards, quiz, chat |
| **Supabase Auth** | OAuth2/PKCE | Autentikasi (email/password, Google, GitHub) |
| **Supabase PostgreSQL** | Database | Penyimpanan materi dan data pengguna (target prod) |

---

## Lingkungan Produksi

### Server Requirement

| Aspek | Spesifikasi |
|---|---|
| **OS** | Ubuntu 22.04 LTS / Debian 12 |
| **WSGI Server** | gunicorn (worker = 2-4 x CPU cores) |
| **Reverse Proxy** | Nginx (opsional, atau gunicorn langsung) |
| **Database** | Supabase PostgreSQL (hosted) |
| **Static Files** | whitenoise (gzip + brotli) |
| **HTTPS** | Let's Encrypt (opsional via reverse proxy) |

### Environment Variables (.env)

```
SECRET_KEY=<string acak panjang>
GOOGLE_API_KEY=<Google Gemini API key>
GEMINI_MODEL=gemini-flash-latest
SUPABASE_URL=<https://xxx.supabase.co>
SUPABASE_ANON_KEY=<anon key>
SUPABASE_CLIENT_ID=<Google OAuth client_id>
SUPABASE_GITHUB_CLIENT_ID=<GitHub OAuth client_id>
DATABASE_URL=<kosong untuk SQLite, isi untuk Supabase PostgreSQL>
DEBUG=False
ALLOWED_HOSTS=<domain>,localhost,127.0.0.1
```

---

## Prosedur Penyelanaan (Deployment)

1. **Build Docker Image**
   ```bash
   docker build -t ayokbelajar .
   ```

2. **Run Container**
   ```bash
   docker run -d -p 8000:8000 --env-file .env ayokbelajar
   ```

3. **Alternatif Tanpa Docker**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   gunicorn ayokbelajar_proj.wsgi:application --bind 0.0.0.0:8000
   ```

---

## File Konfigurasi Penting

| File | Lokasi | Fungsi |
|---|---|---|
| .env | Root project | Variabel rahasia API key, secret |
| requirements.txt | Root project | Dependency Python (UTF-16 BOM) |
| Dockerfile | Root project | Image production |
| Procfile | Root project | Heroku/CDN deployment |
| settings.py | ayokbelajar_proj/ | Konfigurasi Django |
| urls.py | ayokbelajar_proj/ | Routing utama |

---

## Koneksi Internet Yang Diperlukan

| Aktivitas | Minimum Bandwidth |
|---|---|
| **Development (lokal)** | 5 Mbps download |
| **Testing (Gemini API)** | 10 Mbps download |
| **Production (user aktif)** | 50 Mbps download, 10 Mbps upload |
| **OAuth (Supabase)** | HTTPS wajib, redirect ke `http://localhost:8000/oauth/callback/` untuk dev |

---

## Alat Uji

```
python manage.py check          # Health check Django
python manage.py migrate      # Migrasi database
python manage.py test core    # Unit test (~30+ test)
```