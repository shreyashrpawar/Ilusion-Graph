from django.urls import path
from . import views

app_name = 'vault'

urlpatterns = [
    path('', views.vault_dashboard, name='vault_home'),
    path('getFiles/', views.get_fileorFolders, name='get_fileorFolders'),
    path('upload/', views.vault_upload, name='vault_upload'),
    path('folder/', views.create_folder, name='create_folder'),
    path('delete/', views.delete_file, name='delete_file'),
    path('search/', views.search_files, name='search_files'),
    path('share/',views.share_file,name='share_file'),
    path('share/users/', views.get_shared_users, name='get_shared_users'),
    path('share/remove/', views.remove_shared_user, name='remove_shared_user'),
    path('user/check/', views.check_user_exists, name='check_user_exists'),
]
