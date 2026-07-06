# Project Structure

```
ppid/
├── core/                       # Django project config & shared infrastructure
│   ├── settings.py             # Settings (uses python-decouple for .env)
│   ├── urls.py                 # Root URL config, conditional OIDC routes
│   ├── admin.py                # Custom PPIDAdminSite (header, OIDC logout)
│   ├── oidc.py                 # Keycloak OIDC authentication backend
│   ├── views.py                # OIDC callback & logout views
│   ├── middleware.py           # OIDCSessionMiddleware (stores id_token)
│   ├── context_processors.py   # Exposes oidc_enabled to templates
│   ├── templates/admin/
│   │   └── login.html          # Custom admin login (adds "Login with Keycloak" button)
│   ├── wsgi.py
│   └── asgi.py
├── ppid_dokumen/               # Main Django app (documents & CDN)
│   ├── models.py               # UnitKerja, KategoriInformasi, Organisasi, UnitOrganisasi, DokumenPPID
│   ├── views.py                # FBVs: document_list, document_download, list_sftp_files_html, cdn_files_table
│   ├── urls.py                 # App URLs (namespace: ppid_dokumen)
│   ├── admin.py                # Admin: Organisasi/Unit CRUD + CDN upload custom view
│   ├── forms.py                # CDNUploadForm
│   ├── templates/
│   │   ├── ppid_dokumen/
│   │   │   ├── document_list.html      # Public document table with filters
│   │   │   ├── list_files.html         # CDN file browser
│   │   │   └── cdn_files_table.html    # CDN files flat table with filters
│   │   └── admin/
│   │       ├── cdn_upload.html         # Admin: CDN upload form
│   │       └── index.html              # Admin: custom index with CDN upload link
│   └── migrations/
├── .env                        # Environment config (secrets - gitignored)
├── .env.example                # Template for .env
├── requirements.txt            # Pinned Python dependencies
├── manage.py
├── venv/                       # Python virtual environment (gitignored)
└── media/                      # Local file uploads at runtime (not in repo)
```

## Conventions

- Two-module architecture: `core/` = project config & auth infra, `ppid_dokumen/` = all business logic
- Function-based views (not class-based), except OIDC callback (CBV from mozilla-django-oidc)
- Templates follow Django's `<app>/templates/<app>/` namespace convention
- Admin template overrides in both `core/templates/admin/` and `ppid_dokumen/templates/admin/`
- URL namespacing: `app_name = "ppid_dokumen"` with names like `ppid_dokumen:list`
- Models use Indonesian field names and verbose_name (e.g., `tentang`, `tahun`, `penulis`)
- ForeignKey uses `on_delete=models.PROTECT` (prevent cascade) or `on_delete=models.CASCADE` (for child units)
- Admin is the primary management interface; custom admin views for CDN upload
- Config via python-decouple: never hardcode secrets, always use `config('KEY')`
- OIDC integration is feature-flagged (OIDC_ENABLED) — all OIDC code paths check this flag

## Routing

| URL                          | View                  | Name                            |
|------------------------------|-----------------------|---------------------------------|
| /ppid/                       | document_list         | ppid_dokumen:list               |
| /ppid/unduh/<pk>/            | document_download     | ppid_dokumen:download           |
| /ppid/data/                  | list_sftp_files_html  | ppid_dokumen:list_cdn_files     |
| /ppid/data/tabel/            | cdn_files_table       | ppid_dokumen:cdn_files_table    |
| /admin/                      | Django admin          | —                               |
| /admin/cdn-upload/           | CDN upload form       | admin:cdn_upload                |
| /oidc/                       | mozilla-django-oidc   | (when OIDC_ENABLED)             |
| /oidc/logout/                | keycloak_logout       | oidc_logout                     |
| /oidc/callback/              | KeycloakCallbackView  | oidc_authentication_callback    |
