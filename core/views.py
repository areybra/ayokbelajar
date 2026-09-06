import json
from random import randint

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ProfilePreferencesForm, RegisterForm, SettingsForm, StudyKitForm
from .models import ChatMessage, Document, PracticeSession, UserActivity
from .services import (
    build_exam,
    build_learning_kit,
    chat_with_document,
    extract_pdf_text,
    extract_youtube_transcript,
)


def landing_view(request):
    return render(request, 'core/landing.html', {
        'demo_question': 'Apa itu Active Recall?',
        'demo_answer': 'Teknik mengingat aktif dengan menguji diri sendiri, bukan sekadar membaca ulang.',
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect(reverse('core:dashboard'))

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        email = data['email'].strip().lower()
        user = User.objects.create_user(
            username=email,
            email=email,
            password=data['password1'],
            first_name=data['full_name'],
        )
        login(request, user)
        messages.success(request, 'Akun berhasil dibuat. Selamat datang di AyokBelajar!')
        return redirect(reverse('core:dashboard'))

    return render(request, 'core/register.html', {'form': form})


def _dashboard_context(request, form=None):
    """Konfigurasi render halaman dashboard (termasuk state modal preferensi)."""
    from django.utils import timezone
    profile = request.user.profile
    today = timezone.now().date()
    UserActivity.record_if_new(request.user, today)
    docs_this_month = request.user.documents.filter(
        created_at__year=today.year,
        created_at__month=today.month,
    ).count()
    return {
        'form': form or StudyKitForm(initial={'language': profile.language}),
        'prefs_form': ProfilePreferencesForm(),
        'documents': request.user.documents.all()[:20],
        'profile': profile,
        'preferences_set': profile.preferences_set,
        'credit_remaining': max(
            settings.FREE_MONTHLY_DOCUMENT_LIMIT - docs_this_month, 0
        ),
        'streak': UserActivity.streak_for(request.user, today=today),
    }


@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html', _dashboard_context(request))


@login_required
@require_POST
def preferences_view(request):
    """Simpan preferensi belajar (jenjang, kelas) dari modal."""
    profile = request.user.profile
    form = ProfilePreferencesForm(request.POST)
    if not form.is_valid():
        return render(request, 'core/dashboard.html', {
            'form': StudyKitForm(),
            'prefs_form': form,
            'documents': request.user.documents.all()[:20],
            'profile': profile,
            'preferences_set': profile.preferences_set,
        })

    data = form.cleaned_data
    profile.education_level = data['education_level']
    profile.grade = data['grade']
    profile.preferences_set = True
    profile.save(update_fields=['education_level', 'grade', 'preferences_set'])
    messages.success(request, 'Preferensi belajarmu berhasil disimpan. Selamat belajar!')
    return redirect(reverse('core:dashboard'))


@login_required
def library_view(request):
    documents = request.user.documents.all()
    paginator = Paginator(documents, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/library.html', {
        'documents': page_obj,
        'page_obj': page_obj,
        'total_count': paginator.count,
    })


@login_required
def settings_view(request):
    profile = request.user.profile
    form = SettingsForm(
        request.POST or None,
        initial={
            'full_name': request.user.first_name,
            'education_level': profile.education_level,
            'grade': profile.grade,
        },
    )
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        request.user.first_name = data['full_name']
        request.user.save(update_fields=['first_name'])
        profile.education_level = data['education_level']
        profile.grade = data['grade']
        profile.save(update_fields=['education_level', 'grade'])
        messages.success(request, 'Pengaturan akun berhasil disimpan.')
        return redirect(reverse('core:settings'))
    return render(request, 'core/settings.html', {'form': form})


@login_required
@require_POST
def process_content_view(request):
    form = StudyKitForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'core/dashboard.html', _dashboard_context(request, form))

    data = form.cleaned_data
    source_type = data['source_type']

    try:
        if source_type == 'youtube':
            raw_content = extract_youtube_transcript(data['youtube_url'])
            title = _youtube_title(data['youtube_url'])
            source_url = data['youtube_url']
        elif source_type == 'pdf':
            raw_content = extract_pdf_text(data['pdf_file'])
            title = data['pdf_file'].name
            source_url = data['pdf_file'].name
        else:
            raw_content = data['raw_text']
            title = _infer_title(raw_content)
            source_url = ''

        if not raw_content.strip():
            raise ValueError('Tidak ada teks yang bisa diekstrak dari sumber ini.')

        # Preferensi jenjang, kelas, dan gaya belajar diambil dari profil user.
        profile = request.user.profile

        # Default jumlah kartu belajar acak 5-10 jika tidak dispecifikasi
        num_flashcards = data.get('num_flashcards') or randint(5, 10)

        language = data.get('language') or profile.language
        ai_output = build_learning_kit(
            raw_content,
            data.get('learning_style') or profile.learning_style,
            profile.education_level,
            profile.grade,
            num_flashcards,
            language,
        )

        document = Document.objects.create(
            user=request.user,
            title=title[:255],
            source_type=source_type,
            source_url=source_url,
            raw_content=raw_content,
            education_level=profile.education_level,
            grade=profile.grade,
            language=language,
            ai_output=ai_output,
        )
        if profile.language != language:
            profile.language = language
            profile.save(update_fields=['language'])
        return redirect(reverse('core:workspace', kwargs={'pk': document.pk}))
    except Exception as exc:  # noqa: BLE001 - tampilkan pesan ramah
        form.add_error(None, f'Gagal memproses materi: {exc}')
        return render(request, 'core/dashboard.html', _dashboard_context(request, form))


