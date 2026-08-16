"""Service layer untuk AyokBelajar.

Menangani ekstraksi konten (YouTube/PDF) dan integrasi Google Gemini
dalam satu panggilan AI terstruktur untuk menghasilkan learning kit.
"""
import json
import re
import time
from typing import Literal

from pydantic import BaseModel
from django.conf import settings
from google import genai
from google.genai.errors import APIError
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
RETRY_BASE_DELAY = 3
RETRY_MAX_DELAY = 30

FRIENDLY_UNAVAILABLE_MSG = (
    'Layanan AI sedang sibuk (ramai digunakan) dan belum berhasil '
    'meskipun sudah dicoba berkali-kali. Silakan tunggu 1-2 menit lalu '
    'klik "Generate" sekali lagi.'
)

LEARNING_STYLES = {
    'visual': (
        'Fokus pada struktur poin-poin hierarki, peta konsep, dan daftar yang '
        'mudah discan secara visual.'
    ),
    'eli5': (
        'Gunakan bahasa sederhana, analogi nyata sehari-hari, dan hindari '
        'istilah teknis yang berlebihan.'
    ),
    'detailed': (
        'Berikan analisis komprehensif, akademis, dan mendalam sesuai materi.'
    ),
    'socratic': (
        'Rangkuman yang memicu pertanyaan kritis dan mendorong pemikiran mendalam.'
    ),
}

EDUCATION_LEVELS = {
    'sd': (
        'Jenjang SD: gunakan bahasa yang sangat sederhana, kalimat pendek, '
        'contoh dari kehidupan sehari-hari, dan hindari istilah yang rumit.'
    ),
    'smp': (
        'Jenjang SMP: gunakan bahasa yang jelas dan mudah dipahami, beri '
        'penjelasan bertahap, dan contoh yang relevan untuk usia remaja.'
    ),
    'sma': (
        'Jenjang SMA: gunakan bahasa yang lebih formal, beri kedalaman '
        'konsep, contoh aplikasi, dan tingkat kesulitan soal menengah.'
    ),
    'pt': (
        'Jenjang Perguruan Tinggi: gunakan bahasa akademis, analisis '
        'mendalam, terminologi ilmiah, dan tingkat kesulitan soal lanjutan.'
    ),
    'umum': (
        'Jenjang umum: sesuaikan bahasa dan kedalaman dengan materi, '
        'tetap mudah dipahami khalayak luas.'
    ),
}

LEARNING_KIT_SCHEMA = {
    'type': 'object',
    'properties': {
        'summary': {
            'type': 'string',
            'description': 'Rangkuman materi dalam format Markdown.',
        },
        'roadmap': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'step': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'detail': {'type': 'string'},
                },
                'required': ['step', 'title', 'detail'],
            },
        },
        'flashcards': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'question': {'type': 'string'},
                    'answer': {'type': 'string'},
                },
                'required': ['question', 'answer'],
            },
        },
        'resources': {
            'type': 'object',
            'properties': {
                'books': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string'},
                            'note': {'type': 'string'},
                        },
                        'required': ['title'],
                    },
                },
                'articles': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string'},
                            'note': {'type': 'string'},
                        },
                        'required': ['title'],
                    },
                },
                'search_query': {'type': 'string'},
            },
            'required': ['books', 'articles', 'search_query'],
        },
    },
    'required': ['summary', 'roadmap', 'flashcards', 'resources'],
}

def _get_client():
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def _get_models():
    """Daftar model Gemini untuk dicoba berurutan (utamakan yang dikonfigurasi)."""
    primary = getattr(settings, 'GEMINI_MODEL', 'gemini-flash-latest')
    fallback = list(getattr(settings, 'GEMINI_FALLBACK_MODELS', []) or [])
    models = [primary] + [m for m in fallback if m and m != primary]
    return models or ['gemini-flash-latest']


def _call_with_retry(fn, *args, **kwargs):
    """Panggil Gemini dengan retry/backoff + jitter untuk error sementara (429/5xx)."""
    import random
    last_error = None
    delay = RETRY_BASE_DELAY
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except APIError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_STATUS_CODES:
                raise
            if attempt == MAX_RETRIES - 1:
                raise ValueError(FRIENDLY_UNAVAILABLE_MSG)
            time.sleep(delay * (0.5 + random.random()))
            delay = min(delay * 2, RETRY_MAX_DELAY)
    raise last_error


