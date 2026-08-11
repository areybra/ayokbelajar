import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import supabase_auth
from .forms import ProfilePreferencesForm, RegisterForm, SettingsForm, StudyKitForm
from .models import ChatMessage, Document
from .services import (
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
        if supabase_auth.is_configured():
            try:
                supabase_auth.sign_up(email, data['password1'], data['full_name'])
            except Exception as exc:  # noqa: BLE001 - akun lokal tetap dibuat
                messages.warning(request, f'Akun lokal dibuat, tapi sinkron ke Supabase gagal: {exc}')
        login(request, user)
        messages.success(request, 'Akun berhasil dibuat. Selamat datang di AyokBelajar!')
        return redirect(reverse('core:dashboard'))

    return render(request, 'core/register.html', {'form': form})


def oauth_login_view(request, provider):
    if provider not in supabase_auth.SUPPORTED_PROVIDERS:
        raise Http404
    if not supabase_auth.is_configured():
        messages.error(request, 'Login dengan Google/GitHub belum dikonfigurasi.')
        return redirect('login')

    redirect_to = request.build_absolute_uri(reverse('core:oauth_callback'))
    try:
        url, code_verifier = supabase_auth.authorize_url(provider, redirect_to)
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f'Gagal menyiapkan login: {exc}')
        return redirect('login')

    request.session['oauth_code_verifier'] = code_verifier
    return redirect(url)


def oauth_callback_view(request):
    code = request.GET.get('code', '')
    code_verifier = request.session.pop('oauth_code_verifier', '')
    if not code or not code_verifier:
        messages.error(request, 'Proses login sosial gagal atau kedaluwarsa. Silakan coba lagi.')
        return redirect('login')

    try:
        data = supabase_auth.exchange_code(code, code_verifier)
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f'Verifikasi login sosial gagal: {exc}')
        return redirect('login')

    user_info = data.get('user', {})
    email = (user_info.get('email') or '').strip().lower()
    if not email:
        messages.error(request, 'Email tidak tersedia pada akun sosial. Coba metode lain.')
        return redirect('login')

    metadata = user_info.get('user_metadata') or {}
    full_name = metadata.get('full_name') or metadata.get('name') or email.split('@')[0]

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email, 'first_name': full_name},
    )
    if created:
        user.set_unusable_password()
        user.save()
    login(request, user)
    messages.success(request, 'Berhasil masuk melalui akun sosial!')
    return redirect(reverse('core:dashboard'))


def _dashboard_context(request, form=None):
    """Konfigurasi render halaman dashboard (termasuk state modal preferensi)."""
    profile = request.user.profile
    return {
        'form': form or StudyKitForm(),
        'prefs_form': ProfilePreferencesForm(),
        'documents': request.user.documents.all()[:20],
        'profile': profile,
        'preferences_set': profile.preferences_set,
    }


@login_required
def dashboard_view(request):
    return render(request, 'core/dashboard.html', _dashboard_context(request))


@login_required
@require_POST
def preferences_view(request):
    """Simpan preferensi belajar (jenjang, kelas, gaya belajar) dari modal."""
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
    profile.learning_style = data['learning_style']
    profile.education_level = data['education_level']
    profile.grade = data['grade']
    profile.preferences_set = True
    profile.save(update_fields=['learning_style', 'education_level', 'grade', 'preferences_set'])
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
            'learning_style': profile.learning_style,
            'education_level': profile.education_level,
            'grade': profile.grade,
        },
    )
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        request.user.first_name = data['full_name']
        request.user.save(update_fields=['first_name'])
        profile.learning_style = data['learning_style']
        profile.education_level = data['education_level']
        profile.grade = data['grade']
        profile.save(update_fields=['learning_style', 'education_level', 'grade'])
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

        ai_output = build_learning_kit(
            raw_content,
            profile.learning_style,
            profile.education_level,
            profile.grade,
            data['num_flashcards'],
            data['num_quiz'],
        )

        document = Document.objects.create(
            user=request.user,
            title=title[:255],
            source_type=source_type,
            source_url=source_url,
            raw_content=raw_content,
            education_level=profile.education_level,
            grade=profile.grade,
            ai_output=ai_output,
        )
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
    return render(request, 'core/workspace.html', {
        'document': document,
        'summary': output.get('summary', ''),
        'roadmap': output.get('roadmap', []),
        'flashcards': output.get('flashcards', []),
        'quiz': output.get('quiz', []),
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
        )
    except Exception as exc:  # noqa: BLE001
        answer = f'Maaf, terjadi kendala saat menjawab: {exc}'

    ChatMessage.objects.create(document=document, role='assistant', content=answer)
    return JsonResponse({'role': 'assistant', 'content': answer})


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
