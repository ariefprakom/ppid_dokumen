# Tech Stack

## Framework
- Python + Django 5.2
- Django's built-in template engine (DTL)

## Database
- MySQL (configured via .env: localhost:3307, db name `ppid_dokumen`)
- SQLite available as fallback by changing DB_ENGINE in .env

## Authentication
- Keycloak OIDC via `mozilla-django-oidc` (toggle: OIDC_ENABLED in .env)
- Custom OIDC backend: `core/oidc.py` (KeycloakOIDCAuthenticationBackend)
- Role mapping: Keycloak roles → Django is_staff / is_superuser
- Fallback to Django ModelBackend for local accounts

## Frontend
- Server-rendered HTML templates (no SPA framework)
- jQuery 3.7 + DataTables 1.13 for table interactions (CDN-loaded)
- JSZip for Excel export via DataTables Buttons
- Inline CSS in templates (no build pipeline, no static file compilation)

## File Storage & CDN
- Local uploads: Django FileField → MEDIA_ROOT (`<project>/media/`)
- External files: `file_url` field for documents hosted elsewhere
- CDN upload: SFTP via `paramiko` to nginx-served CDN (cdn.ar-raniry.ac.id)
- CDN path structure: `/usr/share/nginx/cdn/ppid/data/{tahun}/{organisasi}/{unit}/`

## Configuration
- `python-decouple` for environment variables (reads from `.env`)
- `.env.example` documents all required/optional env vars
- Secrets (DB password, SFTP credentials, OIDC secret) must stay in .env, never hardcoded

## Key Libraries (requirements.txt)
- Django 5.2.15
- mozilla-django-oidc 5.0.2 (Keycloak SSO)
- paramiko 5.0.0 (SFTP file transfer)
- python-decouple 3.8 (env config)
- mysqlclient 2.2.8 (MySQL driver)
- PyJWT 2.13.0 (JWT handling for OIDC)

## Common Commands

```bash
# Activate virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Run tests
python manage.py test

# Generate requirements file
pip freeze > requirements.txt
```

## Key Settings
- All secrets/config via `python-decouple` from `.env`
- DEBUG controlled by .env (default False)
- MEDIA_URL = /media/
- OIDC can be toggled on/off without code changes (OIDC_ENABLED env var)
