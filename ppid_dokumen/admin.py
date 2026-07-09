from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.utils.html import format_html
from decouple import config

from .models import UnitKerja, KategoriInformasi, DokumenPPID, Organisasi, UnitOrganisasi, CDNActivityLog, TahunDokumen, JenisDokumen, CDNFile
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
# Model yang tampil: Tahun, Organisasi & Unit Organisasi
# ============================================================

@admin.register(TahunDokumen)
class TahunDokumenAdmin(admin.ModelAdmin):
    list_display = ["tahun"]
    search_fields = ["tahun"]
    ordering = ["-tahun"]


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


@admin.register(CDNActivityLog)
class CDNActivityLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "file_name", "file_path", "ip_address"]
    list_filter = ["action", "user", "timestamp"]
    search_fields = ["file_name", "file_path", "detail", "user__username"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "user", "action", "file_path", "file_name",
        "detail", "timestamp", "ip_address",
    ]
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Hanya superuser yang bisa hapus log
        return request.user.is_superuser


@admin.register(JenisDokumen)
class JenisDokumenAdmin(admin.ModelAdmin):
    list_display = ["nama", "slug", "deskripsi", "urutan"]
    search_fields = ["nama", "deskripsi"]
    list_editable = ["urutan"]
    prepopulated_fields = {"slug": ("nama",)}


