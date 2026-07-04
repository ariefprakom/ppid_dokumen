from django.contrib import admin
from .models import UnitKerja, KategoriInformasi, DokumenPPID


@admin.register(UnitKerja)
class UnitKerjaAdmin(admin.ModelAdmin):
    list_display = ["nama"]
    search_fields = ["nama"]


@admin.register(KategoriInformasi)
class KategoriInformasiAdmin(admin.ModelAdmin):
    list_display = ["nama"]
    search_fields = ["nama"]


@admin.register(DokumenPPID)
class DokumenPPIDAdmin(admin.ModelAdmin):
    list_display = [
        "tentang", "unit", "kategori_informasi", "tahun",
        "klasifikasi", "status", "sumber_file", "tanggal_terbit", "diunduh",
    ]
    list_filter = ["unit", "kategori_informasi", "klasifikasi", "status", "tahun"]
    search_fields = ["tentang", "detail", "nomor", "penulis"]
    date_hierarchy = "tanggal_terbit"
    fieldsets = (
        (None, {
            "fields": (
                "unit", "kategori_informasi", "nomor", "tahun",
                "tentang", "detail", "klasifikasi", "status",
            )
        }),
        ("Sumber Dokumen (pilih salah satu)", {
            "description": "Upload file <strong>ATAU</strong> isi URL file eksternal. Tidak boleh keduanya kosong atau keduanya terisi.",
            "fields": ("file", "file_url"),
        }),
        ("Metadata", {
            "fields": ("penulis", "tanggal_terbit", "diunduh"),
        }),
    )

    @admin.display(description="Sumber")
    def sumber_file(self, obj):
        if obj.file_url:
            return "🔗 Eksternal"
        if obj.file:
            return "📄 Upload"
        return "-"
