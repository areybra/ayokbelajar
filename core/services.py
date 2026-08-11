"""Service layer untuk AyokBelajar.

Menangani ekstraksi konten (YouTube/PDF) dan integrasi Google Gemini
dalam satu panggilan AI terstruktur untuk menghasilkan learning kit.
"""
import json
import re
import time

from django.conf import settings
from google import genai
from google.genai.errors import APIError
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2
RETRY_MAX_DELAY = 10

FRIENDLY_UNAVAILABLE_MSG = (
    'Layanan AI sedang sibuk (ramai digunakan). '
    'Silakan coba lagi dalam beberapa saat.'
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
        'quiz': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'question': {'type': 'string'},
                    'options': {'type': 'array', 'items': {'type': 'string'}},
                    'correctAnswer': {'type': 'integer'},
                    'explanation': {'type': 'string'},
                },
                'required': ['question', 'options', 'correctAnswer', 'explanation'],
            },
        },
    },
    'required': ['summary', 'roadmap', 'flashcards', 'quiz'],
}


def _get_client():
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def _get_model():
    return getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')


def _call_with_retry(fn, *args, **kwargs):
    """Panggil Gemini dengan retry/backoff untuk error sementara (429/5xx)."""
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
            time.sleep(delay)
            delay = min(delay * 2, RETRY_MAX_DELAY)
    raise last_error


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_youtube_transcript(url):
    """Ekstrak transkrip teks dari URL YouTube."""
    video_id = _parse_youtube_id(url)
    if not video_id:
        raise ValueError('URL YouTube tidak valid. Gunakan format watch?v= atau youtu.be/.')

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    try:
        transcript = transcript_list.find_transcript(['id'])
    except Exception:
        transcript = transcript_list.find_generated_transcript()
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


def build_learning_kit(raw_content, learning_style, education_level, grade, num_flashcards, num_quiz):
    """Satu panggilan Gemini menghasilkan summary, roadmap, flashcards, quiz."""
    style_prompt = LEARNING_STYLES.get(learning_style, LEARNING_STYLES['detailed'])
    level_prompt = EDUCATION_LEVELS.get(education_level, EDUCATION_LEVELS['umum'])
    grade_label = f' ({grade})' if grade else ''
    prompt = f"""
Kamu adalah asisten pembelajaran AI bernama AyokBelajar.

Berdasarkan materi di bawah, buat "learning kit" lengkap dengan struktur berikut:
1. summary: rangkuman materi dalam format Markdown (beri heading, poin-poin penting, dan glossary istilah).
2. roadmap: peta belajar bertahap (3-6 langkah) berupa array objek {{step, title, detail}}.
3. flashcards: array objek {{question, answer}} sebanyak {num_flashcards} kartu.
4. quiz: array objek {{question, options (4 pilihan), correctAnswer (index 0-3), explanation}} sebanyak {num_quiz} soal.

Target audiens: {education_level}{grade_label}
{level_prompt}
Gaya belajar: {style_prompt}
Gunakan bahasa yang sama dengan materi input.
Pastikan seluruh output valid sebagai JSON murni tanpa teks lain.

MATERI:
{raw_content[:200000]}
"""
    model = _get_model()
    client = _get_client()
    response = _call_with_retry(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type='application/json',
            response_schema=LEARNING_KIT_SCHEMA,
        ),
    )
    return _parse_json(response.text)


def chat_with_document(raw_content, history, education_level='umum', grade=''):
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
    system_context = (
        'Kamu adalah asisten yang menjawab pertanyaan HANYA berdasarkan materi '
        'berikut. Jika pertanyaan di luar materi, katakan tidak tersedia di materi.\n\n'
        f'Target audiens: {education_level}{grade_label}. {level_prompt}\n\n'
        f'MATERI:\n{raw_content[:200000]}'
    )

    model = _get_model()
    client = _get_client()
    chat = _call_with_retry(client.chats.create, model=model, history=conversation)
    response = _call_with_retry(
        chat.send_message, system_context + '\n\nJawab pertanyaan terakhir dari user.'
    )
    return response.text


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
