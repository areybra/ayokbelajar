# Rules — UI/UX AyokBelajar

> Hasil diskusi desain (basis: skill `ui-ux-pro-max`). Direktif ini dipakai untuk SEMUA perubahan UI di proyek ini.
> Filosofi utama: **ramah semua kalangan**, **hemat ikon**, **konsisten**, **aksesibel**.

## 1. Design Tokens

### Warna
| Token | Nilai | Pemakaian |
|---|---|---|
| `primary` | `#4F46E5` | Tombol utama, link, judul aksen |
| `primary-hover` | `#4338CA` | Hover tombol utama |
| `accent` | `#10B981` | Sukses, progres, elemen "selesai" |
| `danger` | `#F43F5E` | Hapus, kesalahan |
| `surface` | `#FFFFFF` | Kartu, panel |
| `bg-page` | `#F8FAFC` (`slate-50`) | Latar halaman |
| `text-strong` | `#0F172A` (`slate-900`) | Judul |
| `text-body` | `#334155` (`slate-700`) | Paragraf |
| `text-muted` | `#64748B` (`slate-500`) | Teks sekunder (min, jangan `slate-400` untuk teks penting) |
| `border-soft` | `#E2E8F0` (`slate-200`) | Border kartu/divider |

Aturan: teks konten **minimal `slate-500`** untuk sekunder dan `slate-700` untuk body (kontras ≥ 4.5:1). `slate-400` hanya untuk hint/dekorasi tipis.

### Tipografi
- Font: **Inter** (sudah dimuat via Google Fonts).
- Skala: h1 `text-2xl/3xl` bold, h2 `text-xl` bold, h3 `text-lg` semibold.
- Judul kartu: `text-lg font-bold text-slate-900`.
- Body: `text-sm` (UI) / `text-base` (prosa panjang).

### Radius & Shadow
- Kartu: `rounded-xl` + `border border-slate-200` + `shadow-sm`.
- Tombol: `rounded-lg`.
- Input: `rounded-lg` + `border border-slate-300`.
- Hover kartu: `transition-colors duration-200` — tanpa lompatan layout (jangan ubah ukuran saat hover).

### Spacing (ritme 4/8)
- Pemisah antar-bagian: `space-y-6` / `space-y-10`.
- Padding kartu: `p-5` / `p-6`.
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
- State: hover `duration-200`; press tetap stabil (tidak memindahkan layout); disabled `disabled:cursor-not-allowed disabled:opacity-50`.
- Tombol utama: `bg-primary text-white hover:bg-primary-hover shadow-sm`.
- Tombol sekunder: `border border-slate-300 bg-white text-slate-700 hover:border-slate-400`.
- Input focus: `focus:border-primary focus:outline-none focus:ring-2 focus:ring-indigo-500`.
- Setiap tombol/aksi punya `<button type="button">` bila bukan submit nyata.

## 4. Loading & Feedback
- Operasi async (>300ms) WAJIB menampilkan feedback.
- **Generate materi besar** (dashboard): progress bar + persentase sebagai indikator kemajuan.
- **Konten tak tahu lama** (ujian): **skeleton loader** menyerupai bentuk asli.
- Micro-interaction 150–300ms; hormati `prefers-reduced-motion`.
- Status sukses/error: hijau `accent` / merah `danger`, teks jelas.

## 5. Bahasa
- Semua UI **Bahasa Indonesia** (kecuali istilah teknis umum).
- Konsisten: "latihan soal" (bukan quiz), "rangkuman" (bukan ringkasan), "peta belajar", "sumber belajar".
- Hindari bahasa Inggris di heading jika Indonesia sudah natural.
- Tidak menyebut versi model AI konkret di UI bila rawan kedaluwarsa.

## 6. Layout
- Halaman app: sidebar kiri (desktop) + topbar hijau mobile; konten utama `space-y-6`.
- Tab yang panjang/scrollable perlu sticky agar konteks tetap terlihat.
- Empty state: pesan + CTA, bukan teks telanjang.
- Prosa panjang: pakai `.summary-prose` (sudah ada) — jangan buat gaya baru.

## 7. Accessibility
- Skip-link "Langsung ke konten" di awal `body`.
- Heading berjenjang (h1 → h2 → h3, tanpa lompat).
- Focus ring terlihat untuk semua elemen interaktif (via keyboard).
- Kontras teks ≥ 4.5:1 (lihat §1).
- `prefers-reduced-motion: reduce` tetap dihormati (sudah di `base.html`).
- Ikon dekoratif `aria-hidden`; tombol ikon tanpa teks wajib `aria-label`.

## 8. Checklist Wajib (lulus sebelum dianggap selesai)
1. Tidak ada emoji sebagai ikon struktural.
2. Ikon hanya di tempat penting & SVG konsisten.
3. Semua elemen klik punya `cursor-pointer`.
4. Hover/disabled/focus state jelas.
5. Kontras teks minimal `slate-500` untuk sekunder.
6. Loading state sesuai §4.
7. Bahasa Indonesia konsisten di seluruh UI baru.
8. `python manage.py test core` hijau.