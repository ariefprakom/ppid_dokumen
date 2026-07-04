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
