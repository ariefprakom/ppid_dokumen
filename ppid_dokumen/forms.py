import datetime
from django import forms
from .models import Organisasi, UnitOrganisasi


class CDNUploadForm(forms.Form):
    """Form untuk upload file ke CDN via SFTP."""
    tahun = forms.IntegerField(
        initial=datetime.date.today().year,
        help_text="Tahun folder tujuan",
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
        value = self.cleaned_data["tahun"]
        if value < 2000 or value > 2100:
            raise forms.ValidationError("Tahun tidak valid.")
        return str(value)

    def clean_organisasi(self):
        """Return pk sebagai string untuk kompatibilitas dengan view."""
        org = self.cleaned_data["organisasi"]
        return org.pk

    def clean_unit_organisasi(self):
        unit = self.cleaned_data.get("unit_organisasi")
        if unit:
            return unit.pk
        return ""
