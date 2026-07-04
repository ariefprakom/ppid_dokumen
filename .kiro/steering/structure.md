# Project Structure

```
ppid/
├── core/                   # Django project config (settings, urls, wsgi/asgi)
│   ├── settings.py
│   ├── urls.py             # Root URL config, includes app URLs
│   ├── wsgi.py
│   └── asgi.py
├── ppid_dokumen/           # Main (and only) Django app
│   ├── models.py           # UnitKerja, KategoriInformasi, DokumenPPID
│   ├── views.py            # Function-based views (document_list, document_download)
│   ├── urls.py             # App URL patterns (namespace: ppid_dokumen)
│   ├── admin.py            # ModelAdmin registrations
│   ├── templates/
│   │   └── ppid_dokumen/
│   │       └── document_list.html
│   └── migrations/
├── manage.py
├── venv/                   # Python virtual environment (gitignored)
└── media/                  # Uploaded files at runtime (not in repo)
```

## Conventions

- Single-app architecture: `core/` for project config, `ppid_dokumen/` for all business logic
- Function-based views (not class-based)
- Templates follow Django's `<app>/templates/<app>/` namespace convention
- URL namespacing: `app_name = "ppid_dokumen"` with names like `ppid_dokumen:list`
- Models use Indonesian field names and verbose_name (e.g., `tentang`, `tahun`, `penulis`)
- ForeignKey uses `on_delete=models.PROTECT` to prevent accidental cascade deletion
- Admin is the primary data-entry interface (no custom forms for document creation)

## Routing

| URL               | View              | Name                    |
|-------------------|-------------------|-------------------------|
| /ppid/            | document_list     | ppid_dokumen:list       |
| /ppid/unduh/<pk>/ | document_download | ppid_dokumen:download   |
| /admin/           | Django admin      | —                       |
