import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from google.genai.errors import APIError

from .models import ChatMessage, Document, Profile
from .services import (
    FRIENDLY_UNAVAILABLE_MSG,
    _call_with_retry,
    _parse_json,
    _parse_youtube_id,
    build_learning_kit,
    chat_with_document,
)

KIT_FIXTURE = {
    'summary': '# Ringkasan',
    'roadmap': [{'step': 1, 'title': 'Mulai', 'detail': 'Definisi'}],
    'flashcards': [{'question': 'Apa X?', 'answer': 'X adalah Y'}],
    'quiz': [{
        'question': 'Pilihan?',
        'options': ['A', 'B', 'C', 'D'],
        'correctAnswer': 0,
        'explanation': 'Karena A.',
    }],
}


class ProfileSignalTests(TestCase):
    def test_profile_created_on_signup(self):
        user = User.objects.create_user('alice', password='pass')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.learning_style, 'detailed')
        self.assertFalse(user.profile.preferences_set)


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')

    def test_document_and_chat_message(self):
        doc = Document.objects.create(
            user=self.user,
            title='Materi',
            source_type='text',
            raw_content='Isi materi',
            ai_output=KIT_FIXTURE,
        )
        ChatMessage.objects.create(document=doc, role='user', content='Halo')
        self.assertEqual(doc.chat_messages.count(), 1)
        self.assertEqual(doc.source_type, 'text')


