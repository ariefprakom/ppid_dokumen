from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.utils.html import format_html
from decouple import config

from .models import UnitKerja, KategoriInformasi, DokumenPPID, Organisasi, UnitOrganisasi
from .forms import CDNUploadForm
from .views import _get_sftp_connection, _sftp_mkdir_p


# ============================================================
# Sembunyikan model yang tidak perlu tampil di admin
# ============================================================

# Tetap register tapi tidak tampil di index
class HiddenModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False


admin.site.register(UnitKerja, HiddenModelAdmin)
admin.site.register(KategoriInformasi, HiddenModelAdmin)
admin.site.register(DokumenPPID, HiddenModelAdmin)


# ============================================================
# Model yang tampil: Organisasi & Unit Organisasi
# ============================================================

class UnitOrganisasiInline(admin.TabularInline):
    model = UnitOrganisasi
    extra = 1


@admin.register(Organisasi)
class OrganisasiAdmin(admin.ModelAdmin):
    list_display = ["nama", "deskripsi", "jumlah_unit"]
    search_fields = ["nama", "deskripsi"]
    inlines = [UnitOrganisasiInline]

    @admin.display(description="Jumlah Unit")
    def jumlah_unit(self, obj):
        return obj.units.count()


@admin.register(UnitOrganisasi)
class UnitOrganisasiAdmin(admin.ModelAdmin):
    list_display = ["nama", "organisasi", "deskripsi"]
    list_filter = ["organisasi"]
    search_fields = ["nama", "deskripsi"]


# ============================================================
# Custom Admin View: Upload ke CDN
# ============================================================

class CDNUploadAdminView:
    """Custom admin view untuk upload file ke CDN via SFTP."""

    @staticmethod
    def get_urls():
        return [
            path(
                "cdn-upload/",
                admin.site.admin_view(CDNUploadAdminView.upload_view),
                name="cdn_upload",
            ),
            path(
                "cdn-upload/units/<int:organisasi_id>/",
                admin.site.admin_view(CDNUploadAdminView.get_units_json),
                name="cdn_upload_units",
            ),
        ]

    @staticmethod
    def get_units_json(request, organisasi_id):
        """API endpoint: daftar unit organisasi berdasarkan organisasi_id."""
        units = UnitOrganisasi.objects.filter(
            organisasi_id=organisasi_id
        ).values_list("id", "nama")
        data = [{"id": uid, "nama": nama} for uid, nama in units]
        return JsonResponse(data, safe=False)

    @staticmethod
    def upload_view(request):
        root_path = config('CDN_ROOT_PATH')
        base_url = config('CDN_BASE_URL')

        organisasi_list = Organisasi.objects.all()
        unit_list = UnitOrganisasi.objects.select_related("organisasi").all()

        if request.method == "POST":
            form = CDNUploadForm(request.POST, request.FILES)
            if form.is_valid():
                tahun = form.cleaned_data["tahun"]
                organisasi_id = form.cleaned_data["organisasi"]
                unit_id = form.cleaned_data.get("unit_organisasi")

                # Ambil nama folder dari database
                try:
                    org = Organisasi.objects.get(pk=organisasi_id)
                    org_folder = org.nama
                except Organisasi.DoesNotExist:
                    messages.error(request, "Organisasi tidak ditemukan.")
                    return redirect("admin:cdn_upload")

                unit_folder = ""
                if unit_id:
                    try:
                        unit = UnitOrganisasi.objects.get(pk=unit_id)
                        unit_folder = unit.nama
                    except UnitOrganisasi.DoesNotExist:
                        pass

                # Bangun path tujuan
                if unit_folder:
                    remote_dir = f"{root_path}/{tahun}/{org_folder}/{unit_folder}"
                    public_dir = f"{base_url}/{tahun}/{org_folder}/{unit_folder}"
                else:
                    remote_dir = f"{root_path}/{tahun}/{org_folder}"
                    public_dir = f"{base_url}/{tahun}/{org_folder}"

                files = request.FILES.getlist("file")
                uploaded = []
                errors = []

                try:
                    transport, sftp = _get_sftp_connection()
                    try:
                        _sftp_mkdir_p(sftp, remote_dir)

                        for f in files:
                            remote_file = f"{remote_dir}/{f.name}"
                            try:
                                with sftp.open(remote_file, "wb") as remote_fh:
                                    for chunk in f.chunks():
                                        remote_fh.write(chunk)
                                uploaded.append(f.name)
                            except Exception as e:
                                errors.append(f"{f.name}: {e}")
                    finally:
                        sftp.close()
                        transport.close()
                except Exception as e:
                    messages.error(request, f"Gagal koneksi SFTP: {e}")
                    return redirect("admin:cdn_upload")

                if uploaded:
                    file_list = ", ".join(uploaded)
                    messages.success(
                        request,
                        f"✅ Berhasil upload {len(uploaded)} file ke {public_dir}/: {file_list}"
                    )
                if errors:
                    for err in errors:
                        messages.error(request, f"❌ Gagal: {err}")

                return redirect("admin:cdn_upload")
        else:
            form = CDNUploadForm()

        context = {
            **admin.site.each_context(request),
            "title": "Upload File ke CDN",
            "form": form,
            "organisasi_list": organisasi_list,
            "unit_list": unit_list,
        }
        return render(request, "admin/cdn_upload.html", context)


# ============================================================
# Custom admin index template: tambah link Upload CDN
# ============================================================

# Override admin site header & tambah custom link
admin.site.site_header = "PPID UIN Ar-Raniry"
admin.site.site_title = "PPID Admin"
admin.site.index_title = "Administrasi Data"


# Daftarkan URL custom ke admin
original_get_urls = admin.AdminSite.get_urls


def custom_admin_urls(self):
    custom_urls = CDNUploadAdminView.get_urls()
    return custom_urls + original_get_urls(self)


admin.AdminSite.get_urls = custom_admin_urls
