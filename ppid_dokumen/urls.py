from django.urls import path
from . import views

app_name = "ppid_dokumen"

urlpatterns = [
    # path("", views.document_list, name="list"),
    path('data/', views.list_sftp_files_html, name='list_cdn_files'),
    path('', views.cdn_files_table, name='cdn_files_table'),
    path("unduh/<int:pk>/", views.document_download, name="download"),
]