@login_required
def workspace_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied
    output = document.ai_output
    practice_sessions = [
        {
            'id': session.pk,
            'title': session.title or f'Sesi #{session.pk}',
            'questions': session.questions,
            'created_label': session.created_at.strftime('%d %b %Y'),
        }
        for session in document.practice_sessions.all()
    ]
    return render(request, 'core/workspace.html', {
        'document': document,
        'summary': output.get('summary', ''),
        'roadmap': output.get('roadmap', []),
        'flashcards': output.get('flashcards', []),
        'resources': output.get('resources') or {},
        'exam': output.get('exam') or [],
        'practice_sessions': practice_sessions,
        'chat_messages': document.chat_messages.all(),
    })

@login_required
@require_POST
def chat_api_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        payload = {}
    message = (payload.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'Pesan tidak boleh kosong.'}, status=400)

    ChatMessage.objects.create(document=document, role='user', content=message)
    history = [
        {'role': m.role, 'content': m.content}
        for m in list(document.chat_messages.all())[-8:]
    ]

    try:
        answer = chat_with_document(
            document.raw_content,
            history,
            document.education_level,
            document.grade,
            document.title,
            document.language,
        )
    except Exception as exc:  # noqa: BLE001
        answer = f'Maaf, terjadi kendala saat menjawab: {exc}'

    ChatMessage.objects.create(document=document, role='assistant', content=answer)
    return JsonResponse({'role': 'assistant', 'content': answer})


@login_required
@require_POST
def summary_save_api_view(request, pk):
    """Simpan hasil edit rangkuman (rich text editor) kembali ke dokumen."""
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        payload = {}
    html = (payload.get('html') or '').strip()
    if not html:
        return JsonResponse({'error': 'Konten rangkuman tidak boleh kosong.'}, status=400)
    if len(html) > 200_000:
        return JsonResponse({'error': 'Konten rangkuman terlalu panjang.'}, status=400)

    document.summary_html = html
    document.save(update_fields=['summary_html'])
    return JsonResponse({'ok': True, 'html': html})


@login_required
@require_POST
def practice_generate_api_view(request, pk):
    """Generate latihan soal baru (20 soal) dari materi dokumen."""
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied

    try:
        questions = build_exam(document.raw_content, document.education_level, document.grade, document.language)
    except Exception as exc:  # noqa: BLE001 - dikembalikan sebagai pesan ramah
        return JsonResponse({'error': str(exc)}, status=400)

    ai_output = dict(document.ai_output or {})
    ai_output['exam'] = questions
    document.ai_output = ai_output
    document.save(update_fields=['ai_output'])
    return JsonResponse({'ok': True, 'exam': questions})


@login_required
@require_POST
def practice_save_api_view(request, pk):
    """Simpan sesi latihan soal (sesi saat ini) untuk dipelajari ulang."""
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        payload = {}
    title = (payload.get('title') or '').strip()[:255]

    questions = (document.ai_output or {}).get('exam') or []
    if not questions:
        return JsonResponse({'error': 'Belum ada soal latihan untuk disimpan.'}, status=400)

    session = PracticeSession.objects.create(
        document=document,
        title=title or f'Sesi #{document.practice_sessions.count() + 1}',
        questions=questions,
    )
    return JsonResponse({
        'ok': True,
        'session': {
            'id': session.pk,
            'title': session.title,
            'created_label': session.created_at.strftime('%d %b %Y'),
        },
    })


@login_required
@require_POST
def practice_delete_api_view(request, pk, session_pk):
    """Hapus satu sesi latihan soal yang tersimpan."""
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied
    session = get_object_or_404(PracticeSession, pk=session_pk, document=document)
    session.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def delete_document_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.user != request.user:
        raise PermissionDenied
    document.delete()
    return redirect(reverse('core:dashboard'))


def _infer_title(text):
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), '')
    return first_line[:100] or 'Materi tanpa judul'


def _youtube_title(url):
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    video_id = params.get('v', [''])[0] or url.rsplit('/', 1)[-1]
    return f'YouTube Video ({video_id})'
