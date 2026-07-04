# Tech Stack

## Framework
- Python + Django 5.2
- Django's built-in template engine (DTL)

## Database
- MySQL (development: localhost:3307, db name `ppid_dokumen`, user `root`)
- SQLite available as commented-out fallback

## Frontend
- Server-rendered HTML templates (no SPA framework)
- jQuery 3.7 + DataTables 1.13 for table interactions (CDN-loaded)
- JSZip for Excel export via DataTables Buttons
- Inline CSS in templates (no build pipeline)

## File Storage
- Django FileField with MEDIA_ROOT = `<project>/media/`
- Upload path pattern: `dokumen_ppid/%Y/`

## Environment
- Python virtualenv at `venv/`
- No requirements.txt or pyproject.toml currently checked in

## Common Commands

```bash
# Activate virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Run tests
python manage.py test
```

## Key Settings
- DEBUG = True (development)
- MEDIA_URL = /media/
- Static files served by Django's dev server
- No third-party Django packages (no DRF, no crispy-forms, etc.)
