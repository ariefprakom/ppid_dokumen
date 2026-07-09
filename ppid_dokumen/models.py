from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class UnitKerja(models.Model):
    """PPID Pelaksana / unit kerja, mis. Fakultas, Lembaga, Biro."""
    nama = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = "Unit Kerja"
        verbose_name_plural = "Unit Kerja"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class KategoriInformasi(models.Model):
    """Kategori informasi publik sesuai UU KIP:
    Serta Merta, Berkala, Tersedia Setiap Saat, Dikecualikan, dsb."""
    nama = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Kategori Informasi"
        verbose_name_plural = "Kategori Informasi"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class TahunDokumen(models.Model):
    """Tahun untuk struktur folder CDN (level 1)."""
    tahun = models.PositiveIntegerField(
        "Tahun", unique=True,
        help_text="Tahun folder di CDN, contoh: 2025, 2026"
    )

    class Meta:
        verbose_name = "Tahun Dokumen"
        verbose_name_plural = "Tahun Dokumen"
        ordering = ["-tahun"]

    def __str__(self):
        return str(self.tahun)


class Organisasi(models.Model):
    """Organisasi / bidang untuk struktur folder CDN (level 2)."""
    nama = models.CharField(
        "Nama Organisasi", max_length=100, unique=True,
        help_text="Nama folder di CDN, contoh: AAKK, AUPK, LP2M, PPID, SPI"
    )
    deskripsi = models.CharField(
        "Deskripsi", max_length=255, blank=True,
        help_text="Nama lengkap, contoh: Akademik dan Kemahasiswaan"
    )

    class Meta:
        verbose_name = "Organisasi"
        verbose_name_plural = "Organisasi"
        ordering = ["nama"]

    def __str__(self):
        if self.deskripsi:
            return f"{self.nama} - {self.deskripsi}"
        return self.nama


class UnitOrganisasi(models.Model):
    """Unit di bawah Organisasi untuk struktur folder CDN (level 3)."""
    organisasi = models.ForeignKey(
        Organisasi, on_delete=models.CASCADE, related_name="units"
    )
    nama = models.CharField(
        "Nama Unit", max_length=100,
        help_text="Nama folder unit di CDN, contoh: Administrasi Akademik"
    )
    deskripsi = models.CharField(
        "Deskripsi", max_length=255, blank=True,
    )

    class Meta:
        verbose_name = "Unit Organisasi"
        verbose_name_plural = "Unit Organisasi"
        ordering = ["organisasi__nama", "nama"]
        unique_together = [("organisasi", "nama")]

    def __str__(self):
        return f"{self.organisasi.nama} / {self.nama}"


class DokumenPPID(models.Model):
    KLASIFIKASI_CHOICES = [
        ("umum", "Umum"),
        ("terbatas", "Terbatas"),
        ("dikecualikan", "Dikecualikan"),
    ]

    STATUS_CHOICES = [
        ("berlaku", "Berlaku"),
        ("kadaluarsa", "Kadaluarsa"),
        ("proses", "Dalam Proses"),
    ]

    unit = models.ForeignKey(
        UnitKerja, on_delete=models.PROTECT, related_name="dokumen"
    )
    kategori_informasi = models.ForeignKey(
        KategoriInformasi, on_delete=models.PROTECT, related_name="dokumen"
    )
    nomor = models.CharField("Nomor", max_length=100, blank=True)
    tahun = models.PositiveIntegerField("Tahun")
    tentang = models.CharField("Tentang", max_length=255)
    detail = models.TextField("Detail", blank=True)
    klasifikasi = models.CharField(
        max_length=20, choices=KLASIFIKASI_CHOICES, default="umum"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="berlaku"
    )
    file = models.FileField("File Upload", upload_to="dokumen_ppid/%Y/", blank=True)
    file_url = models.URLField(
        "URL File Eksternal", max_length=500, blank=True,
        help_text="Isi URL jika file sudah tersimpan di penyimpanan lain (Google Drive, cloud storage, dsb.)"
    )
    penulis = models.CharField("Penulis/Pengunggah", max_length=100)
    tanggal_terbit = models.DateTimeField("Tanggal Terbit", auto_now_add=False)
    diunduh = models.PositiveIntegerField("Jumlah Diunduh", default=0)

    class Meta:
        verbose_name = "Dokumen PPID"
        verbose_name_plural = "Dokumen PPID"
        ordering = ["-tanggal_terbit"]

    def __str__(self):
        return f"{self.tentang} ({self.tahun})"

    def clean(self):
        super().clean()
        if not self.file and not self.file_url:
            raise ValidationError(
                "Harus mengisi salah satu: upload file atau URL file eksternal."
            )
        if self.file and self.file_url:
            raise ValidationError(
                "Pilih salah satu saja: upload file ATAU URL file eksternal, tidak keduanya."
            )

    @property
    def is_external(self):
        """True jika dokumen menggunakan link eksternal."""
        return bool(self.file_url)

    @property
    def download_url(self):
        """URL untuk mengakses/mengunduh dokumen."""
        if self.file_url:
            return self.file_url
        if self.file:
            return reverse("ppid_dokumen:download", kwargs={"pk": self.pk})
        return ""

    def get_absolute_url(self):
        return reverse("ppid_dokumen:detail", kwargs={"pk": self.pk})


