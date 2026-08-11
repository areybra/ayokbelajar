from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('oauth/callback/', views.oauth_callback_view, name='oauth_callback'),
    path('oauth/<str:provider>/', views.oauth_login_view, name='oauth_login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('preferences/', views.preferences_view, name='preferences'),
    path('library/', views.library_view, name='library'),
    path('settings/', views.settings_view, name='settings'),
    path('process/', views.process_content_view, name='process'),
    path('workspace/<int:pk>/', views.workspace_view, name='workspace'),
    path('workspace/<int:pk>/chat/', views.chat_api_view, name='chat'),
    path('workspace/<int:pk>/delete/', views.delete_document_view, name='delete'),
]