def _generate_with_failover(fn, *args, **kwargs):
    """Coba beberapa model berurutan; lanjut ke model berikut jika yang aktif sibuk."""
    errors = []
    for model in _get_models():
        try:
            return _call_with_retry(fn, *args, model=model, **kwargs)
        except (ValueError, APIError) as exc:
            errors.append(f'{model}: {exc}')
            if isinstance(exc, APIError) and exc.code not in RETRYABLE_STATUS_CODES:
                # 404 / 400 = model tidak tersedia/valid -> coba model berikutnya
                continue
            if isinstance(exc, ValueError):
                continue
    raise ValueError(FRIENDLY_UNAVAILABLE_MSG)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_youtube_transcript(url):
    """Ekstrak transkrip teks dari URL YouTube."""
    video_id = _parse_youtube_id(url)
    if not video_id:
        raise ValueError('URL YouTube tidak valid. Gunakan format watch?v= atau youtu.be/.')

    transcript_list = YouTubeTranscriptApi().list(video_id)
    try:
        transcript = transcript_list.find_transcript(['id', 'en'])
    except Exception:
        transcript = transcript_list.find_generated_transcript(['id', 'en'])
    parts = [item.text for item in transcript.fetch()]
    return ' '.join(parts)


def _parse_youtube_id(url):
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([A-Za-z0-9_-]{11})',
        r'(?:shorts/)([A-Za-z0-9_-]{11})',
        r'(?:embed/)([A-Za-z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_pdf_text(pdf_file):
    """Ekstrak teks dari file PDF yang diupload."""
    reader = PdfReader(pdf_file)
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ''
        parts.append(text.strip())
    return '\n'.join(parts)


def build_learning_kit(raw_content, learning_style, education_level, grade, num_flashcards):
    """Satu panggilan Gemini menghasilkan summary, roadmap, flashcards, resources."""
    style_prompt = LEARNING_STYLES.get(learning_style, LEARNING_STYLES['detailed'])
    level_prompt = EDUCATION_LEVELS.get(education_level, EDUCATION_LEVELS['umum'])
    grade_label = f' ({grade})' if grade else ''
    prompt = f"""
Kamu adalah asisten pembelajaran AI bernama AyokBelajar.

Berdasarkan materi di bawah, buat "learning kit" lengkap dengan struktur berikut:
1. summary: rangkuman materi yang LENGKAP, PADAT, dan MENDALAM dalam format Markdown. JANGAN membuat rangkuman singkat/superficial. Uraikan secara rinci namun tidak bertele-tele.
   JANGAN mengikuti kerangka baku yang sama untuk semua topik (mis. tidak wajib memuat "Pendahuluan → Teori inti → Permasalahan → Proses → Kesimpulan → Glosarium"). Susun rangkuman secara ALAMI seperti catatan belajar yang hidup, mengikuti alur logis materi itu sendiri, dan bervariasi antar topik. Definisi, istilah, prinsip, rumus, proses, contoh penerapan, serta penutup dihadirkan di tempat yang paling natural sesuai alur pembahasan — bukan sebagai daftar bagian template yang kaku dan berulang.
   Tetap gunakan heading & sub-heading bila benar-benar membantu mengelompokkan konsep, dengan susunan yang RAPI, mudah dibaca, dan enak diikuti — sekaligus tidak terasa monoton seperti dokumen template/cetakan. Hindari kesan "jawaban kuis/AI"; tulislah seperti rangkuman yang menuntun pembaca memahami konsep secara berurutan.
2. roadmap: peta belajar bertahap (3-6 langkah) berupa array objek {{step, title, detail}}.
3. flashcards: array objek {{question, answer}} sebanyak {num_flashcards} kartu.
4. resources: objek {{books: [{{title, note}}], articles: [{{title, note}}], search_query}} berisi:
   - 4 rekomendasi buku yang benar-benar relevan dengan topik,
   - 4 rekomendasi artikel/web yang relevan,
   - search_query: satu kalimat kunci pencarian yang efektif untuk menemukan materi lanjutan.
   Catatan: JANGAN membuat URL asli; cukup judul sumber daya dan catatan singkat (satu kalimat) mengapa berguna.
   Catatan tambahan tentang mind map: Jika menghasilkan diagram mermaid, HANYA keluarkan syntax Mermaid dalam format kotak putih murni tanpa tambahan markdown code block (``` mermaid ... ```), tanpa label judul tambahan, hanya blok mermaid saja.

Target audiens: {education_level}{grade_label}
{level_prompt}
Gaya belajar: {style_prompt}
Gunakan bahasa yang sama dengan materi input.
Pastikan seluruh output valid sebagai JSON murni tanpa teks lain.

MATERIAL:
{raw_content[:200000]}
"""
    client = _get_client()
    response = _generate_with_failover(
        client.models.generate_content,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type='application/json',
            response_schema=LEARNING_KIT_SCHEMA,
        ),
    )
    return _parse_json(response.text)


