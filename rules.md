# Rules — UI/UX AyokBelajar

> Hasil diskusi desain (basis: skill `ui-ux-pro-max`). Direktif ini dipakai untuk SEMUA perubahan UI di proyek ini.
> Filosofi utama: **ramah semua kalangan**, **hemat ikon**, **konsisten**, **aksesibel**, **clean & tidak kaku** (flat/balanced polish).

## 1. Design Tokens

### Warna
| Token | Nilai | Pemakaian |
|---|---|---|
| `primary` | `#0D9488` (teal-600) | Tombol utama, link, judul aksen, tab aktif |
| `primary-hover` | `#0F766E` (teal-700) | Hover tombol utama |
| `accent` | `#10B981` | Sukses, progres, elemen "selesai" |
| `danger` | `#F43F5E` | Hapus, kesalahan |
| `surface` | `#FFFFFF` | Kartu, panel |
| `bg-page` | `teal-50/60` | Latar halaman (tint teal lembut) |
| `text-strong` | `#0F172A` (`slate-900`) | Judul |
| `text-body` | `#334155` (`slate-700`) | Paragraf |
| `text-muted` | `#64748B` (`slate-500`) | Teks sekunder (min, jangan `slate-400` untuk teks penting) |
| `border-soft` | `#E2E8F0` (`slate-200`) / `teal-100` | Border kartu/divider |

Aturan: teks konten **minimal `slate-500`** untuk sekunder dan `slate-700` untuk body (kontras ≥ 4.5:1). `slate-400` hanya untuk hint/dekorasi tipis.

> **Jangan pakai kelas `indigo-*`.** Semua aksen biru-indigo yang lama diganti teal (mis. `bg-indigo-50` → `bg-teal-50`, `text-indigo-700` → `text-teal-700`, `focus:ring-indigo-500` → `focus:ring-teal-500/30`). Sukses tetap `emerald-*`, hapus/error tetap `rose-*`.

### Tipografi
- Font: **Plus Jakarta Sans** (sudah dimuat via Google Fonts; ganti dari Inter).
- Skala: h1 `text-2xl/3xl` bold `tracking-tight`, h2 `text-xl` bold, h3 `text-lg` semibold.
- Judul kartu: `text-lg font-bold text-slate-900`.
- Body: `text-sm` (UI) / `text-base` (prosa panjang).
- Angka statistik/timer: pakai **`tabular-nums`** agar ritme sejajar.

### Radius & Shadow
- Kartu: **`rounded-2xl`** + `border border-slate-200/70` + `shadow-sm` (ringan).
- Kartu interaktif (library/dashboard): hover `hover:-translate-y-1` + `hover:shadow-lg hover:shadow-teal-100/40` — tanpa lompatan layout.
- Tombol utama: `rounded-xl` + `shadow-md`, hover `hover:bg-primary-hover`, press `active:scale-[0.98]`.
- Input/select: `rounded-xl` + `border border-slate-200`; focus `focus:ring-2 focus:ring-teal-500/30`.
- Auth/landing surfaces: `rounded-2xl` + `shadow-xl shadow-teal-100/30`.

### Spacing (ritme 4/8)
- Pemisah antar-bagian: `space-y-8` / `space-y-10` / `space-y-12`.
- Padding kartu: `p-5` / `p-6` / `p-8` (hero/auth).
- Gap kartu grid: `gap-5`.
- Touch target: **minimal `min-h-[44px]`** untuk tombol/aksi tappable.

## 2. Iconography — HEMAT Ikon
- **Jangan menambah ikon di semua tempat.** Ikon hanya untuk elemen yang benar-benar butuh pengenalan mental cepat: status/aksi utama, sumber materi, tombol CTA utama, mode belajar.
- **DILARANG emoji sebagai ikon struktural** (navigasi, tombol, heading, status). Emoji tidak konsisten antar-perangkat.
- Gunakan **SVG inline** (gaya Heroicons, `stroke-width="1.8"` konsisten, `fill="none"`).
- Ukuran token ikon: kecil `h-4 w-4`, standar `h-5 w-5`, besar `h-6 w-6`. Satu halaman memakai ukuran konsisten per tingkat.
- Semua ikon dekoratif wajib `aria-hidden="true"`.
- Jika ragu ikon membantu: **jangan pakai**. Teks lebih jelas & ramah semua kalangan.

