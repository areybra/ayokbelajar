from django import forms
from django.contrib.auth.models import User

from .models import EDUCATION_LEVELS, LANGUAGES, Document, Profile

MAX_PDF_SIZE_MB = 20

GRADES_BY_LEVEL = {
    'sd': [str(i) for i in range(1, 7)],
    'smp': [str(i) for i in range(7, 10)],
    'sma': [str(i) for i in range(10, 13)],
    'pt': [f'Semester {i}' for i in range(1, 9)],
    'umum': [],
}

_SELECT_CLASS = (
    'w-full cursor-pointer rounded-xl border border-slate-200 bg-white p-2.5 '
    'focus:border-primary focus:outline-none focus:ring-2 focus:ring-teal-500/30'
)


class ProfilePreferencesForm(forms.Form):
    """Preferensi belajar profil: gaya belajar, jenjang pendidikan, dan kelas."""

    education_level = forms.ChoiceField(
        choices=EDUCATION_LEVELS,
        initial='umum',
        label='Jenjang pendidikan',
        widget=forms.Select(attrs={'class': _SELECT_CLASS}),
    )
    grade = forms.CharField(
        required=False,
        max_length=20,
        label='Kelas / Semester',
        widget=forms.Select(attrs={'class': _SELECT_CLASS}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        level = self.data.get('education_level') if self.is_bound else self.initial.get('education_level', 'umum')
        if level in GRADES_BY_LEVEL:
            self.fields['grade'].widget.choices = [
                (grade, grade) for grade in GRADES_BY_LEVEL[level]
            ]

    def clean(self):
        cleaned = super().clean()
        level = cleaned.get('education_level')
        grade = cleaned.get('grade')
        if level and level != 'umum':
            if not grade:
                self.add_error('grade', 'Pilih kelas atau semester terlebih dahulu.')
            elif grade not in GRADES_BY_LEVEL.get(level, []):
                self.add_error('grade', 'Kelas tidak valid untuk jenjang yang dipilih.')
        return cleaned


class StudyKitForm(forms.Form):
    SOURCE_CHOICES = (
        ('text', 'Raw Text'),
        ('youtube', 'YouTube URL'),
        ('pdf', 'Upload PDF'),
    )

    source_type = forms.ChoiceField(choices=SOURCE_CHOICES, initial='text')
    raw_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': 'Tempel teks materi di sini...'}),
        required=False,
    )
    youtube_url = forms.URLField(
        widget=forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=...'}),
        required=False,
    )
    pdf_file = forms.FileField(required=False, help_text='Maksimal 20 MB.')
    learning_style = forms.ChoiceField(
        choices=Profile.LEARNING_STYLES,
        initial='detailed',
        label='Gaya belajar',
        error_messages={'required': 'Gaya belajar wajib dipilih.'},
        widget=forms.Select(attrs={'class': _SELECT_CLASS}),
    )
    language = forms.ChoiceField(
        choices=LANGUAGES,
        initial='id',
        label='Bahasa output',
        error_messages={'required': 'Bahasa wajib dipilih.'},
        widget=forms.Select(attrs={'class': _SELECT_CLASS}),
    )

    def clean(self):
        cleaned = super().clean()
        source_type = cleaned.get('source_type')
        if source_type == 'text' and not cleaned.get('raw_text'):
            self.add_error('raw_text', 'Teks materi wajib diisi.')
        elif source_type == 'youtube' and not cleaned.get('youtube_url'):
            self.add_error('youtube_url', 'URL YouTube wajib diisi.')
        elif source_type == 'pdf' and not cleaned.get('pdf_file'):
            self.add_error('pdf_file', 'File PDF wajib diunggah.')
        return cleaned


class RegisterForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label='Nama lengkap',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama lengkap',
            'autocomplete': 'name',
        }),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'nama@email.com',
            'autocomplete': 'email',
        }),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Konfirmasi password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get('email') or '').strip().lower()
        if email and User.objects.filter(email=email).exists():
            self.add_error('email', 'Email ini sudah terdaftar.')
        if cleaned.get('password1') != cleaned.get('password2'):
            self.add_error('password2', 'Konfirmasi password tidak cocok.')
        return cleaned


class SettingsForm(ProfilePreferencesForm):
    full_name = forms.CharField(
        max_length=150,
        label='Nama lengkap',
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'class': 'w-full rounded-xl border border-slate-200 p-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-teal-500/30',
        }),
    )
