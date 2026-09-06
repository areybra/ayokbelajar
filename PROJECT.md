# AyokBelajar — Dokumentasi Proyek & Handoff AI Agent

Dokumen ini merangkum arsitektur, workflow, konfigurasi, dan perbaikan yang sudah dilakukan.
Gunakan dokumen ini sebagai referensi cepat agar tidak perlu membaca seluruh source code untuk memahami proyek.

---

## 1. Ringkasan

Aplikasi belajar interaktif berbasis Django 5.2 yang mengubah materi belajar (teks, PDF, YouTube)
menjadi paket belajar lengkap: **rangkuman, mind map, peta belajar (roadmap), flashcards, dan latihan soal** — yang
dihasilkan oleh **Google Gemini API**. Tambahan: **chat dengan dokumen** untuk bertanya tentang materi.

- **Lokasi proyek:** `C:\yok\ayokbelajar_proj`
- **Framework:** Django 5.2.x (wajib, sesuai `AGENTS.md` — bukan Laravel/Next/React)
- **UI:** Django Templates + Tailwind CSS (CDN) + Alpine.js + HTMX-ish vanilla JS + marked.js
- **AI:** Google Gemini via library `google-genai` (SDK resmi, bukan REST manual)
- **Auth:** Django Auth native (email/password saja, tanpa Supabase/OAuth)
 - **DB:** SQLite (dev via `runserver`); produksi MySQL 8.x lewat `DATABASE_URL` (`mysql://`).

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
| Admin panel | `django-jazzmin` 3.0.5 (tema `flatly` + brand teal, dark mode `auto`) |
 | DB prod | `mysqlclient` (MySQL 8.x) via `dj-database-url` (`DATABASE_URL`) |
 | Env loader | `python-dotenv` |

> **Catatan penting:** `requirements.txt` di-encode **UTF-8 dengan BOM** dan baris
> memakai **CRLF** (agar konsisten lintas sistem). Jangan timpa dengan encoding lain.

File penting lain: `Procfile` (gunicorn). Tidak ada lagi `Dockerfile` — proyek
deploy tanpa Docker (lihat README > Deployment).

---

## 3. Struktur File Utama

