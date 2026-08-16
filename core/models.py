from django.conf import settings
from django.db import models

EDUCATION_LEVELS = (
    ('umum', 'Umum/Perguruan Tinggi'),
    ('sd', 'SD'),
    ('smp', 'SMP'),
    ('sma', 'SMA'),
    ('pt', 'Perguruan Tinggi'),
)


class Profile(models.Model):
    LEARNING_STYLES = (
        ('visual', 'Visual'),
        ('eli5', 'Explain Like I\'m 5'),
        ('detailed', 'Detailed'),
        ('socratic', 'Socratic'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    learning_style = models.CharField(
        max_length=20,
        choices=LEARNING_STYLES,
        default='detailed',
    )
    education_level = models.CharField(
        max_length=10,
        choices=EDUCATION_LEVELS,
        default='umum',
    )
    grade = models.CharField(max_length=20, blank=True, default='')
    preferences_set = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} ({self.learning_style})'


class Document(models.Model):
    SOURCE_TYPES = (
        ('youtube', 'YouTube'),
        ('pdf', 'PDF'),
        ('text', 'Raw Text'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
        db_index=True,
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_url = models.TextField(blank=True, default='')
    raw_content = models.TextField()
    education_level = models.CharField(
        max_length=10,
        choices=EDUCATION_LEVELS,
        default='umum',
    )
    grade = models.CharField(max_length=20, blank=True, default='')
    ai_output = models.JSONField(default=dict)
    summary_html = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return self.title


class PracticeSession(models.Model):
    """Sesi latihan soal yang tersimpan untuk dipelajari ulang."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='practice_sessions',
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True, default='')
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f'Sesi #{self.pk}'


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        db_index=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'


class UserActivity(models.Model):
    """Jejak hari aktif pengguna untuk menghitung streak belajar."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities',
        db_index=True,
    )
    active_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-active_date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'active_date'],
                name='one_activity_per_user_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.active_date}'

    @classmethod
    def record_if_new(cls, user, date):
        """Catat aktivitas hari ini bila belum ada (anti-duplikat per hari)."""
        if not user.is_authenticated:
            return None
        obj, _ = cls.objects.get_or_create(user=user, active_date=date)
        return obj

    @classmethod
    def streak_for(cls, user, today=None):
        """Jumlah hari aktif beruntun hingga hari ini (atau kemarin bila hari ini belum aktif)."""
        from datetime import timedelta
        if today is None:
            from django.utils import timezone
            today = timezone.now().date()
        dates = set(cls.objects.filter(user=user).values_list('active_date', flat=True))
        if not dates:
            return 0
        cursor = today if today in dates else today - timedelta(days=1)
        streak = 0
        while cursor in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak
