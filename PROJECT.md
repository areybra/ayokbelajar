# AyokBelajar — Dokumentasi Proyek & Handoff AI Agent

Dokumen ini merangkum arsitektur, workflow, konfigurasi, dan perbaikan yang sudah dilakukan.
Gunakan dokumen ini sebagai referensi cepat agar tidak perlu membaca seluruh source code untuk memahami proyek.

---

## 1. Ringkasan

Aplikasi belajar interaktif berbasis Django 5.2 yang mengubah materi belajar (teks, PDF, YouTube)
menjadi paket belajar lengkap: **rangkuman, mind map, peta belajar (roadmap), flashcards, dan simulasi ujian** — yang
dihasilkan oleh **Google Gemini API**. Tambahan: **chat dengan dokumen** untuk bertanya tentang materi.

- **Lokasi proyek:** `C:\yok\ayokbelajar_proj`
- **Framework:** Django 5.2.x (wajib, sesuai `AGENTS.md` — bukan Laravel/Next/React)
- **UI:** Django Templates + Tailwind CSS (CDN) + Alpine.js + HTMX-ish vanilla JS + marked.js
- **AI:** Google Gemini via library `google-genai` (SDK resmi, bukan REST manual)
- **Auth:** Supabase Auth (email/password + OAuth Google & GitHub) via PKCE; sesi Django dibangun manual
- **DB:** SQLite (dev) via `DATABASE_URL`; produksi target Supabase PostgreSQL + RLS

---

## 2. Stack & Lingkungan

| Komponen | Nilai |
|---|---|
| Python | 3.14.6 (dev local) |
| Django | 5.2.17 |
| Google SDK | `google-genai` 2.17.0 |
| PDF | `pypdf` 6.15.0 |
| YouTube transcript | `youtube-transcript-api` 1.2.4 — **pakai instance `.list(video_id)`**, bukan `list_transcripts` (dihapus di v1.2.4) |
| HTTP | `httpx` |
| Web server prod | `gunicorn` + `whitenoise` 6.12.0 (statics) |
| DB prod | `psycopg` (PostgreSQL) |
| Env loader | `python-dotenv` |

> **Catatan penting:** `requirements.txt` di-encode **UTF-16 dengan BOM**.
> Jangan menimpa dengan encoding lain; baca pakai `decode('utf-16')` bila diperlukan.

File penting lain: `Dockerfile` (python:3.12-slim + gunicorn + collectstatic), `Procfile` (gunicorn).

---

## 3. Struktur File Utama

```
C:\yok\ayokbelajar_proj\
├── manage.py
├── .env                        <- KONFIGURASI RAHASIA NYATA (dibaca settings.py)
├── requirements.txt            <- UTF-16 BOM
├── Dockerfile
├── Procfile
├── ayokbelajar_proj\
│   └── settings.py             <- load_dotenv(BASE_DIR / '.env'); DATABASES if/elif/else
│   └── urls.py                 <- root urls (mount core + accounts/)
├── core\
│   ├── urls.py                 <- semua route app
│   ├── views.py                <- view functions (landing..delete_document)
│   ├── services.py             <- logika bisnis + integrasi Gemini
│   ├── supabase_auth.py        <- PKCE, authorize_url, exchange_code, sign_up
│   ├── models.py               <- Profile, Document, ChatMessage, UserActivity
│   ├── forms.py                <- StudyKitForm, RegisterForm
│   ├── signals.py              <- buat Profile otomatis saat User dibuat
│   ├── apps.py                 <- ready() memuat signals
│   ├── admin.py
│   └── migrations\0001_0002
├── templates\
│   ├── base.html               <- layout: sidebar (login) / top navbar (anonim); [x-cloak] CSS
│   ├── registration\login.html <- tombol Google/GitHub + form email/password
│   └── core\
│       ├── dashboard.html      <- form input materi (Alpine: source switcher + x-cloak) + kredit/streak
│       ├── workspace.html      <- tampilan paket belajar (tab, editor rangkuman, ujian) + chat panel
│       ├── library.html        <- daftar materi + paginasi
│       ├── settings.html       <- pengaturan profil & preferensi
│       ├── register.html
│       ├── _profile_preferences_fields.html
│       └── landing.html
├── rules.md                    <- pedoman UI/UX proyek (design tokens, ikon hemat, a11y)
└── static\core\js\app.js       <- export md/csv (Blob), markdown, flashcards, ujian, chat, editor
```

> `C:\yok\core` (di luar proyek) adalah stub lama — **abaikan**.

---

## 4. Model Database

| Model | Field utama |
|---|---|
| `Profile` | user (OneToOne), learning_style, education_level, grade |
| `Document` | user (FK), title, source_type (text/youtube/pdf), source_url, raw_content, education_level, grade, ai_output (JSONField: summary, roadmap, flashcards, resources, exam), summary_html |
| `ChatMessage` | document (FK), role (user/assistant), content |
| `UserActivity` | user (FK), active_date (unik per user/hari) — dasar hitung hari streak |

Relasi: `User 1—1 Profile`, `User 1—N Document`, `Document 1—N ChatMessage`, `User 1—N UserActivity`.

