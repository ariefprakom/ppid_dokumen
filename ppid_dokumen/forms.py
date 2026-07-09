from django import forms
from .models import Organisasi, UnitOrganisasi, TahunDokumen, JenisDokumen


class CDNUploadForm(forms.Form):
    """Form untuk upload file ke CDN via SFTP."""
    tahun = forms.ModelChoiceField(
        queryset=TahunDokumen.objects.all(),
        empty_label="-- Pilih Tahun --",
        help_text="Pilih tahun (folder level 1)",
    )
    organisasi = forms.ModelChoiceField(
        queryset=Organisasi.objects.all(),
        empty_label="-- Pilih Organisasi --",
        help_text="Pilih organisasi (folder level 2)",
    )
    unit_organisasi = forms.ModelChoiceField(
        queryset=UnitOrganisasi.objects.all(),
        required=False,
        empty_label="-- Pilih Unit (opsional) --",
        help_text="Pilih unit organisasi (folder level 3)",
    )
    jenis_dokumen = forms.ModelChoiceField(
        queryset=JenisDokumen.objects.all(),
        required=False,
        empty_label="-- Pilih Jenis Dokumen --",
        help_text="Jenis dokumen sesuai kategori informasi publik",
    )
    deskripsi = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Keterangan singkat tentang isi dokumen (opsional)",
    )
    file = forms.FileField(
        required=False,
        help_text="Pilih file yang akan diupload ke CDN",
    )
    external_url = forms.URLField(
        required=False,
        max_length=500,
        help_text="Atau isi URL link dokumen (Google Drive, dsb). Pilih salah satu: upload file ATAU isi link.",
    )
    link_nama = forms.CharField(
        required=False,
        max_length=255,
        help_text="Nama tampilan untuk link (wajib jika pakai URL). Contoh: SK Rektor 2025.pdf",
    )

    def clean(self):
        cleaned_data = super().clean()
        file = self.files.get("file") or cleaned_data.get("file")
        url = cleaned_data.get("external_url", "").strip()
        link_nama = cleaned_data.get("link_nama", "").strip()

        if not file and not url:
            raise forms.ValidationError(
                "Harus mengisi salah satu: upload file atau isi URL link."
            )
        if file and url:
            raise forms.ValidationError(
                "Pilih salah satu saja: upload file ATAU isi URL link, tidak keduanya."
            )
        if url and not link_nama:
            self.add_error("link_nama", "Nama link wajib diisi jika menggunakan URL.")

        return cleaned_data

    def clean_tahun(self):
        tahun_obj = self.cleaned_data["tahun"]
        return str(tahun_obj.tahun)

    def clean_organisasi(self):
        """Return pk untuk kompatibilitas dengan view."""
        org = self.cleaned_data["organisasi"]
        return org.pk

    def clean_unit_organisasi(self):
        unit = self.cleaned_data.get("unit_organisasi")
        if unit:
            return unit.pk
        return ""
