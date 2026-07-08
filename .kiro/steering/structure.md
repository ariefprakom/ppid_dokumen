# Project Structure

```
ppid_dokumen/
├── core/                       # Django project config & shared infrastructure
│   ├── settings.py             # Settings (python-decouple, whitenoise, OIDC)
│   ├── urls.py                 # Root URL config: / redirect, /admin/, /ppid/, /oidc/
│   ├── admin.py                # Custom PPIDAdminSite (header, OIDC logout)
│   ├── oidc.py                 # Keycloak OIDC authentication backend
│   ├── views.py                # OIDC callback & logout views
│   ├── middleware.py           # OIDCSessionMiddleware (stores id_token)
│   ├── context_processors.py   # Exposes oidc_enabled to templates
│   ├── templates/admin/
│   │   └── login.html          # Custom admin login (adds "Login with Keycloak" button)
│   ├── wsgi.py
│   └── asgi.py
├── ppid_dokumen/               # Main Django app (CDN documents)
│   ├── models.py               # Organisasi, UnitOrganisasi, UnitKerja, KategoriInformasi, DokumenPPID
│   ├── views.py                # FBVs: cdn_files_table, list_sftp_files_html, document_download, cdn_file_delete, cdn_file_rename
│   ├── urls.py                 # App URLs (namespace: ppid_dokumen)
│   ├── admin.py                # Admin: Organisasi/Unit CRUD + CDN upload & manage custom views
│   ├── forms.py                # CDNUploadForm
│   ├── templates/
│   │   ├── ppid_dokumen/
│   │   │   ├── cdn_files_table.html    # Public: CDN files table with filters (landing page)
│   │   │   ├── document_list.html      # Legacy: document table (disabled)
│   │   │   └── list_files.html         # CDN file browser (folder navigation)
│   │   └── admin/
│   │       ├── cdn_upload.html         # Admin: CDN upload form
│   │       ├── cdn_manage.html         # Admin: CDN file management (rename/delete)
│   │       └── index.html              # Admin: custom index with CDN links
│   └── migrations/
├── .env                        # Environment config (secrets - gitignored)
├── .env.example                # Template for .env
├── .dockerignore               # Excludes for Docker build
├── Dockerfile                  # Multi-stage production image (Gunicorn + Whitenoise)
├── requirements.txt            # Pinned Python dependencies
├── manage.py
├── venv/                       # Python virtual environment (gitignored)
└── media/                      # Local file uploads at runtime (gitignored)
```

## Conventions

- Two-module architecture: `core/` = project config & auth infra, `ppid_dokumen/` = all business logic
- Function-based views (not class-based), except OIDC callback (CBV from mozilla-django-oidc)
- Templates follow Django's `<app>/templates/<app>/` namespace convention
- Admin template overrides in both `core/templates/admin/` and `ppid_dokumen/templates/admin/`
- URL namespacing: `app_name = "ppid_dokumen"`
- Models use Indonesian field names and verbose_name (e.g., `tentang`, `tahun`, `penulis`)
- ForeignKey uses `on_delete=models.PROTECT` (prevent cascade) or `on_delete=models.CASCADE` (for child units)
- Admin is the primary management interface; custom admin views for CDN operations
- Config via python-decouple: never hardcode secrets, always use `config('KEY')`
- OIDC integration is feature-flagged (OIDC_ENABLED) — all OIDC code paths check this flag

## Routing

| URL                          | View                  | Name                            |
|------------------------------|-----------------------|---------------------------------|
| /                            | RedirectView → /ppid/ | —                               |
| /ppid/                       | cdn_files_table       | ppid_dokumen:cdn_files_table    |
| /ppid/data/                  | list_sftp_files_html  | ppid_dokumen:list_cdn_files     |
| /ppid/unduh/<pk>/            | document_download     | ppid_dokumen:download           |
| /ppid/cdn/delete/            | cdn_file_delete       | ppid_dokumen:cdn_file_delete    |
| /ppid/cdn/rename/            | cdn_file_rename       | ppid_dokumen:cdn_file_rename    |
| /admin/                      | Django admin          | —                               |
| /admin/cdn-upload/           | CDN upload form       | admin:cdn_upload                |
| /oidc/                       | mozilla-django-oidc   | (when OIDC_ENABLED)             |
| /oidc/logout/                | keycloak_logout       | oidc_logout                     |
| /oidc/callback/              | KeycloakCallbackView  | oidc_authentication_callback    |
