from django.contrib import admin
from django.utils.html import format_html

from .models import ChatMessage, Document, PracticeSession, Profile, UserActivity


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'learning_style', 'education_level', 'grade', 'language', 'preferences_set', 'created_at')
    list_filter = ('learning_style', 'education_level', 'language', 'preferences_set')
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_select_related = ('user',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'source_type', 'education_level', 'grade', 'language', 'created_at')
    list_filter = ('source_type', 'education_level', 'language')
    search_fields = ('title', 'user__username', 'user__email', 'raw_content')
    list_select_related = ('user',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ai_output_preview', 'summary_html_preview')

    @admin.display(description='Isi AI')
    def ai_output_preview(self, obj):
        output = obj.ai_output or {}
        summary = (output.get('summary') or '')[:200]
        n_cards = len(output.get('flashcards') or [])
        n_steps = len(output.get('roadmap') or [])
        n_exam = len(output.get('exam') or [])
        if not summary:
            return '—'
        return format_html(
            '<code>{}</code><br><small class="text-muted">{} kartu · {} peta · {} soal</small>',
            summary, n_cards, n_steps, n_exam,
        )

    @admin.display(description='Rangkuman HTML (hasil edit)')
    def summary_html_preview(self, obj):
        return 'Ada' if obj.summary_html else 'Belum diedit'

    ai_output_preview.short_description = 'Isi AI (pratinjau)'
    summary_html_preview.short_description = 'Rangkuman HTML'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('document', 'role', 'content_preview', 'created_at')
    list_filter = ('role',)
    search_fields = ('document__title', 'content')
    list_select_related = ('document',)
    date_hierarchy = 'created_at'

    @admin.display(description='Isi pesan')
    def content_preview(self, obj):
        text = obj.content
        if len(text) > 80:
            return f'{text[:80]}…'
        return text


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'document', 'question_count', 'created_at')
    search_fields = ('title', 'document__title')
    list_select_related = ('document',)
    date_hierarchy = 'created_at'

    @admin.display(description='Jumlah soal')
    def question_count(self, obj):
        return len(obj.questions or [])


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'active_date', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_select_related = ('user',)
    date_hierarchy = 'active_date'
