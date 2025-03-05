from django.urls import path
from . import views

app_name = 'sync'

urlpatterns = [
    path('', views.sync_dashboard, name='dashboard'),
    path('content/', views.sync_content_form, name='content_form'),
    path('trigger/', views.trigger_sync, name='trigger'),
    path('receive/', views.receive_sync, name='receive'),
    path('log/<int:log_id>/', views.sync_log_detail, name='log_detail'),
    path('direct-sync/', views.direct_sync, name='direct_sync'),
    path('file-sync-content/', views.file_sync_content, name='file_sync_content'),
]