class ServiceTests(TestCase):
    def test_parse_youtube_id_watch(self):
        self.assertEqual(
            _parse_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
            'dQw4w9WgXcQ',
        )

    def test_parse_youtube_id_short(self):
        self.assertEqual(_parse_youtube_id('https://youtu.be/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')

    def test_parse_json_strips_fences(self):
        text = '```json\n{"summary": "ok"}\n```'
        self.assertEqual(_parse_json(text), {'summary': 'ok'})

    def test_parse_json_raises_on_invalid(self):
        with self.assertRaises(ValueError):
            _parse_json('bukan json')

    @mock.patch('core.services._get_client')
    def test_build_learning_kit_returns_parsed_dict(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps(KIT_FIXTURE)
        mock_client.return_value.models.generate_content.return_value = fake
        result = build_learning_kit('materi', 'detailed', 'sma', '10', 10, 5)
        self.assertEqual(result['flashcards'][0]['question'], 'Apa X?')
        mock_client.return_value.models.generate_content.assert_called_once()

    @mock.patch('core.services.time.sleep')
    def test_call_with_retry_retries_on_503_then_succeeds(self, _mock_sleep):
        fn = mock.Mock(side_effect=[
            APIError(503, {'error': {'code': 503}}),
            'berhasil',
        ])
        self.assertEqual(_call_with_retry(fn), 'berhasil')
        self.assertEqual(fn.call_count, 2)

    @mock.patch('core.services.time.sleep')
    def test_call_with_retry_raises_friendly_error_after_retries(self, _mock_sleep):
        fn = mock.Mock(side_effect=APIError(503, {'error': {'code': 503}}))
        with self.assertRaises(ValueError) as ctx:
            _call_with_retry(fn)
        self.assertEqual(str(ctx.exception), FRIENDLY_UNAVAILABLE_MSG)
        self.assertEqual(fn.call_count, 3)

    def test_call_with_retry_does_not_retry_non_retryable_error(self):
        fn = mock.Mock(side_effect=APIError(400, {'error': {'code': 400}}))
        with self.assertRaises(APIError):
            _call_with_retry(fn)
        self.assertEqual(fn.call_count, 1)

    @mock.patch('core.services._get_client')
    def test_build_learning_kit_injects_education_level(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps(KIT_FIXTURE)
        mock_client.return_value.models.generate_content.return_value = fake
        build_learning_kit('materi', 'visual', 'sma', '10', 5, 3)
        kwargs = mock_client.return_value.models.generate_content.call_args
        prompt = kwargs.kwargs['contents']
        self.assertIn('Target audiens: sma (10)', prompt)
        self.assertIn('Jenjang SMA', prompt)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_injects_education_level(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        result = chat_with_document('materi', [], 'smp', '8')
        self.assertEqual(result, 'Jawaban')
        sent = chat.send_message.call_args.args[0]
        self.assertIn('Target audiens: smp kelas 8', sent)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_builds_part_dicts_for_history(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        history = [
            {'role': 'user', 'content': 'Halo'},
            {'role': 'assistant', 'content': 'Hai!'},
            {'role': 'user', 'content': 'Pertanyaan?'},
        ]
        chat_with_document('materi', history, 'sma', '10')
        kwargs = mock_client.return_value.chats.create.call_args.kwargs
        expected = [
            {'role': 'user', 'parts': [{'text': 'Halo'}]},
            {'role': 'model', 'parts': [{'text': 'Hai!'}]},
            {'role': 'user', 'parts': [{'text': 'Pertanyaan?'}]},
        ]
        self.assertEqual(kwargs['history'], expected)


class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')
        self.client.force_login(self.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_landing_public(self):
        response = self.client.get(reverse('core:landing'))
        self.assertEqual(response.status_code, 200)

    @mock.patch('core.views.build_learning_kit', return_value=KIT_FIXTURE)
    def test_process_text_uses_profile_preferences(self, mock_kit):
        profile = self.user.profile
        profile.learning_style = 'visual'
        profile.education_level = 'sma'
        profile.grade = '10'
        profile.save(update_fields=['learning_style', 'education_level', 'grade'])

        response = self.client.post(reverse('core:process'), {
            'source_type': 'text',
            'raw_text': 'Isi materi yang cukup panjang untuk belajar.',
            'num_flashcards': 5,
            'num_quiz': 3,
        })
        self.assertEqual(response.status_code, 302)
        doc = Document.objects.get(user=self.user)
        self.assertEqual(doc.source_type, 'text')
        self.assertEqual(doc.education_level, 'sma')
        self.assertEqual(doc.grade, '10')
        self.assertEqual(doc.ai_output['summary'], '# Ringkasan')
        self.assertEqual(self.user.profile.learning_style, 'visual')
        mock_kit.assert_called_once_with(
            'Isi materi yang cukup panjang untuk belajar.',
            'visual',
            'sma',
            '10',
            5,
            3,
        )

    def test_process_invalid_form_shows_errors(self):
        response = self.client.post(reverse('core:process'), {
            'source_type': 'text',
            'raw_text': '',
            'num_flashcards': 5,
            'num_quiz': 3,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'wajib diisi')

    def test_workspace_ownership_denied(self):
        other = User.objects.create_user('bob', password='pass')
        doc = Document.objects.create(
            user=other, title='M', source_type='text', raw_content='x', ai_output=KIT_FIXTURE
        )
        response = self.client.get(reverse('core:workspace', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 403)

    @mock.patch('core.views.chat_with_document', return_value='Jawaban AI')
    def test_chat_api_saves_messages(self, mock_chat):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE, education_level='sma', grade='10',
        )
        response = self.client.post(
            reverse('core:chat', kwargs={'pk': doc.pk}),
            data=json.dumps({'message': 'Pertanyaan'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['content'], 'Jawaban AI')
        self.assertEqual(ChatMessage.objects.filter(document=doc).count(), 2)
        mock_chat.assert_called_once_with('x', mock.ANY, 'sma', '10')


class LibraryAndSettingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')
        self.client.force_login(self.user)

    def test_library_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:library'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_library_lists_only_own_documents(self):
        Document.objects.create(
            user=self.user, title='Milik Alice', source_type='text', raw_content='x'
        )
        other = User.objects.create_user('bob', password='pass')
        Document.objects.create(
            user=other, title='Milik Bob', source_type='text', raw_content='x'
        )
        response = self.client.get(reverse('core:library'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Milik Alice')
        self.assertNotContains(response, 'Milik Bob')

    def test_library_paginates(self):
        for i in range(15):
            Document.objects.create(
                user=self.user, title=f'Materi {i}', source_type='text', raw_content='x'
            )
        response = self.client.get(reverse('core:library'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['documents']), 12)
        response = self.client.get(reverse('core:library'), {'page': 2})
        self.assertEqual(len(response.context['documents']), 3)

    def test_settings_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_settings_get_renders_with_initial_values(self):
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pengaturan Akun')
        form = response.context['form']
        self.assertEqual(form.initial['full_name'], '')
        self.assertEqual(form.initial['learning_style'], 'detailed')
        self.assertEqual(form.initial['education_level'], 'umum')
        self.assertEqual(form.initial['grade'], '')

    def test_settings_post_updates_profile(self):
        response = self.client.post(reverse('core:settings'), {
            'full_name': 'Alice Baru',
            'learning_style': 'visual',
            'education_level': 'smp',
            'grade': '7',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:settings'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alice Baru')
        self.assertEqual(self.user.profile.learning_style, 'visual')
        self.assertEqual(self.user.profile.education_level, 'smp')
        self.assertEqual(self.user.profile.grade, '7')

    def test_settings_grade_required_for_level(self):
        response = self.client.post(reverse('core:settings'), {
            'full_name': 'Alice',
            'learning_style': 'visual',
            'education_level': 'sma',
            'grade': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'grade', 'Pilih kelas atau semester terlebih dahulu.')


class LandingAuthStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')
        self.client.force_login(self.user)

    def test_landing_hides_login_button_for_authenticated_user(self):
        response = self.client.get(reverse('core:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buka Dashboard')
        self.assertNotContains(response, 'Masuk')
        self.assertNotContains(response, 'Mulai Gratis')

    def test_landing_shows_login_button_for_anonymous_user(self):
        self.client.logout()
        response = self.client.get(reverse('core:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Masuk')
        self.assertContains(response, 'Mulai Gratis')

    def test_login_page_redirects_authenticated_user(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))


class RegisterViewTests(TestCase):
    def test_register_page_renders(self):
        response = self.client.get(reverse('core:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buat akun')

    @mock.patch('core.views.supabase_auth.is_configured', return_value=False)
    def test_register_creates_user_and_logs_in(self, _mock_configured):
        response = self.client.post(reverse('core:register'), {
            'full_name': 'Alice',
            'email': 'alice@example.com',
            'password1': 'rahasia123',
            'password2': 'rahasia123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))
        user = User.objects.get(email='alice@example.com')
        self.assertEqual(user.username, 'alice@example.com')
        self.assertEqual(user.first_name, 'Alice')
        self.assertTrue(user.check_password('rahasia123'))

    def test_register_rejects_mismatched_password(self):
        response = self.client.post(reverse('core:register'), {
            'full_name': 'Alice',
            'email': 'alice@example.com',
            'password1': 'rahasia123',
            'password2': 'rahasia124',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'password2', 'Konfirmasi password tidak cocok.')

    @mock.patch('core.views.supabase_auth.is_configured', return_value=False)
    def test_register_creates_profile_without_preferences(self, _mock_configured):
        response = self.client.post(reverse('core:register'), {
            'full_name': 'Budi',
            'email': 'budi@example.com',
            'password1': 'rahasia123',
            'password2': 'rahasia123',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='budi@example.com')
        self.assertFalse(user.profile.preferences_set)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(username='a@example.com', email='a@example.com', password='x')
        response = self.client.post(reverse('core:register'), {
            'full_name': 'Alice',
            'email': 'a@example.com',
            'password1': 'rahasia123',
            'password2': 'rahasia123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'Email ini sudah terdaftar.')

    @mock.patch('core.views.supabase_auth.sign_up')
    @mock.patch('core.views.supabase_auth.is_configured', return_value=True)
    def test_register_syncs_supabase_when_configured(self, _mock_configured, mock_signup):
        self.client.post(reverse('core:register'), {
            'full_name': 'Bob',
            'email': 'bob@example.com',
            'password1': 'rahasia123',
            'password2': 'rahasia123',
        })
        mock_signup.assert_called_once_with('bob@example.com', 'rahasia123', 'Bob')


class PreferencesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')
        self.client.force_login(self.user)

    def test_preferences_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('core:preferences'), {})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_preferences_saves_profile_and_marks_set(self):
        response = self.client.post(reverse('core:preferences'), {
            'learning_style': 'visual',
            'education_level': 'sma',
            'grade': '11',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.learning_style, 'visual')
        self.assertEqual(profile.education_level, 'sma')
        self.assertEqual(profile.grade, '11')
        self.assertTrue(profile.preferences_set)

    def test_preferences_grade_required_for_level(self):
        response = self.client.post(reverse('core:preferences'), {
            'learning_style': 'visual',
            'education_level': 'smp',
            'grade': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['prefs_form'], 'grade', 'Pilih kelas atau semester terlebih dahulu.')
        self.assertFalse(Profile.objects.get(user=self.user).preferences_set)

    def test_dashboard_shows_modal_when_preferences_not_set(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lengkapi preferensi belajarmu')

    def test_preferences_modal_renders_all_options(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="sd">SD</option>', html=True)
        self.assertContains(response, '<option value="smp">SMP</option>', html=True)
        self.assertContains(response, '<option value="visual">Visual</option>', html=True)
        self.assertContains(response, '<option value="socratic">Socratic</option>', html=True)

    def test_dashboard_hides_modal_when_preferences_set(self):
        profile = self.user.profile
        profile.preferences_set = True
        profile.save(update_fields=['preferences_set'])
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'x-data="dashboardPage(true)"')


class OAuthViewTests(TestCase):
    def test_oauth_login_unknown_provider_404(self):
        response = self.client.get(reverse('core:oauth_login', kwargs={'provider': 'x'}))
        self.assertEqual(response.status_code, 404)

    @mock.patch('core.views.supabase_auth.is_configured', return_value=False)
    def test_oauth_login_not_configured_redirects(self, _mock_configured):
        response = self.client.get(reverse('core:oauth_login', kwargs={'provider': 'google'}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    @mock.patch('core.views.supabase_auth.authorize_url',
                return_value=('https://x.supabase.co/auth/v1/authorize?...', 'VERIFIER'))
    @mock.patch('core.views.supabase_auth.is_configured', return_value=True)
    def test_oauth_login_redirects_to_provider(self, _mock_configured, _mock_authorize):
        response = self.client.get(reverse('core:oauth_login', kwargs={'provider': 'github'}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://x.supabase.co'))
        self.assertEqual(self.client.session.get('oauth_code_verifier'), 'VERIFIER')

    @mock.patch('core.views.supabase_auth.exchange_code', return_value={
        'user': {'email': 'dev@github.com', 'user_metadata': {'name': 'Dev'}},
    })
    def test_oauth_callback_creates_user_and_logs_in(self, _mock_exchange):
        session = self.client.session
        session['oauth_code_verifier'] = 'VERIFIER'
        session.save()
        response = self.client.get(reverse('core:oauth_callback'), {'code': 'CODE'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))
        user = User.objects.get(email='dev@github.com')
        self.assertEqual(user.username, 'dev@github.com')
        self.assertFalse(user.has_usable_password())

    def test_oauth_callback_without_code_redirects(self):
        response = self.client.get(reverse('core:oauth_callback'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
