from django import forms
from .models import Organisasi, UnitOrganisasi, TahunDokumen


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
    file = forms.FileField(
        help_text="Pilih file yang akan diupload ke CDN",
    )

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