---

## 5. Workflow Aplikasi

### 5.1 URL & View (namespaced `core:`)

```
/                               landing_view
/register/                      register_view
/oauth/<provider>/              oauth_login_view          (mulai PKCE, redirect ke Supabase)
/oauth/callback/                oauth_callback_view       (tukar code -> buat sesi)
/accounts/                      Django auth (login/logout/password)
/dashboard/                     dashboard_view            (login required; kredit & streak)
/preferences/                   preferences_view          (POST preferensi dari modal)
/library/                       library_view              (daftar materi + paginasi)
/settings/                      settings_view
/process/                       process_content_view      (POST materi -> proses Gemini)
/workspace/<pk>/                workspace_view            (tampilkan paket belajar)
/workspace/<pk>/chat/           chat_api_view             (POST JSON -> jawaban AI)
/workspace/<pk>/summary/        summary_save_api_view     (POST JSON -> simpan edit rangkuman)
/workspace/<pk>/exam/generate/  exam_generate_api_view    (POST -> generate 20 soal)
/workspace/<pk>/delete/         delete_document_view
```

### 5.2 Alur Auth
- **Register:** `RegisterForm` -> `sign_up()` ke Supabase -> buat `User` Django + `Profile` (via signal).
- **Login email/password:** form Django -> `authenticate/login` (sesi Django).
- **OAuth:** tombol Google/GitHub -> `authorize_url(provider)` membangun URL Supabase PKCE
  (tanpa `client_id`, pakai `scopes`) -> callback tukar `code` -> buat `User` lokal -> login.

### 5.3 Alur Proses Materi (core/services.py: `build_learning_kit`)
1. View menerima input dari `StudyKitForm` (teks / URL YouTube / upload PDF, jumlah flashcard,
   learning_style, education_level, grade). Field `num_quiz` sudah DIPINDAHKAN dari form.
2. Ekstrak konten: `extract_youtube_transcript()` (pakai API instance `.list()`; lihat catatan v1.2.4)
   atau `extract_pdf_text()` (pypdf).
3. Simpan `Document` (raw_content + metadata).
4. Panggil Gemini sekali untuk membuat `ai_output` berisi:
   `summary` (markdown), `roadmap` (steps), `flashcards`, `resources`.
   `exam` (20 soal pilihan ganda) DIBUAT TERPISAH via `/workspace/<pk>/exam/generate/`.
5. `_parse_json` memastikan output AI valid (fallback struktural jika JSON tidak bersih).

### 5.4 Chat dengan Dokumen (`chat_with_document`)
- Klik tombol "Tanya AI" (floating) -> panel chat -> POST ke `/workspace/<pk>/chat/`.
- Konteks = `raw_content` dokumen dikirim sebagai bagian dari prompt (tanpa vector store, sesuai AGENTS.md).
- Riwayat `ChatMessage` dirender di panel.

### 5.5 Export (100% client-side, sesuai AGENTS.md)
- **Markdown:** `Ayok.downloadMarkdown` -> Blob `text/markdown`.
- **Anki CSV:** `Ayok.downloadAnkiCSV` -> Blob CSV ber-BOM UTF-8.
- **Cetak PDF:** `window.print()` + CSS `no-print`.

### 5.6 Simulasi Ujian (`exam`)
- 20 soal pilihan ganda, dibuat AI **sesaat diminta** lewat `/workspace/<pk>/exam/generate/`
  (bukan saat generate materi) — karena itu kredit & proses materi tidak menunggu soal ujian.
- Item soal: `{question, options[4], correctAnswer (int 0-3), explanation}`.
- Pengaturan waktu: 30 menit di client (`app.js` `examEngine`); lulus bila skor ≥ 70%.

### 5.7 Kredit & Streak
- **Kredit bulanan:** `FREE_MONTHLY_DOCUMENT_LIMIT` (default 3) dikurangi jumlah dokumen bulan
  berjalan; sisa ditampilkan di dashboard.
- **Streak:** dihitung dari `UserActivity` (hari aktif beruntun), dicatat saat user membuka dashboard.
- Implementasi: `core/models.py` (`UserActivity.streak_for`, `record_if_new`) + `_dashboard_context`.

### 5.8 Loading State
- **Generate materi** (dashboard): overlay progress bar + persentase (palsu/indikasi, karena submit
  full-page POST).
- **Simulasi ujian** (workspace): skeleton loader menyerupai layout soal.
- Pedoman selengkapnya di `rules.md`.

---

## 6. Konfigurasi `.env` (RAHASIA — jangan commit)

File yang dibaca: **`C:\yok\ayokbelajar_proj\.env`** (bukan `C:\yok\.env` yang sudah stale).