## 3. Tombol & Input
- Semua elemen klik = `cursor-pointer`.
- State: hover `duration-200`; press tetap stabil (`active:scale-[0.98]`, bukan ubah ukuran penuh); disabled `disabled:cursor-not-allowed disabled:opacity-50`.
- Tombol utama: `bg-primary text-white hover:bg-primary-hover shadow-md`.
- Tombol sekunder: `border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50`.
- Setiap tombol/aksi punya `<button type="button">` bila bukan submit nyata.

## 4. Loading & Feedback
- Operasi async (>300ms) WAJIB menampilkan feedback.
- **Generate materi besar** (dashboard): progress bar + persentase sebagai indikator kemajuan.
- **Konten tak tahu lama** (ujian): **skeleton loader** menyerupai bentuk asli.
- **Chat AI**: bubble "mengetik" dengan **3 titik pulse** (`.typing-dot`) selama menunggu jawaban.
- Micro-interaction 150–300ms; hormati `prefers-reduced-motion`.

## 5. Bahasa
- Semua UI **Bahasa Indonesia** (kecuali istilah teknis umum).
- Konsisten: "latihan soal" (bukan quiz), "rangkuman" (bukan ringkasan), "peta belajar", "sumber belajar".
- Hindari bahasa Inggris di heading jika Indonesia sudah natural.
- Tidak menyebut versi model AI konkret di UI bila rawan kedaluwarsa.

## 6. Layout
- Halaman app: sidebar kiri (desktop) + topbar mobile; konten utama `max-w-6xl` + `space-y-8` (tidak melar ke layar sangat lebar).
- **Anti-kaku:** hindari semua elemen berkotak seragam. Gunakan whitespace lega, kartu ringan (border halus, bukan shadow tebal), separator lewat tint latar, dan hierarki via tipografi.
- Tab yang panjang/scrollable perlu sticky agar konteks tetap terlihat.
- Empty state: ikon + pesan + CTA, bukan teks telanjang.
- Prosa panjang: pakai `.summary-prose` (sudah ada) — jangan buat gaya baru.

## 7. Motion (anti-kaku, tetap hormati reduced-motion)
- **1–2 elemen fokus per tampilan**; jangan animasi semua yang bergerak.
- Durasi micro-interaction **150–300ms**, `ease-out` saat masuk, `ease-in` saat keluar; hanya `transform`/`opacity` (tanpa layout shift).
- Hover lift kecil (1–4px); animasi tak berujung **hanya** untuk indikator loading (skeleton, typing dots, progress bar).
- Scroll reveal: elemen berkelas `.reveal` muncul saat masuk viewport (IntersectionObserver di `app.js`), offset 8–12px, stagger ≤ 0.04s. Selalu ada fallback konten terlihat saat JS/reduced-motion.
- Dilarang: `animate-bounce` dekoratif, durasi > 500ms untuk UI, easing linear, animasi yang mengubah layout (width/height/margin).

## 8. Accessibility
- Skip-link "Langsung ke konten" di awal `body`.
- Heading berjenjang (h1 → h2 → h3, tanpa lompat).
- Focus ring terlihat untuk semua elemen interaktif (via keyboard).
- Kontras teks ≥ 4.5:1 (lihat §1).
- `prefers-reduced-motion: reduce` tetap dihormati (sudah di `base.html`).
- Ikon dekoratif `aria-hidden`; tombol ikon tanpa teks wajib `aria-label`.

## 9. Checklist Wajib (lulus sebelum dianggap selesai)
1. Tidak ada emoji sebagai ikon struktural.
2. Ikon hanya di tempat penting & SVG konsisten.
3. Semua elemen klik punya `cursor-pointer`.
4. Hover/disabled/focus state jelas.
5. Tidak ada kelas `indigo-*`; aksen teal konsisten.
6. Kontras teks minimal `slate-500` untuk sekunder.
7. Loading state sesuai §4.
8. Motion mematuhi §7 (tanpa layout shift, hormati reduced-motion).
9. Bahasa Indonesia konsisten di seluruh UI baru.
10. `python manage.py test core` hijau.
