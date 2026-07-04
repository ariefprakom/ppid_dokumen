from django.urls import path
from . import views

app_name = "ppid_dokumen"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("unduh/<int:pk>/", views.document_download, name="download"),
]