```
C:\yok\ayokbelajar_proj\
├── manage.py
├── .env                        <- KONFIGURASI RAHASIA NYATA (dibaca settings.py)
 ├── requirements.txt            <- MySQL via mysqlclient + dj-database-url
 ├── Procfile                     <- gunicorn
 ├── ayokbelajar_proj\
 │   └── settings.py             <- load_dotenv(BASE_DIR / '.env'); DATABASES via dj_database_url (mysql://)
│   └── urls.py                 <- root urls (mount core + accounts/)
├── core\
│   ├── urls.py                 <- semua route app
│   ├── views.py                <- view functions (landing..delete_document)
│   ├── services.py             <- logika bisnis + integrasi Gemini
│   ├── models.py               <- Profile, Document, ChatMessage, UserActivity
│   ├── forms.py                <- StudyKitForm, RegisterForm
│   ├── signals.py              <- buat Profile otomatis saat User dibuat
│   ├── apps.py                 <- ready() memuat signals
│   ├── admin.py
│   └── migrations\0001_0002
├── templates\
│   ├── base.html               <- layout: sidebar (login) / top navbar (anonim); [x-cloak] CSS
│   ├── registration\login.html <- form email/password Django native
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
| `Profile` | user (OneToOne), learning_style, education_level, grade, language |
| `Document` | user (FK), title, source_type (text/youtube/pdf), source_url, raw_content, education_level, grade, language, ai_output (JSONField: summary, roadmap, flashcards, resources, exam), summary_html |
| `ChatMessage` | document (FK), role (user/assistant), content |
| `UserActivity` | user (FK), active_date (unik per user/hari) — dasar hitung hari streak |

Relasi: `User 1—1 Profile`, `User 1—N Document`, `Document 1—N ChatMessage`, `User 1—N UserActivity`.

---

## 5. Workflow Aplikasi

### 5.1 URL & View (namespaced `core:`)

```
/                               landing_view
/register/                      register_view
/accounts/                      Django auth native (login/logout/password, tanpa OAuth)
/dashboard/                     dashboard_view            (login required; kredit & streak)
/preferences/                   preferences_view          (POST preferensi dari modal)
/library/                       library_view              (daftar materi + paginasi)
/settings/                      settings_view
/process/                       process_content_view      (POST materi -> proses Gemini)
/workspace/<pk>/                workspace_view            (tampilkan paket belajar)
/workspace/<pk>/chat/           chat_api_view             (POST JSON -> jawaban AI)
/workspace/<pk>/summary/        summary_save_api_view     (POST JSON -> simpan edit rangkuman)
/workspace/<pk>/practice/generate/  practice_generate_api_view    (POST -> generate 20 soal)
/workspace/<pk>/delete/         delete_document_view
```

### 5.2 Alur Auth (Django native — tanpa Supabase/OAuth)
- **Register:** `RegisterForm` -> `User.objects.create_user()` + `Profile` (via signal) -> `login()`.
- **Login:** `django.contrib.auth` `LoginView` (email sebagai `username`) -> sesi Django.

### 5.3 Alur Proses Materi (core/services.py: `build_learning_kit`)
1. View menerima input dari `StudyKitForm` (teks / URL YouTube / upload PDF, jumlah flashcard,
   learning_style, **language (bahasa output)**, education_level, grade). Field `num_quiz` sudah DIPINDAHKAN dari form.
2. Ekstrak konten: `extract_youtube_transcript()` (pakai API instance `.list()`; lihat catatan v1.2.4)
   atau `extract_pdf_text()` (pypdf).
3. Simpan `Document` (raw_content + metadata, termasuk `language`).
4. Panggil Gemini sekali untuk membuat `ai_output` berisi:
   `summary` (markdown), `roadmap` (steps), `flashcards`, `resources`.
   `exam` (20 soal pilihan ganda) DIBUAT TERPISAH via `/workspace/<pk>/practice/generate/`.
5. `_parse_json` memastikan output AI valid (fallback struktural jika JSON tidak bersih).

> **Bahasa output:** user memilih bahasa pada form study kit (dropdown "Bahasa output",
> default dari `Profile.language`). Seluruh output AI (rangkuman, roadmap, flashcard,
> resources, latihan soal, dan chat) WAJIB ditulis dalam bahasa tersebut, meskipun materi
> input berbahasa lain (mis. transkrip YouTube berbahasa Inggris → dipilih Bahasa Indonesia).
> Pilihan disimpan di `Document.language` dan dipakai ulang oleh `chat_with_document` dan
> `build_exam`. Pilihan terakhir juga disimpan ke `Profile.language` sebagai default berikutnya.

### 5.4 Chat dengan Dokumen (`chat_with_document`)
- Klik tombol "Tanya AI" (floating) -> panel chat -> POST ke `/workspace/<pk>/chat/`.
- Konteks = `raw_content` dokumen dikirim sebagai bagian dari prompt (tanpa vector store, sesuai AGENTS.md).
- Riwayat `ChatMessage` dirender di panel.
- **Prompt longgar:** materi dipakai sebagai sumber utama/acuan, tetapi AI boleh menjawab
  pertanyaan lanjutan yang relevan (contoh, analogi, pendalaman) meski tidak tertulis eksplisit
  di materi — tidak lagi menolak mentah-mentah jika pertanyaan di luar teks materi.

### 5.9 Status Kartu Belajar (Masih Belajar / Sudah Mahir)
- Setiap flashcard dapat ditandai "Masih Belajar" atau "Sudah Mahir" (mode satu kartu & grid).
- Status disimpan per dokumen di `localStorage` (key `ayok-flashcards-<doc_id>`, pola sama dengan roadmap),
  jadi tidak hilang saat halaman dimuat ulang.
- Ada progress bar mahir, tombol "Belum Mahir" (lompat ke kartu yang belum mahir), dan "Ulangi status semua kartu".
- Logika: `static/core/js/app.js` `flashcardDeck()`; UI: `core/templates/core/workspace.html`.

### 5.5 Export (100% client-side, sesuai AGENTS.md)
- **Markdown:** `Ayok.downloadMarkdown` -> Blob `text/markdown`.
- **Anki CSV:** `Ayok.downloadAnkiCSV` -> Blob CSV ber-BOM UTF-8.
- **Cetak PDF:** `window.print()` + CSS `no-print`.

### 5.10 Admin Panel (Jazzmin)
- `django-jazzmin` 3.0.5, diaktifkan sebelum `django.contrib.admin` di `INSTALLED_APPS`.
- Konfigurasi di `settings.py`: `JAZZMIN_SETTINGS` (brand, ikon Font Awesome per model,
  `search_model=core.document`, `related_modal_active`, `changeform_format=horizontal_tabs`)
  dan `JAZZMIN_UI_TWEAKS` (tema `flatly`, `default_theme_mode=auto` mengikuti
  `prefers-color-scheme`, sidebar `sidebar-dark-primary`, navbar putih).
- Brand teal + font Plus Jakarta Sans + radius lembut via `static/jazzmin/admin.css`
  (didaftarkan lewat `custom_css`). Tombol/link/aksi utama mengikuti `#0D9488` (teal-600).