| Var | Fungsi |
|---|---|
| `SECRET_KEY` | Django secret |
| `GOOGLE_API_KEY` | key Gemini (NYATA) |
| `GEMINI_MODEL` | **`gemini-flash-latest`** (jangan pakai `gemini-1.5-flash`, tidak tersedia) |
| `GEMINI_FALLBACK_MODELS` | daftar model cadangan dipisah koma; default `gemini-2.5-flash,gemini-2.5-flash-lite` (dipakai saat model aktif 429/5xx atau tidak tersedia) |
| `FREE_MONTHLY_DOCUMENT_LIMIT` | kuota kredit study kit per bulan (default `3`) |
| `SUPABASE_URL` | base URL Supabase project |
| `SUPABASE_ANON_KEY` | anon key |
| `SUPABASE_CLIENT_ID` | client_id OAuth Google terdaftar di Supabase |
| `SUPABASE_GITHUB_CLIENT_ID` | client_id OAuth GitHub |
| `DATABASE_URL` | **harus KOSONG** di dev agar pakai SQLite; jika diisi Supabase URL akan error |

---

## 7. Perbaikan yang Sudah Dilakukan (jangan regresi)

| # | Masalah | Solusi | File |
|---|---|---|---|
| 1 | Logout error CSRF | Tambah `django.middleware.csrf.CsrfViewMiddleware` ke `MIDDLEWARE` | `settings.py` |
| 2 | Input dashboard tak tampil | Ganti `hidden`/`:class` -> `x-show` + `x-cloak`; tambah CSS `[x-cloak]` | `dashboard.html`, `base.html` |
| 3 | Gemini API 400 (placeholder key) | `load_dotenv(BASE_DIR / '.env')` bukan parent | `settings.py` |
| 4 | Model Gemini tidak ada | `gemini-flash-latest` (bukan `gemini-1.5-flash`) | `.env` |
| 5 | DB config error | `DATABASE_URL` dikosongkan; struktur `DATABASES` if/elif/else + import `sys` | `.env`, `settings.py` |
| 6 | OAuth Google/GitHub ditolak | `authorize_url` pakai `scopes`, tanpa `client_id`/`response_type`; client_id asli dipakai via Supabase config | `core/supabase_auth.py` |
| 7 | Nav login vs anonim | Sidebar (kiri) untuk login; top navbar untuk anonim | `base.html` |
| 8 | Generate materi error 400 (skema quiz) | `quiz` dihapus dari skema & diganti `exam` (20 soal, generate terpisah); frontend pakai `correctAnswer` | `services.py`, `workspace.html`, `app.js` |
| 9 | Rangkuman tak bisa diedit (format) | Ganti Quill → `contenteditable` + `document.execCommand` (toolbar `.rt-toolbar`), simpan HTML ke `Document.summary_html` | `workspace.html`, `app.js`, `views.py` |
| 10 | "Layanan AI sedang ramai" (429/5xx) | Retry 5× + delay eksponensial + jitter; fallback multi-model (`GEMINI_FALLBACK_MODELS`) | `services.py`, `settings.py` |
| 11 | Model fallback `gemini-2.0-flash` sudah tidak ada (404) | Ganti default ke `gemini-2.5-flash,gemini-2.5-flash-lite`; APIError 404/400 dianggap "model tidak tersedia" → lanjut model berikut | `settings.py`, `services.py` |
| 12 | Statistik dashboard palsu (kredit & streak hardcoded) | Model `UserActivity` + hitung kredit bulanan nyata; tampilkan SVG (bukan emoji) | `models.py`, `views.py`, `dashboard.html` |
| 13 | Aksesibilitas & konsistensi UI | `skip-link`, `focus-visible`, emoji struktural → SVG hemat, copy quiz→simulasi ujian | `base.html`, semua template |
| 14 | `YouTubeTranscriptApi.list_transcripts` error (API v1.2.4) | Tidak pakai classmethod lama; gunakan **instance** `YouTubeTranscriptApi().list(video_id)` | `services.py` |

---

## 8. Menjalankan & Verifikasi

```bash
cd C:\yok\ayokbelajar_proj
python manage.py check          # health check
python manage.py migrate        # pastikan migrasi terpasang
python manage.py test core      # 64 unit test — semua PASS
python manage.py runserver      # dev di http://localhost:8000
```

Verifikasi manual setelah perubahan: login, proses materi (3 sumber), buka workspace, export, chat.

---

## 9. Catatan Operasional / Risiko

- **Supabase Redirect URL:** `http://localhost:8000/oauth/callback/` harus didaftarkan di
  Supabase Dashboard → Authentication → URL Configuration → Redirect URLs, jika tidak OAuth gagal.
- `python manage.py collectstatic` hanya untuk produksi; ada warning `staticfiles/` belum ada di dev — wajar.
- **jangan regresi:** jangan kembalikan pemanggilan YouTube ke `YouTubeTranscriptApi.list_transcripts()` —
  API itu dihapus di `youtube-transcript-api` 1.2.4; gunakan instance `.list()`.
- **Belum dikerjakan:** integrasi Supabase PostgreSQL/RLS produksi; payment/upgrade paket (harga di
  landing hanya mock); uji end-to-end OAuth pada env non-lokal; dark mode (sengaja ditunda).
- Baca `AGENTS.md` di `C:\yok` untuk aturan koding yang wajib dipatuhi (Django 5.x, minimal perubahan,
  test wajib, no hardcode secret). Pedoman UI: `rules.md` di root proyek.