def chat_with_document(raw_content, history, education_level='umum', grade='', document_title=''):
    """Jawab pertanyaan dengan raw_content sebagai konteks (Zero-RAG)."""
    conversation = []
    for message in history:
        content = message.get('content', '')
        if not content:
            continue
        role = 'model' if message.get('role') == 'assistant' else 'user'
        conversation.append({'role': role, 'parts': [{'text': content}]})

    grade_label = f' kelas {grade}' if grade else ''
    level_prompt = EDUCATION_LEVELS.get(education_level, EDUCATION_LEVELS['umum'])
    title_label = f'Judul dokumen: {document_title}\n\n' if document_title else ''
    system_context = (
        'Kamu adalah asisten yang menjawab pertanyaan HANYA berdasarkan materi '
        'berikut. Jika pertanyaan di luar materi, katakan tidak tersedia di materi.\n\n'
        f'{title_label}'
        f'Target audiens: {education_level}{grade_label}. {level_prompt}\n\n'
        f'MATERI:\n{raw_content[:200000]}'
    )

    client = _get_client()
    last_error = None
    for model in _get_models():
        try:
            chat = _call_with_retry(client.chats.create, model=model, history=conversation)
            response = _call_with_retry(
                chat.send_message,
                system_context + '\n\nJawab pertanyaan terakhir dari user.',
            )
            return response.text
        except (ValueError, APIError) as exc:
            last_error = exc
            if isinstance(exc, APIError) and exc.code not in RETRYABLE_STATUS_CODES:
                # 404 / 400 = model tidak tersedia/valid -> coba model berikutnya
                continue
    if isinstance(last_error, ValueError):
        raise last_error
    raise ValueError(FRIENDLY_UNAVAILABLE_MSG)


def _parse_json(text):
    """Parse JSON dari respons Gemini dengan fallback pembersihan."""
    if not text:
        raise ValueError('Respons AI kosong.')
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError('Respons AI bukan JSON yang valid.')


def _validate_exam_item(item):
    """Validasi satu soal latihan (multiple_choice saja)."""
    options = item.get('options')
    if not options or len(options) != 4:
        raise ValueError('Soal latihan harus memiliki 4 opsi jawaban.')
    ca = item.get('correctAnswer')
    if not isinstance(ca, int) or ca < 0 or ca > 3:
        raise ValueError('correctAnswer multiple choice harus index 0-3')
    if not item.get('question'):
        raise ValueError('Soal latihan harus memiliki pertanyaan.')
    if not item.get('explanation'):
        raise ValueError('Setiap soal harus memiliki explanation')


EXAM_TOTAL_QUESTIONS = 20


def build_exam(raw_content, education_level='umum', grade=''):
    """Hasilkan latihan soal persis 20 soal pilihan ganda (timer & skor di client)."""
    level_prompt = EDUCATION_LEVELS.get(education_level, EDUCATION_LEVELS['umum'])
    grade_label = f' ({grade})' if grade else ''
    prompt = f"""
Kamu adalah penyusun soal latihan bernama AyokBelajar.

Berdasarkan materi di bawah, buat latihan soal PERSIS {EXAM_TOTAL_QUESTIONS} soal pilihan ganda (multiple_choice). Berikut format output JSON valid:
{{
  "exam": [
    {{"question_type": "multiple_choice", "question", "options" (4 pilihan A-D), "correctAnswer" (index 0-3), "explanation"}}
  ]
}}

Aturan penyusunan:
- Total tepat {EXAM_TOTAL_QUESTIONS} soal pilihan ganda.
- Setiap soal punya options TEPAT 4 opsi (A-D) dan correctAnswer berupa index 0-3.
- Tingkat kesulitan bervariasi: mudah, sedang, sulit (proporsi ~ 4:10:6).
- Soal menguji pemahaman konsep, bukan sekadar hafalan kalimat materi.
- Setiap soal hanya boleh punya SATU jawaban benar yang jelas.
- explanation berisi alasan singkat mengapa jawaban tersebut benar.
- Target audiens: {education_level}{grade_label}
{level_prompt}
Gunakan bahasa yang sama dengan materi input.
Pastikan seluruh output valid sebagai JSON murni tanpa teks lain.

MATERIAL:
{raw_content[:200000]}
"""
    client = _get_client()
    response = _generate_with_failover(
        client.models.generate_content,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type='application/json',
            response_schema={
                'type': 'object',
                'properties': {
                    'exam': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'question_type': {
                                    'type': 'string',
                                    'enum': ['multiple_choice'],
                                },
                                'question': {'type': 'string'},
                                'options': {'type': 'array', 'items': {'type': 'string'}},
                                'correctAnswer': {'type': 'integer'},
                                'explanation': {'type': 'string'},
                            },
                            'required': ['question_type', 'question', 'options', 'correctAnswer', 'explanation'],
                        },
                    },
                },
                'required': ['exam'],
            },
        ),
    )
    data = _parse_json(response.text)
    questions = data.get('exam') or data.get('quiz') or []
    for item in questions:
        _validate_exam_item(item)
    if len(questions) > EXAM_TOTAL_QUESTIONS:
        questions = questions[:EXAM_TOTAL_QUESTIONS]
    if len(questions) < EXAM_TOTAL_QUESTIONS:
        raise ValueError(
            f'Latihan soal membutuhkan tepat {EXAM_TOTAL_QUESTIONS} soal, '
            f'tetapi AI hanya menghasilkan {len(questions)}. Silakan coba generate lagi.'
        )
    for item in questions:
        item['question_type'] = 'multiple_choice'
    return questions
