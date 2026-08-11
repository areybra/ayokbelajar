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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return self.title


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