- `core/admin.py` kini mendaftarkan 5 model (termasuk `UserActivity`) dengan
  `list_display`, `list_filter`, `search_fields`, `date_hierarchy`, dan pratinjau isi AI.

### 5.6 Latihan Soal (`exam`)
- 20 soal pilihan ganda, dibuat AI **sesaat diminta** lewat `/workspace/<pk>/practice/generate/`
  (bukan saat generate materi) — karena itu kredit & proses materi tidak menunggu soal latihan.
- Item soal: `{question, options[4], correctAnswer (int 0-3), explanation}`.
- Pengaturan waktu: 30 menit di client (`app.js` `practiceEngine`); lulus bila skor ≥ 70%.

### 5.7 Kredit & Streak
- **Kredit bulanan:** `FREE_MONTHLY_DOCUMENT_LIMIT` (default 3) dikurangi jumlah dokumen bulan
  berjalan; sisa ditampilkan di dashboard.
- **Streak:** dihitung dari `UserActivity` (hari aktif beruntun), dicatat saat user membuka dashboard.
- Implementasi: `core/models.py` (`UserActivity.streak_for`, `record_if_new`) + `_dashboard_context`.

### 5.8 Loading State
- **Generate materi** (dashboard): overlay progress bar + persentase (palsu/indikasi, karena submit
  full-page POST).
- **Latihan soal** (workspace): skeleton loader menyerupai layout soal.
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
| `DATABASE_URL` | **kosong** di dev (SQLite), isi `mysql://user:password@host:3306/dbname` di produksi (MySQL) |

---

## 7. Perbaikan yang Sudah Dilakukan (jangan regresi)

| # | Masalah | Solusi | File |
|---|---|---|---|
| 1 | Logout error CSRF | Tambah `django.middleware.csrf.CsrfViewMiddleware` ke `MIDDLEWARE` | `settings.py` |
| 2 | Input dashboard tak tampil | Ganti `hidden`/`:class` -> `x-show` + `x-cloak`; tambah CSS `[x-cloak]` | `dashboard.html`, `base.html` |
| 3 | Gemini API 400 (placeholder key) | `load_dotenv(BASE_DIR / '.env')` bukan parent | `settings.py` |
| 4 | Model Gemini tidak ada | `gemini-flash-latest` (bukan `gemini-1.5-flash`) | `.env` |
| 5 | DB config error | `DATABASE_URL` dikosongkan; struktur `DATABASES` if/elif/else + import `sys` | `.env`, `settings.py` |
| 6 | Auth Supabase/OAuth (deprecated) | Dihapus v0.0.3 — ganti Django auth native (MySQL-only, tanpa Supabase) agar deploy VPS/shared hosting simpel | `views.py`, `urls.py`, `supabase_auth.py` (dihapus) |
| 7 | Nav login vs anonim | Sidebar (kiri) untuk login; top navbar untuk anonim | `base.html` |
| 8 | Generate materi error 400 (skema quiz) | `quiz` dihapus dari skema & diganti `exam` (20 soal, generate terpisah); frontend pakai `correctAnswer` | `services.py`, `workspace.html`, `app.js` |
| 9 | Rangkuman tak bisa diedit (format) | Ganti Quill → `contenteditable` + `document.execCommand` (toolbar `.rt-toolbar`), simpan HTML ke `Document.summary_html` | `workspace.html`, `app.js`, `views.py` |
| 10 | "Layanan AI sedang ramai" (429/5xx) | Retry 5× + delay eksponensial + jitter; fallback multi-model (`GEMINI_FALLBACK_MODELS`) | `services.py`, `settings.py` |
| 11 | Model fallback `gemini-2.0-flash` sudah tidak ada (404) | Ganti default ke `gemini-2.5-flash,gemini-2.5-flash-lite`; APIError 404/400 dianggap "model tidak tersedia" → lanjut model berikut | `settings.py`, `services.py` |
| 12 | Statistik dashboard palsu (kredit & streak hardcoded) | Model `UserActivity` + hitung kredit bulanan nyata; tampilkan SVG (bukan emoji) | `models.py`, `views.py`, `dashboard.html` |
| 13 | Aksesibilitas & konsistensi UI | `skip-link`, `focus-visible`, emoji struktural → SVG hemat, copy quiz→latihan soal | `base.html`, semua template |
| 14 | `YouTubeTranscriptApi.list_transcripts` error (API v1.2.4) | Tidak pakai classmethod lama; gunakan **instance** `YouTubeTranscriptApi().list(video_id)` | `services.py` |
| 15 | Status kartu belajar tidak aktif (klik "Sudah Mahir" hilang saat reload) | Persist status per dokumen di `localStorage` (`ayok-flashcards-<doc_id>`); tambah progress bar, badge status, tombol "Belum Mahir" & reset | `app.js`, `workspace.html` |
| 16 | Chat "Tanya AI" terlalu ketat (menolak bila di luar teks materi) | Prompt dilonggarkan: materi tetap sumber utama, tapi AI boleh menjawab yang berkaitan (contoh, analogi, pendalaman) selama sejalan topik | `services.py` |
| 17 | Output AI selalu mengikuti bahasa materi input | Tambah field `language` di `Profile` & `Document`; dropdown "Bahasa output" di form study kit (default `id`); semua prompt AI (kit, latihan, chat) memaksa bahasa output terpilih | `models.py`, `forms.py`, `views.py`, `services.py`, `dashboard.html`, migration `0009` |
| 18 | Dark mode (sebelumnya ditunda) | Toggle tema di sidebar/navbar (localStorage `ayok-theme`, opsi light/dark/system di Settings); layer CSS override `.dark` + `darkMode:'class'`; print paksa terang | `base.html`, `_theme_toggle.html`, `settings.html`, `landing.html`, `workspace.html`, `app.js` |
| 19 | Export terpisah-pisah di header workspace | Gabung jadi dropdown "Export": Rangkuman (.md), Anki CSV, Paket Lengkap (.md), Latihan Soal (.md), Cetak PDF | `workspace.html`, `app.js` (`downloadKit`, `downloadExam`, `exportPanel`) |
| 20 | Admin polos bawaan Django | Integrasi `django-jazzmin` 3.0.5 (tema `flatly` + brand teal `#0D9488`, dark mode `auto`, sidebar `dark-primary`, logo `static/img/ayok-logo.svg`); `core/admin.py` didesain ulang (list/filter/search/date_hierarchy, pratinjau AI, `UserActivity` ikut terdaftar) | `settings.py` (`JAZZMIN_SETTINGS`, `JAZZMIN_UI_TWEAKS`), `static/jazzmin/admin.css`, `static/img/ayok-logo.svg`, `core/admin.py` |

---

## 8. Menjalankan & Verifikasi

```bash
cd C:\yok\ayokbelajar_proj
python manage.py check          # health check
python manage.py migrate        # pastikan migrasi terpasang
python manage.py test core      # 74 unit test — semua PASS
python manage.py runserver      # dev di http://localhost:8000
```

Verifikasi manual setelah perubahan: login, proses materi (3 sumber), buka workspace, export, chat.

---

## 9. Catatan Operasional / Risiko

- `python manage.py collectstatic` hanya untuk produksi; ada warning `staticfiles/` belum ada di dev — wajar.
- **jangan regresi:** jangan kembalikan pemanggilan YouTube ke `YouTubeTranscriptApi.list_transcripts()` —
  API itu dihapus di `youtube-transcript-api` 1.2.4; gunakan instance `.list()`.
 - **Production DB:** MySQL 8.x via `DATABASE_URL` (`mysql://...`) — `mysqlclient==2.2.7` (`requirements.txt`).
 - **Belum dikerjakan:** payment/upgrade paket (harga di landing hanya mock).
- Baca `AGENTS.md` di `C:\yok` untuk aturan koding yang wajib dipatuhi (Django 5.x, minimal perubahan,
  test wajib, no hardcode secret). Pedoman UI: `rules.md` di root proyek.