class CDNActivityLog(models.Model):
    """Log aktivitas operasi file di CDN (upload, rename, hapus)."""

    ACTION_CHOICES = [
        ("upload", "Upload"),
        ("rename", "Rename"),
        ("delete", "Hapus"),
    ]

    user = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cdn_logs",
        verbose_name="User",
    )
    action = models.CharField("Aksi", max_length=10, choices=ACTION_CHOICES)
    file_path = models.CharField("Path File", max_length=500)
    file_name = models.CharField("Nama File", max_length=255)
    detail = models.TextField(
        "Detail", blank=True,
        help_text="Info tambahan, misal: nama baru saat rename, jumlah file saat upload"
    )
    timestamp = models.DateTimeField("Waktu", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP Address", null=True, blank=True)

    class Meta:
        verbose_name = "Log Aktivitas CDN"
        verbose_name_plural = "Log Aktivitas CDN"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.get_action_display()}] {self.file_name} - {self.user} ({self.timestamp:%Y-%m-%d %H:%M})"


class JenisDokumen(models.Model):
    """Referensi jenis dokumen sesuai UU KIP.
    Contoh: Wajib Berkala, Serta Merta, Tersedia Setiap Saat, Dikecualikan."""
    nama = models.CharField("Nama Jenis", max_length=100, unique=True)
    slug = models.SlugField(
        "Slug URL", max_length=100, unique=True, default="",
        help_text="URL-friendly identifier, contoh: wajib-berkala. Otomatis di-generate jika kosong."
    )
    deskripsi = models.TextField("Deskripsi", blank=True)
    urutan = models.PositiveIntegerField(
        "Urutan Tampil", default=0,
        help_text="Urutan tampil di dropdown dan halaman publik (kecil = di atas)"
    )

    class Meta:
        verbose_name = "Jenis Dokumen"
        verbose_name_plural = "Jenis Dokumen"
        ordering = ["urutan", "nama"]

    def __str__(self):
        return self.nama

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nama)
        super().save(*args, **kwargs)


class CDNFile(models.Model):
    """Metadata file yang tersimpan di CDN.
    Merekam path, jenis dokumen, organisasi, dan info lainnya."""

    file_path = models.CharField(
        "Path di CDN", max_length=255, unique=True,
        help_text="Path relatif dari root CDN, misal: 2025/AUPK/dokumen.pdf"
    )
    file_name = models.CharField("Nama File", max_length=255)
    jenis_dokumen = models.ForeignKey(
        JenisDokumen, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cdn_files",
        verbose_name="Jenis Dokumen",
    )
    organisasi = models.ForeignKey(
        Organisasi, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cdn_files",
        verbose_name="Organisasi",
    )
    unit_organisasi = models.ForeignKey(
        UnitOrganisasi, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cdn_files",
        verbose_name="Unit Organisasi",
    )
    tahun = models.CharField("Tahun", max_length=4, blank=True)
    deskripsi = models.CharField(
        "Deskripsi/Keterangan", max_length=500, blank=True,
        help_text="Keterangan singkat tentang isi dokumen"
    )
    uploaded_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cdn_uploads",
        verbose_name="Diupload oleh",
    )
    uploaded_at = models.DateTimeField("Waktu Upload", auto_now_add=True)
    file_size = models.PositiveIntegerField("Ukuran (bytes)", default=0)

    class Meta:
        verbose_name = "File CDN"
        verbose_name_plural = "File CDN"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name

    @property
    def cdn_url(self):
        """URL publik file di CDN."""
        from decouple import config
        base_url = config('CDN_BASE_URL', default='')
        return f"{base_url}/{self.file_path}"