@admin.register(CDNFile)
class CDNFileAdmin(admin.ModelAdmin):
    list_display = ["file_name", "jenis_dokumen", "organisasi", "unit_organisasi", "tahun", "is_link", "uploaded_by", "uploaded_at"]
    list_filter = ["jenis_dokumen", "organisasi", "tahun"]
    search_fields = ["file_name", "file_path", "deskripsi", "external_url"]
    date_hierarchy = "uploaded_at"
    readonly_fields = ["file_path", "file_name", "file_size", "uploaded_by", "uploaded_at", "external_url"]

    @admin.display(description="Link?", boolean=True)
    def is_link(self, obj):
        return bool(obj.external_url)

    def delete_model(self, request, obj):
        """Log saat hapus CDNFile dari admin."""
        from .views import _log_cdn_activity
        _log_cdn_activity(
            request, "delete", obj.file_path, obj.file_name,
            detail=f"Dihapus dari admin (CDNFile record)"
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Log saat hapus banyak CDNFile dari admin."""
        from .views import _log_cdn_activity
        for obj in queryset:
            _log_cdn_activity(
                request, "delete", obj.file_path, obj.file_name,
                detail=f"Bulk delete dari admin"
            )
        super().delete_queryset(request, queryset)

    def has_module_permission(self, request):
        return True


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
            path(
                "cdn-manage/",
                admin.site.admin_view(CDNManageAdminView.manage_view),
                name="cdn_manage",
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
        tahun_list = TahunDokumen.objects.all()

        if request.method == "POST":
            form = CDNUploadForm(request.POST, request.FILES)
            if form.is_valid():
                tahun = form.cleaned_data["tahun"]
                organisasi_id = form.cleaned_data["organisasi"]
                unit_id = form.cleaned_data.get("unit_organisasi")
                external_url = form.cleaned_data.get("external_url", "").strip()
                link_nama = form.cleaned_data.get("link_nama", "").strip()

                # Ambil nama folder dari database
                try:
                    org = Organisasi.objects.get(pk=organisasi_id)
                    org_folder = org.nama
                except Organisasi.DoesNotExist:
                    messages.error(request, "Organisasi tidak ditemukan.")
                    return redirect("admin:cdn_upload")

                unit_folder = ""
                unit_obj = None
                if unit_id:
                    try:
                        unit_obj = UnitOrganisasi.objects.get(pk=unit_id)
                        unit_folder = unit_obj.nama
                    except UnitOrganisasi.DoesNotExist:
                        pass

                jenis_dok = form.cleaned_data.get("jenis_dokumen")
                deskripsi = form.cleaned_data.get("deskripsi", "")

                # ========== MODE LINK ==========
                if external_url:
                    # Bangun path virtual (untuk referensi, bukan path fisik)
                    if unit_folder:
                        virtual_path = f"{tahun}/{org_folder}/{unit_folder}/{link_nama}"
                    else:
                        virtual_path = f"{tahun}/{org_folder}/{link_nama}"

                    CDNFile.objects.update_or_create(
                        file_path=virtual_path,
                        defaults={
                            "file_name": link_nama,
                            "jenis_dokumen": jenis_dok,
                            "organisasi": org,
                            "unit_organisasi": unit_obj,
                            "tahun": tahun,
                            "deskripsi": deskripsi,
                            "uploaded_by": request.user,
                            "file_size": 0,
                            "external_url": external_url,
                        }
                    )

                    # Invalidate cache
                    from django.core.cache import cache
                    cache.delete("cdn_files_all")

                    messages.success(
                        request,
                        f"✅ Link berhasil disimpan: {link_nama} → {external_url}"
                    )
                    from .views import _log_cdn_activity
                    _log_cdn_activity(
                        request, "upload_link", virtual_path, link_nama,
                        detail=f"Link eksternal: {external_url}"
                    )
                    return redirect("admin:cdn_upload")

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
                    # Invalidate cache
                    from django.core.cache import cache
                    cache.delete("cdn_files_all")

                    # Simpan metadata CDNFile
                    for fname in uploaded:
                        rel_path = f"{remote_dir}/{fname}"[len(config('CDN_ROOT_PATH')):].lstrip("/")
                        # Cari ukuran file dari FILES
                        file_size = 0
                        for f in files:
                            if f.name == fname:
                                file_size = f.size
                                break
                        CDNFile.objects.update_or_create(
                            file_path=rel_path,
                            defaults={
                                "file_name": fname,
                                "jenis_dokumen": jenis_dok,
                                "organisasi": org,
                                "unit_organisasi": unit_obj,
                                "tahun": tahun,
                                "deskripsi": deskripsi,
                                "uploaded_by": request.user,
                                "file_size": file_size,
                            }
                        )

                    # Log aktivitas upload
                    from .views import _log_cdn_activity
                    for fname in uploaded:
                        rel_path = f"{remote_dir}/{fname}"[len(config('CDN_ROOT_PATH')):].lstrip("/")
                        _log_cdn_activity(
                            request, "upload", rel_path, fname,
                            detail=f"Upload ke {public_dir}/"
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
            "tahun_list": tahun_list,
            "organisasi_list": organisasi_list,
            "unit_list": unit_list,
            "jenis_dokumen_list": JenisDokumen.objects.all(),
        }
        return render(request, "admin/cdn_upload.html", context)


# ============================================================
# Custom Admin View: Kelola File CDN (Delete / Rename)
# ============================================================

class CDNManageAdminView:
    """Admin view untuk melihat, menghapus, dan rename file di CDN."""

    @staticmethod
    def manage_view(request):
        from .views import _get_sftp_connection, _sftp_walk
        root_path = config('CDN_ROOT_PATH')
        base_url = config('CDN_BASE_URL')

        transport, sftp = _get_sftp_connection()
        try:
            # Ambil semua folder level-1
            top_folders = []
            for entry in sftp.listdir_attr(root_path):
                import stat as stat_mod
                if stat_mod.S_ISDIR(entry.st_mode):
                    top_folders.append(entry.filename)

            all_files = _sftp_walk(sftp, root_path, base_url, root_path)
        finally:
            sftp.close()
            transport.close()

        # Filter
        tahun_set = sorted(top_folders, reverse=True)
        organisasi_set = sorted(set(f["organisasi"] for f in all_files if f["organisasi"]))

        filter_tahun = request.GET.get("tahun", "")
        filter_organisasi = request.GET.get("organisasi", "")
        filter_unit = request.GET.get("unit", "")
        filter_q = request.GET.get("q", "")

        filtered = all_files
        if filter_tahun:
            filtered = [f for f in filtered if f["tahun"] == filter_tahun]
        if filter_organisasi:
            filtered = [f for f in filtered if f["organisasi"] == filter_organisasi]
        if filter_unit:
            filtered = [f for f in filtered if f["unit_organisasi"] == filter_unit]
        if filter_q:
            q_lower = filter_q.lower()
            filtered = [f for f in filtered if q_lower in f["name"].lower()]

        filtered_organisasi_set = sorted(set(
            f["organisasi"] for f in all_files
            if f["organisasi"] and (not filter_tahun or f["tahun"] == filter_tahun)
        ))
        filtered_unit_set = sorted(set(
            f["unit_organisasi"] for f in all_files
            if f["unit_organisasi"]
            and (not filter_tahun or f["tahun"] == filter_tahun)
            and (not filter_organisasi or f["organisasi"] == filter_organisasi)
        ))

        # Ambil metadata jenis dokumen dari CDNFile
        cdn_file_map = {}
        cdn_records = CDNFile.objects.select_related("jenis_dokumen").all()
        for rec in cdn_records:
            cdn_file_map[rec.file_path] = rec.jenis_dokumen_id

        for f in filtered:
            f["jenis_dokumen_id"] = cdn_file_map.get(f["path"], "")

        context = {
            **admin.site.each_context(request),
            "title": "Kelola File CDN",
            "files": filtered,
            "total_files": len(all_files),
            "tahun_list": tahun_set,
            "organisasi_list": filtered_organisasi_set,
            "unit_list": filtered_unit_set,
            "jenis_dokumen_list": JenisDokumen.objects.all(),
            "filter_values": {
                "tahun": filter_tahun,
                "organisasi": filter_organisasi,
                "unit": filter_unit,
                "q": filter_q,
            },
        }
        return render(request, "admin/cdn_manage.html", context)


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
