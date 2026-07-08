# Tech Stack

## Framework
- Python 3.11 + Django 5.2
- Django's built-in template engine (DTL)

## Database
- MySQL (configured via .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
- Production: 192.168.176.26:3308

## Authentication
- Keycloak OIDC via `mozilla-django-oidc` (toggle: OIDC_ENABLED in .env)
- Custom OIDC backend: `core/oidc.py` (KeycloakOIDCAuthenticationBackend)
- Role mapping: Keycloak roles → Django is_staff / is_superuser
- Fallback to Django ModelBackend for local accounts

## Frontend
- Server-rendered HTML templates (no SPA framework)
- Bootstrap 5.3 + Bootstrap Icons (CDN-loaded)
- jQuery 3.7 + DataTables 1.13 for table interactions (CDN-loaded)
- JSZip for Excel export via DataTables Buttons
- Inline CSS in templates (no build pipeline, no static file compilation)

## File Storage & CDN
- CDN server: cdn.ar-raniry.ac.id, served by Nginx
- CDN upload/manage: SFTP via `paramiko` (credentials in .env)
- CDN path structure: `/usr/share/nginx/cdn/ppid/data/{tahun}/{organisasi}/{unit}/`
- Public URL: `https://cdn.ar-raniry.ac.id/ppid/data/{tahun}/{organisasi}/{unit}/{file}`
- Local uploads (legacy): Django FileField → MEDIA_ROOT (`<project>/media/`)

## Configuration
- `python-decouple` for environment variables (reads from `.env`)
- `.env.example` documents all required/optional env vars
- Secrets (DB password, SFTP credentials, OIDC secret) must stay in .env, never hardcoded

## Deployment
- Docker: multi-stage Dockerfile (python:3.11-bullseye builder → python:3.11-slim-bullseye)
- WSGI server: Gunicorn (3 workers, timeout 120s)
- Static files: Whitenoise (CompressedManifestStaticFilesStorage)
- Workflow: build locally → push to Docker Hub → pull on server → docker run with -e flags
- Image name: ariefprakom/ppid-dokumen:latest
- Production host: 192.168.176.23:8000
- No docker-compose, no Nginx container needed

## Key Libraries (requirements.txt)
- Django 5.2.15
- gunicorn 23.0.0 (WSGI server)
- whitenoise 6.7.0 (static file serving)
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

# Collect static files (for production)
python manage.py collectstatic --noinput

# Docker build & deploy
docker build -t ariefprakom/ppid-dokumen:latest .
docker push ariefprakom/ppid-dokumen:latest
# On server:
docker stop ppid_dokumen && docker rm ppid_dokumen
docker pull ariefprakom/ppid-dokumen:latest
docker run -d --name ppid_dokumen --restart unless-stopped -p 8000:8000 -e ... ariefprakom/ppid-dokumen:latest
```

## Key Settings
- All secrets/config via `python-decouple` from `.env`
- DEBUG controlled by .env (default False)
- STATIC_ROOT = staticfiles/ (served by Whitenoise)
- MEDIA_URL = /media/
- OIDC can be toggled on/off without code changes (OIDC_ENABLED env var)
- ALLOWED_HOSTS must include production IP/domain
