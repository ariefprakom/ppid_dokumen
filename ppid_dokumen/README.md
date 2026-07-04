# App `ppid_dokumen`

## 1. Salin folder
Salin folder `ppid_dokumen/` ini ke root project Django Anda (sejajar dengan app lain).

## 2. Daftarkan app
Di `settings.py`:
```python
INSTALLED_APPS = [
    ...
    "ppid_dokumen",
]
```

## 3. Sambungkan URL
Di `urls.py` project utama:
```python
from django.urls import path, include

urlpatterns = [
    ...
    path("ppid/", include("ppid_dokumen.urls")),
]
```

## 4. Migrasi
```bash
python manage.py makemigrations ppid_dokumen
python manage.py migrate
```

## 5. Media file
Pastikan `MEDIA_URL` dan `MEDIA_ROOT` sudah dikonfigurasi di `settings.py` untuk menyimpan file upload dokumen, dan di-serve saat development:
```python
# settings.py
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```
```python
# urls.py (development only)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 6. Isi data awal
Buka `/admin/` lalu tambahkan data `Unit Kerja` (mis. Fak. Dakwah dan Komunikasi, Fak. Sains dan Teknologi, dst) dan `Kategori Informasi` (Serta Merta, Berkala, Tersedia Setiap Saat, Dikecualikan) sebelum mulai upload dokumen.

## 7. Akses
Halaman daftar dokumen: `/ppid/`
Link ini yang nantinya ditempel di website PPID (https://ppid.ar-raniry.ac.id/).

## Catatan penyesuaian
- Kolom `klasifikasi` dan `kategori_informasi` mengikuti terminologi UU Keterbukaan Informasi Publik (KIP). Sesuaikan pilihan di `KategoriInformasi` dengan kategori resmi yang dipakai PPID UIN Ar-Raniry.
- Jika nanti butuh alur upload dengan approval (draft -> diverifikasi -> publish), tambahkan field `status_review` terpisah dari `status` (yang saat ini untuk Berlaku/Kadaluarsa).
- Script migrasi/metadata-scanning Anda yang sudah ada bisa dipakai untuk mengisi data awal `DokumenPPID` secara massal (bulk_create) berdasarkan hasil scan folder dokumen.
