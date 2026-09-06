from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('preferences/', views.preferences_view, name='preferences'),
    path('library/', views.library_view, name='library'),
    path('settings/', views.settings_view, name='settings'),
    path('process/', views.process_content_view, name='process'),
    path('workspace/<int:pk>/', views.workspace_view, name='workspace'),
    path('workspace/<int:pk>/chat/', views.chat_api_view, name='chat'),
    path('workspace/<int:pk>/summary/', views.summary_save_api_view, name='summary_save'),
    path('workspace/<int:pk>/practice/generate/', views.practice_generate_api_view, name='practice_generate'),
    path('workspace/<int:pk>/practice/save/', views.practice_save_api_view, name='practice_save'),
    path('workspace/<int:pk>/practice/<int:session_pk>/delete/', views.practice_delete_api_view, name='practice_delete'),
    path('workspace/<int:pk>/delete/', views.delete_document_view, name='delete'),
]
