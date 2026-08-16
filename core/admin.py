from django.contrib import admin

from .models import ChatMessage, Document, PracticeSession, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'learning_style', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'source_type', 'created_at')
    list_filter = ('source_type',)
    search_fields = ('title', 'user__username')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('document', 'role', 'created_at')
    list_filter = ('role',)


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ('document', 'title', 'created_at')
    search_fields = ('document__title', 'title')
