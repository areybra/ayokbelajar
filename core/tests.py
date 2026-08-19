import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from google.genai.errors import APIError

from .models import ChatMessage, Document, Profile, UserActivity
from .services import (
    FRIENDLY_UNAVAILABLE_MSG,
    _call_with_retry,
    _parse_json,
    _parse_youtube_id,
    build_exam,
    build_learning_kit,
    chat_with_document,
)

KIT_FIXTURE = {
    'summary': '# Ringkasan',
    'roadmap': [{'step': 1, 'title': 'Mulai', 'detail': 'Definisi'}],
    'flashcards': [{'question': 'Apa X?', 'answer': 'X adalah Y'}],
    'resources': {
        'books': [{'title': 'Buku X', 'note': 'Bagus untuk pemula.'}],
        'articles': [{'title': 'Artikel Y', 'note': 'Penjelasan visual.'}],
        'search_query': 'teori X untuk pemula',
    },
}

EXAM_FIXTURE = [
    {
        'question_type': 'multiple_choice',
        'question': f'Soal {i}',
        'options': ['A', 'B', 'C', 'D'],
        'correctAnswer': 0,
        'explanation': 'Karena A.',
    }
    for i in range(20)
]


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
        result = build_learning_kit('materi', 'detailed', 'sma', '10', 10)
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
        self.assertEqual(fn.call_count, 5)

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
        build_learning_kit('materi', 'visual', 'sma', '10', 5)
        kwargs = mock_client.return_value.models.generate_content.call_args
        prompt = kwargs.kwargs['contents']
        self.assertIn('Target audiens: sma (10)', prompt)
        self.assertIn('Jenjang SMA', prompt)

    @mock.patch('core.services._get_client')
    def test_build_learning_kit_injects_output_language(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps(KIT_FIXTURE)
        mock_client.return_value.models.generate_content.return_value = fake
        build_learning_kit('English materi', 'detailed', 'umum', '', 5, language='id')
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs['contents']
        self.assertIn('BAHASA OUTPUT', prompt)
        self.assertIn('Bahasa Indonesia', prompt)
        self.assertNotIn('Gunakan bahasa yang sama dengan materi input', prompt)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_injects_education_level(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        result = chat_with_document('materi', [], 'smp', '8')
        self.assertEqual(result, 'Jawaban')
        sent = chat.send_message.call_args.args[0]
        self.assertIn('Target audiens: smp kelas 8', sent)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_injects_document_title(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        result = chat_with_document('materi', [], 'smp', '8', 'Biologi Kelas 8')
        self.assertEqual(result, 'Jawaban')
        sent = chat.send_message.call_args.args[0]
        self.assertIn('Judul dokumen: Biologi Kelas 8', sent)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_injects_output_language(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        chat_with_document('english materi', [], 'smp', '8', language='id')
        sent = chat.send_message.call_args.args[0]
        self.assertIn('BAHASA OUTPUT', sent)
        self.assertIn('Bahasa Indonesia', sent)

    @mock.patch('core.services._get_client')
    def test_chat_with_document_prompt_is_not_overly_strict(self, mock_client):
        chat = mock_client.return_value.chats.create.return_value
        chat.send_message.return_value.text = 'Jawaban'
        chat_with_document('materi', [], 'smp', '8')
        sent = chat.send_message.call_args.args[0]
        self.assertNotIn('HANYA berdasarkan materi', sent)
        self.assertNotIn('tidak tersedia di materi', sent)
        self.assertIn('materi ini sebagai sumber utama', sent)
        self.assertIn('masih sejalan dengan topik', sent)

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

    @mock.patch('core.services._get_client')
    def test_build_exam_returns_exactly_20_questions(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps({'exam': EXAM_FIXTURE})
        mock_client.return_value.models.generate_content.return_value = fake
        result = build_exam('materi', 'sma', '10')
        self.assertEqual(len(result), 20)
        self.assertEqual(result[0]['question'], 'Soal 0')
        kwargs = mock_client.return_value.models.generate_content.call_args
        self.assertIn('Target audiens: sma (10)', kwargs.kwargs['contents'])
        self.assertIn('PERSIS 20 soal', kwargs.kwargs['contents'])

    @mock.patch('core.services._get_client')
    def test_build_exam_truncates_when_more_than_20(self, mock_client):
        too_many = EXAM_FIXTURE + [EXAM_FIXTURE[0]]
        fake = mock.Mock()
        fake.text = json.dumps({'exam': too_many})
        mock_client.return_value.models.generate_content.return_value = fake
        self.assertEqual(len(build_exam('materi', 'sma', '10')), 20)

    @mock.patch('core.services._get_client')
    def test_build_exam_injects_output_language(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps({'exam': EXAM_FIXTURE})
        mock_client.return_value.models.generate_content.return_value = fake
        build_exam('english materi', 'sma', '10', language='id')
        prompt = mock_client.return_value.models.generate_content.call_args.kwargs['contents']
        self.assertIn('BAHASA OUTPUT', prompt)
        self.assertIn('Bahasa Indonesia', prompt)

    @mock.patch('core.services._get_client')
    def test_build_exam_raises_when_fewer_than_20(self, mock_client):
        fake = mock.Mock()
        fake.text = json.dumps({'exam': EXAM_FIXTURE[:5]})
        mock_client.return_value.models.generate_content.return_value = fake
        with self.assertRaises(ValueError) as ctx:
            build_exam('materi', 'sma', '10')
        self.assertIn('tepat 20 soal', str(ctx.exception))


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
            'learning_style': 'socratic',
            'language': 'id',
        })
        self.assertEqual(response.status_code, 302)
        doc = Document.objects.get(user=self.user)
        self.assertEqual(doc.source_type, 'text')
        self.assertEqual(doc.education_level, 'sma')
        self.assertEqual(doc.grade, '10')
        self.assertEqual(doc.ai_output['summary'], '# Ringkasan')
        mock_kit.assert_called_once_with(
            'Isi materi yang cukup panjang untuk belajar.',
            'socratic',
            'sma',
            '10',
            mock.ANY,
            'id',
        )

    @mock.patch('core.views.build_learning_kit', return_value=KIT_FIXTURE)
    def test_process_text_uses_selected_output_language(self, mock_kit):
        response = self.client.post(reverse('core:process'), {
            'source_type': 'text',
            'raw_text': 'Isi materi dalam bahasa Inggris.',
            'learning_style': 'detailed',
            'language': 'id',
        })
        self.assertEqual(response.status_code, 302)
        doc = Document.objects.get(user=self.user)
        self.assertEqual(doc.language, 'id')
        mock_kit.assert_called_once_with(
            'Isi materi dalam bahasa Inggris.',
            'detailed',
            'umum',
            '',
            mock.ANY,
            'id',
        )

    def test_process_invalid_form_shows_errors(self):
        response = self.client.post(reverse('core:process'), {
            'source_type': 'text',
            'raw_text': '',
            'learning_style': 'detailed',
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

    def test_workspace_flashcard_flip_uses_flipped_state(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.get(reverse('core:workspace', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '@click="flipped = !flipped"')
        self.assertNotContains(response, '@click="flip = !flip"')

    def test_workspace_flashcards_render_mastery_feature(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.get(reverse('core:workspace', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'flashcardDeck()')
        self.assertContains(response, 'Sudah Mahir ✓')
        self.assertContains(response, 'Belum Mahir')
        self.assertContains(response, 'Ulangi status semua kartu')
        self.assertContains(response, 'isCurrentMastered')

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
        mock_chat.assert_called_once_with('x', mock.ANY, 'sma', '10', 'M', 'id')

    def test_workspace_renders_new_feature_sections(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.get(reverse('core:workspace', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Peta Pikiran')
        self.assertContains(response, 'Latihan Soal')
        self.assertContains(response, 'Sumber Belajar')
        self.assertContains(response, 'Edit Rangkuman')

    def test_workspace_passes_resources_and_exam(self):
        output = dict(KIT_FIXTURE)
        output['exam'] = EXAM_FIXTURE
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=output,
        )
        doc.practice_sessions.create(title='Sesi Ujian 1', questions=EXAM_FIXTURE)
        response = self.client.get(reverse('core:workspace', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['exam']), 20)
        self.assertEqual(len(response.context['practice_sessions']), 1)
        self.assertEqual(response.context['practice_sessions'][0]['title'], 'Sesi Ujian 1')
        self.assertEqual(response.context['resources']['search_query'], 'teori X untuk pemula')

    def test_summary_save_api_persists_html(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(
            reverse('core:summary_save', kwargs={'pk': doc.pk}),
            data=json.dumps({'html': '<p>Rangkuman baru</p><p>Kedua</p>'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        doc.refresh_from_db()
        self.assertEqual(doc.summary_html, '<p>Rangkuman baru</p><p>Kedua</p>')

    def test_summary_save_api_rejects_empty(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(
            reverse('core:summary_save', kwargs={'pk': doc.pk}),
            data=json.dumps({'html': '   '}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        doc.refresh_from_db()
        self.assertEqual(doc.summary_html, '')

    def test_summary_save_api_ownership_denied(self):
        other = User.objects.create_user('bob', password='pass')
        doc = Document.objects.create(
            user=other, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(
            reverse('core:summary_save', kwargs={'pk': doc.pk}),
            data=json.dumps({'html': '<p>x</p>'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    @mock.patch('core.views.build_exam', return_value=EXAM_FIXTURE)
    def test_practice_generate_api_creates_and_saves_exam(self, mock_exam):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='materi',
            ai_output=KIT_FIXTURE, education_level='sma', grade='10',
        )
        response = self.client.post(reverse('core:practice_generate', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['exam']), 20)
        doc.refresh_from_db()
        self.assertEqual(doc.ai_output['exam'], EXAM_FIXTURE)
        mock_exam.assert_called_once_with('materi', 'sma', '10', 'id')

    @mock.patch('core.views.build_exam',
                side_effect=ValueError('tepat 20 soal tetapi AI menghasilkan 5.'))
    def test_practice_generate_api_returns_error_json(self, _mock_exam):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='materi',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(reverse('core:practice_generate', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 400)
        self.assertIn('tepat 20 soal', response.json()['error'])
        doc.refresh_from_db()
        self.assertNotIn('exam', doc.ai_output)

    def test_practice_generate_api_ownership_denied(self):
        other = User.objects.create_user('bob', password='pass')
        doc = Document.objects.create(
            user=other, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(reverse('core:practice_generate', kwargs={'pk': doc.pk}))
        self.assertEqual(response.status_code, 403)

    def test_practice_save_api_saves_current_session(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='materi',
            ai_output=dict(KIT_FIXTURE, exam=EXAM_FIXTURE),
        )
        response = self.client.post(
            reverse('core:practice_save', kwargs={'pk': doc.pk}),
            data=json.dumps({'title': 'Latihan Bab 1'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        session = doc.practice_sessions.get()
        self.assertEqual(session.title, 'Latihan Bab 1')
        self.assertEqual(session.questions, EXAM_FIXTURE)

    def test_practice_save_api_requires_questions(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        response = self.client.post(
            reverse('core:practice_save', kwargs={'pk': doc.pk}),
            data=json.dumps({'title': 'Sesi'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_practice_delete_api_removes_session(self):
        doc = Document.objects.create(
            user=self.user, title='M', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        session = doc.practice_sessions.create(title='Sesi A', questions=EXAM_FIXTURE)
        other = User.objects.create_user('bob2', password='pass')
        doc2 = Document.objects.create(
            user=other, title='N', source_type='text', raw_content='x',
            ai_output=KIT_FIXTURE,
        )
        session2 = doc2.practice_sessions.create(title='Sesi Lain', questions=EXAM_FIXTURE)

        response = self.client.post(
            reverse('core:practice_delete', kwargs={'pk': doc.pk, 'session_pk': session.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(doc.practice_sessions.filter(pk=session.pk).exists())
        self.assertTrue(doc2.practice_sessions.filter(pk=session2.pk).exists())

        response = self.client.post(
            reverse('core:practice_delete', kwargs={'pk': doc.pk, 'session_pk': session2.pk})
        )
        self.assertEqual(response.status_code, 404)


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
        self.assertEqual(form.initial['education_level'], 'umum')
        self.assertEqual(form.initial['grade'], '')

    def test_settings_post_updates_profile(self):
        response = self.client.post(reverse('core:settings'), {
            'full_name': 'Alice Baru',
            'education_level': 'smp',
            'grade': '7',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:settings'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alice Baru')
        self.assertEqual(self.user.profile.education_level, 'smp')
        self.assertEqual(self.user.profile.grade, '7')

    def test_settings_grade_required_for_level(self):
        response = self.client.post(reverse('core:settings'), {
            'full_name': 'Alice',
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
            'education_level': 'sma',
            'grade': '11',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.education_level, 'sma')
        self.assertEqual(profile.grade, '11')
        self.assertTrue(profile.preferences_set)

    def test_preferences_grade_required_for_level(self):
        response = self.client.post(reverse('core:preferences'), {
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
        self.assertContains(response, '<option value="socratic">Socratic</option>', html=True)

    def test_dashboard_hides_modal_when_preferences_set(self):
        profile = self.user.profile
        profile.preferences_set = True
        profile.save(update_fields=['preferences_set'])
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'x-data="dashboardPage(true)"')

    def test_dashboard_shows_output_language_select(self):
        profile = self.user.profile
        profile.preferences_set = True
        profile.save(update_fields=['preferences_set'])
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bahasa output')
        self.assertContains(response, 'name="language"')


class UserActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streak@example.com', password='x')

    def test_streak_counting_consecutive_days(self):
        from datetime import date, timedelta
        today = date(2026, 8, 15)
        for offset in range(3):
            UserActivity.objects.create(
                user=self.user, active_date=today - timedelta(days=offset)
            )
        self.assertEqual(UserActivity.streak_for(self.user, today=today), 3)

    def test_streak_breaks_on_gap(self):
        from datetime import date, timedelta
        today = date(2026, 8, 15)
        for offset in (0, 1, 3, 4):
            UserActivity.objects.create(
                user=self.user, active_date=today - timedelta(days=offset)
            )
        self.assertEqual(UserActivity.streak_for(self.user, today=today), 2)

    def test_streak_zero_when_no_activity(self):
        from datetime import date
        self.assertEqual(UserActivity.streak_for(self.user, today=date(2026, 8, 15)), 0)

    def test_record_if_new_is_idempotent(self):
        from datetime import date
        UserActivity.record_if_new(self.user, date(2026, 8, 15))
        UserActivity.record_if_new(self.user, date(2026, 8, 15))
        self.assertEqual(UserActivity.objects.filter(user=self.user).count(), 1)

    def test_dashboard_credit_reflects_current_month(self):
        from datetime import date, timedelta
        from django.utils import timezone
        from ayokbelajar_proj import settings
        today = timezone.now().date()
        month_start = today.replace(day=1)
        Document.objects.create(
            user=self.user, title='A', source_type='text', raw_content='x',
            ai_output={}, created_at=month_start + timedelta(days=4)
        )
        Document.objects.create(
            user=self.user, title='B', source_type='text', raw_content='y',
            ai_output={}, created_at=month_start + timedelta(days=5)
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['credit_remaining'],
            max(settings.FREE_MONTHLY_DOCUMENT_LIMIT - 2, 0),
        )
        self.assertEqual(
            response.context['documents'].count(), 2
        )


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
