import paramiko, stat
from decouple import config
from django.core.cache import cache
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required

from .models import DokumenPPID, UnitKerja, KategoriInformasi, CDNActivityLog

# Cache timeout untuk data CDN (5 menit)
CDN_CACHE_TIMEOUT = 300


def _get_client_ip(request):
    """Ambil IP address client dari request."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _log_cdn_activity(request, action, file_path, file_name, detail=""):
    """Catat aktivitas CDN ke database."""
    CDNActivityLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        file_path=file_path,
        file_name=file_name,
        detail=detail,
        ip_address=_get_client_ip(request),
    )


def _get_sftp_connection():
    """Buat koneksi SFTP dan kembalikan (transport, sftp)."""
    host = config('SFTP_HOST')
    port = config('SFTP_PORT', default=22, cast=int)
    username = config('SFTP_USERNAME')
    password = config('SFTP_PASSWORD')
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return transport, sftp


def _sftp_mkdir_p(sftp, remote_path):
    """Buat folder secara rekursif di SFTP (seperti mkdir -p)."""
    dirs_to_create = []
    path = remote_path
    while True:
        try:
            sftp.stat(path)
            break  # folder sudah ada
        except IOError:
            dirs_to_create.append(path)
            path = "/".join(path.rstrip("/").rsplit("/", 1)[:-1]) or "/"
            if path == "/":
                break
    for d in reversed(dirs_to_create):
        try:
            sftp.mkdir(d)
        except IOError:
            pass  # mungkin sudah ada (race condition)


def document_list(request):
    qs = DokumenPPID.objects.select_related("unit", "kategori_informasi").all()

    unit_id = request.GET.get("unit")
    kategori_id = request.GET.get("kategori")
    klasifikasi = request.GET.get("klasifikasi")
    status = request.GET.get("status")
    tahun = request.GET.get("tahun")
    nomor = request.GET.get("nomor")
    kata_kunci = request.GET.get("q")

    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    if kategori_id:
        qs = qs.filter(kategori_informasi_id=kategori_id)
    if klasifikasi:
        qs = qs.filter(klasifikasi=klasifikasi)
    if status:
        qs = qs.filter(status=status)
    if tahun:
        qs = qs.filter(tahun=tahun)
    if nomor:
        qs = qs.filter(nomor__icontains=nomor)
    if kata_kunci:
        qs = qs.filter(
            Q(tentang__icontains=kata_kunci) | Q(detail__icontains=kata_kunci)
        )

    tahun_list = (
        DokumenPPID.objects.order_by("-tahun")
        .values_list("tahun", flat=True)
        .distinct()
    )

    context = {
        "dokumen_list": qs,
        "unit_list": UnitKerja.objects.all(),
        "kategori_list": KategoriInformasi.objects.all(),
        "klasifikasi_choices": DokumenPPID.KLASIFIKASI_CHOICES,
        "status_choices": DokumenPPID.STATUS_CHOICES,
        "tahun_list": tahun_list,
        "filter_values": {
            "unit": unit_id or "",
            "kategori": kategori_id or "",
            "klasifikasi": klasifikasi or "",
            "status": status or "",
            "tahun": tahun or "",
            "nomor": nomor or "",
            "q": kata_kunci or "",
        },
    }
    return render(request, "ppid_dokumen/document_list.html", context)


def document_download(request, pk):
    dokumen = get_object_or_404(DokumenPPID, pk=pk)

    # Increment download counter
    dokumen.diunduh += 1
    dokumen.save(update_fields=["diunduh"])

    # Jika file eksternal, redirect ke URL
    if dokumen.file_url:
        return redirect(dokumen.file_url)

    # Jika file upload lokal
    if dokumen.file:
        return FileResponse(
            dokumen.file.open("rb"),
            as_attachment=True,
            filename=dokumen.file.name.split("/")[-1],
        )

    raise Http404("File tidak ditemukan")

def list_sftp_files_html(request):
    host = config('SFTP_HOST')
    port = config('SFTP_PORT', default=22, cast=int)
    username = config('SFTP_USERNAME')
    password = config('SFTP_PASSWORD')
    base_url = config('CDN_BASE_URL')
    root_path = config('CDN_ROOT_PATH')

    # ambil query string ?path=
    relative_path = request.GET.get("path", "").strip("/")
    remote_path = f"{root_path}/{relative_path}" if relative_path else root_path
    public_path = f"{base_url}/{relative_path}" if relative_path else base_url

    # koneksi SFTP
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    items = []
    try:
        for f in sftp.listdir_attr(remote_path):
            is_dir = stat.S_ISDIR(f.st_mode)

            # kalau folder, klik = reload view dgn ?path=subfolder
            if is_dir:
                url = f"?path={relative_path}/{f.filename}".strip("/")
            else:
                url = f"{public_path}/{f.filename}"

            items.append({
                "name": f.filename,
                "is_dir": is_dir,
                "url": url
            })
    finally:
        sftp.close()
        transport.close()

    # breadcrumb
    breadcrumbs = []
    if relative_path:
        parts = relative_path.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[:i+1])
            breadcrumbs.append({
                "name": parts[i],
                "url": f"?path={subpath}"
            })

    return render(request, "ppid_dokumen/list_files.html", {
        "items": items,
        "breadcrumbs": breadcrumbs,
    })


def _sftp_walk(sftp, remote_path, base_url, root_path):
    """Rekursif membaca semua file dari SFTP.
    
    Struktur folder: root / tahun / organisasi / unit_organisasi / file
    """
    files = []
    try:
        entries = sftp.listdir_attr(remote_path)
    except IOError:
        return files

    for entry in entries:
        entry_path = f"{remote_path}/{entry.filename}"
        if stat.S_ISDIR(entry.st_mode):
            files.extend(_sftp_walk(sftp, entry_path, base_url, root_path))
        else:
            # Hitung relative path dari root
            rel = entry_path[len(root_path):].lstrip("/")
            parts = rel.split("/")
            # Parse struktur: tahun/organisasi/unit_organisasi/filename
            tahun = parts[0] if len(parts) > 1 else ""
            organisasi = parts[1] if len(parts) > 2 else ""
            unit_organisasi = parts[2] if len(parts) > 3 else ""
            # Ekstensi file
            ext = entry.filename.rsplit(".", 1)[-1].lower() if "." in entry.filename else ""
            files.append({
                "name": entry.filename,
                "tahun": tahun,
                "organisasi": organisasi,
                "unit_organisasi": unit_organisasi,
                "path": rel,
                "url": f"{base_url}/{rel}",
                "size": entry.st_size,
                "ext": ext,
            })
    return files


def cdn_files_table(request):
    """View tabel semua file CDN dengan filter (tahun, organisasi, unit organisasi)."""

    base_url = config('CDN_BASE_URL')
    root_path = config('CDN_ROOT_PATH')

    # Coba ambil dari cache dulu
    cache_key = "cdn_files_all"
    cached = cache.get(cache_key)

    if cached:
        top_folders, all_files = cached
    else:
        # Koneksi SFTP hanya kalau cache miss
        transport = paramiko.Transport((config('SFTP_HOST'), config('SFTP_PORT', default=22, cast=int)))
        transport.connect(username=config('SFTP_USERNAME'), password=config('SFTP_PASSWORD'))
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            # Ambil semua folder level-1 langsung (termasuk yang kosong)
            top_folders = []
            for entry in sftp.listdir_attr(root_path):
                if stat.S_ISDIR(entry.st_mode):
                    top_folders.append(entry.filename)

            all_files = _sftp_walk(sftp, root_path, base_url, root_path)
        finally:
            sftp.close()
            transport.close()

        # Simpan ke cache
        cache.set(cache_key, (top_folders, all_files), CDN_CACHE_TIMEOUT)

    # Kumpulkan opsi filter — tahun dari folder level-1 (bukan hanya dari file)
    tahun_set = sorted(top_folders, reverse=True)
    organisasi_set = sorted(set(f["organisasi"] for f in all_files if f["organisasi"]))

    # Gabungkan record link eksternal dari database (yang tidak ada file fisik di CDN)
    from .models import CDNFile as CDNFileModel, JenisDokumen
    cdn_records = CDNFileModel.objects.select_related(
        "jenis_dokumen", "organisasi", "unit_organisasi"
    ).all()

    existing_paths = {f["path"] for f in all_files}
    for rec in cdn_records:
        if rec.external_url and rec.file_path not in existing_paths:
            all_files.append({
                "name": rec.file_name,
                "tahun": rec.tahun or "",
                "organisasi": rec.organisasi.nama if rec.organisasi else "",
                "unit_organisasi": rec.unit_organisasi.nama if rec.unit_organisasi else "",
                "path": rec.file_path,
                "url": rec.external_url,
                "size": 0,
                "ext": "link",
            })

    # Build metadata map
    cdn_file_map = {}
    for rec in cdn_records:
        cdn_file_map[rec.file_path] = {
            "jenis_dokumen": rec.jenis_dokumen.nama if rec.jenis_dokumen else "",
            "deskripsi": rec.deskripsi,
        }

    # Ambil filter dari query string
    filter_tahun = request.GET.get("tahun", "")
    filter_organisasi = request.GET.get("organisasi", "")
    filter_unit = request.GET.get("unit", "")
    filter_q = request.GET.get("q", "")

    # Terapkan filter
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

    # Terapkan metadata (jenis dokumen) ke filtered
    for f in filtered:
        meta = cdn_file_map.get(f["path"], {})
        f["jenis_dokumen"] = meta.get("jenis_dokumen", "")
        f["deskripsi_meta"] = meta.get("deskripsi", "")

    # Ambil filter jenis dokumen
    filter_jenis = request.GET.get("jenis", "")
    if filter_jenis:
        filtered = [f for f in filtered if f["jenis_dokumen"] == filter_jenis]

    # Daftar jenis dokumen untuk filter
    jenis_list = list(JenisDokumen.objects.values_list("nama", flat=True))

    # Organisasi yang tersedia setelah filter tahun diterapkan
    filtered_organisasi_set = sorted(set(
        f["organisasi"] for f in all_files
        if f["organisasi"]
        and (not filter_tahun or f["tahun"] == filter_tahun)
    ))

    # Unit organisasi yang tersedia setelah filter tahun & organisasi diterapkan
    filtered_unit_set = sorted(set(
        f["unit_organisasi"] for f in all_files
        if f["unit_organisasi"]
        and (not filter_tahun or f["tahun"] == filter_tahun)
        and (not filter_organisasi or f["organisasi"] == filter_organisasi)
    ))

    context = {
        "files": filtered,
        "total_files": len(all_files),
        "tahun_list": tahun_set,
        "organisasi_list": filtered_organisasi_set,
        "unit_list": filtered_unit_set,
        "jenis_list": jenis_list,
        "filter_values": {
            "tahun": filter_tahun,
            "organisasi": filter_organisasi,
            "unit": filter_unit,
            "q": filter_q,
            "jenis": filter_jenis,
        },
    }
    return render(request, "ppid_dokumen/cdn_files_table.html", context)


def cdn_files_by_jenis(request, slug):
    """View tabel file CDN yang ter-filter berdasarkan jenis dokumen (via slug URL)."""
    from .models import CDNFile as CDNFileModel, JenisDokumen

    jenis = get_object_or_404(JenisDokumen, slug=slug)

    base_url = config('CDN_BASE_URL')
    root_path = config('CDN_ROOT_PATH')

    # Ambil data CDN (dari cache atau SFTP)
    cache_key = "cdn_files_all"
    cached = cache.get(cache_key)

    if cached:
        top_folders, all_files = cached
    else:
        transport = paramiko.Transport((config('SFTP_HOST'), config('SFTP_PORT', default=22, cast=int)))
        transport.connect(username=config('SFTP_USERNAME'), password=config('SFTP_PASSWORD'))
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            top_folders = []
            for entry in sftp.listdir_attr(root_path):
                if stat.S_ISDIR(entry.st_mode):
                    top_folders.append(entry.filename)
            all_files = _sftp_walk(sftp, root_path, base_url, root_path)
        finally:
            sftp.close()
            transport.close()

        cache.set(cache_key, (top_folders, all_files), CDN_CACHE_TIMEOUT)

    # Gabungkan metadata dari CDNFile + tambahkan link eksternal
    cdn_file_map = {}
    cdn_records = CDNFileModel.objects.select_related(
        "jenis_dokumen", "organisasi", "unit_organisasi"
    ).all()
    for rec in cdn_records:
        cdn_file_map[rec.file_path] = {
            "jenis_dokumen": rec.jenis_dokumen.nama if rec.jenis_dokumen else "",
            "deskripsi": rec.deskripsi,
        }

    # Tambahkan record link eksternal (yang tidak ada file fisik di CDN)
    existing_paths = {f["path"] for f in all_files}
    for rec in cdn_records:
        if rec.external_url and rec.file_path not in existing_paths:
            all_files.append({
                "name": rec.file_name,
                "tahun": rec.tahun or "",
                "organisasi": rec.organisasi.nama if rec.organisasi else "",
                "unit_organisasi": rec.unit_organisasi.nama if rec.unit_organisasi else "",
                "path": rec.file_path,
                "url": rec.external_url,
                "size": 0,
                "ext": "link",
            })

    for f in all_files:
        meta = cdn_file_map.get(f["path"], {})
        f["jenis_dokumen"] = meta.get("jenis_dokumen", "")
        f["deskripsi_meta"] = meta.get("deskripsi", "")

    # Filter hanya file dengan jenis dokumen ini
    filtered = [f for f in all_files if f["jenis_dokumen"] == jenis.nama]

    # Sub-filter dari query string
    filter_tahun = request.GET.get("tahun", "")
    filter_organisasi = request.GET.get("organisasi", "")
    filter_unit = request.GET.get("unit", "")
    filter_q = request.GET.get("q", "")

    if filter_tahun:
        filtered = [f for f in filtered if f["tahun"] == filter_tahun]
    if filter_organisasi:
        filtered = [f for f in filtered if f["organisasi"] == filter_organisasi]
    if filter_unit:
        filtered = [f for f in filtered if f["unit_organisasi"] == filter_unit]
    if filter_q:
        q_lower = filter_q.lower()
        filtered = [f for f in filtered if q_lower in f["name"].lower()]

    # Opsi filter berdasarkan file yang ada di jenis ini
    all_jenis_files = [f for f in all_files if f["jenis_dokumen"] == jenis.nama]
    tahun_set = sorted(set(f["tahun"] for f in all_jenis_files if f["tahun"]), reverse=True)
    organisasi_set = sorted(set(f["organisasi"] for f in all_jenis_files if f["organisasi"]))
    unit_set = sorted(set(
        f["unit_organisasi"] for f in all_jenis_files
        if f["unit_organisasi"]
        and (not filter_tahun or f["tahun"] == filter_tahun)
        and (not filter_organisasi or f["organisasi"] == filter_organisasi)
    ))

    context = {
        "files": filtered,
        "total_files": len(all_jenis_files),
        "jenis": jenis,
        "tahun_list": tahun_set,
        "organisasi_list": organisasi_set,
        "unit_list": unit_set,
        "filter_values": {
            "tahun": filter_tahun,
            "organisasi": filter_organisasi,
            "unit": filter_unit,
            "q": filter_q,
        },
    }
    return render(request, "ppid_dokumen/cdn_files_jenis.html", context)


# ============================================================
# CDN File Management: Delete & Rename
# ============================================================

@staff_member_required
@require_POST
def cdn_file_delete(request):
    """Hapus file dari CDN via SFTP."""
    import json
    root_path = config('CDN_ROOT_PATH')

    try:
        body = json.loads(request.body)
        file_path = body.get("path", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Request tidak valid."}, status=400)

    if not file_path:
        return JsonResponse({"success": False, "error": "Path file tidak boleh kosong."}, status=400)

    # Keamanan: pastikan path tidak keluar dari root
    remote_path = f"{root_path}/{file_path}"
    if ".." in file_path or not remote_path.startswith(root_path):
        return JsonResponse({"success": False, "error": "Path tidak valid."}, status=400)

    try:
        transport, sftp = _get_sftp_connection()
        try:
            sftp.remove(remote_path)
        finally:
            sftp.close()
            transport.close()
    except FileNotFoundError:
        return JsonResponse({"success": False, "error": "File tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Gagal menghapus: {e}"}, status=500)

    # Log aktivitas
    file_name = file_path.split("/")[-1]
    _log_cdn_activity(request, "delete", file_path, file_name)

    # Invalidate cache
    cache.delete("cdn_files_all")

    return JsonResponse({"success": True, "message": f"File '{file_path}' berhasil dihapus."})


@staff_member_required
@require_POST
def cdn_file_rename(request):
    """Rename file di CDN via SFTP."""
    import json
    root_path = config('CDN_ROOT_PATH')

    try:
        body = json.loads(request.body)
        old_path = body.get("path", "").strip()
        new_name = body.get("new_name", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Request tidak valid."}, status=400)

    if not old_path or not new_name:
        return JsonResponse({"success": False, "error": "Path dan nama baru harus diisi."}, status=400)

    # Validasi nama file baru (tidak boleh mengandung / atau ..)
    if "/" in new_name or "\\" in new_name or ".." in new_name:
        return JsonResponse({"success": False, "error": "Nama file tidak valid."}, status=400)

    # Keamanan: pastikan path tidak keluar dari root
    remote_old = f"{root_path}/{old_path}"
    if ".." in old_path or not remote_old.startswith(root_path):
        return JsonResponse({"success": False, "error": "Path tidak valid."}, status=400)

    # Bangun path baru (ganti filename, folder tetap sama)
    folder = "/".join(old_path.split("/")[:-1])
    new_path = f"{folder}/{new_name}" if folder else new_name
    remote_new = f"{root_path}/{new_path}"

    try:
        transport, sftp = _get_sftp_connection()
        try:
            # Cek file lama ada
            sftp.stat(remote_old)
            # Cek file baru belum ada
            try:
                sftp.stat(remote_new)
                return JsonResponse(
                    {"success": False, "error": f"File '{new_name}' sudah ada di folder yang sama."},
                    status=409
                )
            except FileNotFoundError:
                pass  # OK, file baru belum ada
            # Rename
            sftp.rename(remote_old, remote_new)
        finally:
            sftp.close()
            transport.close()
    except FileNotFoundError:
        return JsonResponse({"success": False, "error": "File sumber tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Gagal rename: {e}"}, status=500)

    # Log aktivitas
    old_name = old_path.split("/")[-1]
    _log_cdn_activity(
        request, "rename", old_path, old_name,
        detail=f"Rename: {old_name} → {new_name}"
    )

    # Invalidate cache
    cache.delete("cdn_files_all")

    return JsonResponse({
        "success": True,
        "message": f"File berhasil di-rename menjadi '{new_name}'.",
        "new_path": new_path,
    })


@staff_member_required
@require_POST
def cdn_file_set_jenis(request):
    """Set atau ubah jenis dokumen untuk file di CDN."""
    import json
    from .models import CDNFile as CDNFileModel, JenisDokumen, Organisasi, UnitOrganisasi

    try:
        body = json.loads(request.body)
        file_path = body.get("path", "").strip()
        jenis_id = body.get("jenis_id")  # bisa None/kosong untuk hapus jenis
        file_name = body.get("file_name", "")
        tahun = body.get("tahun", "")
        organisasi_nama = body.get("organisasi", "")
        unit_nama = body.get("unit_organisasi", "")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Request tidak valid."}, status=400)

    if not file_path:
        return JsonResponse({"success": False, "error": "Path file tidak boleh kosong."}, status=400)

    try:
        # Resolve jenis dokumen
        jenis_obj = None
        if jenis_id:
            try:
                jenis_obj = JenisDokumen.objects.get(pk=jenis_id)
            except JenisDokumen.DoesNotExist:
                return JsonResponse({"success": False, "error": "Jenis dokumen tidak ditemukan."}, status=404)

        # Resolve organisasi & unit (best effort)
        org_obj = None
        if organisasi_nama:
            org_obj = (
                Organisasi.objects.filter(nama=organisasi_nama).first()
                or Organisasi.objects.filter(nama__icontains=organisasi_nama).first()
            )
        unit_obj = None
        if unit_nama:
            if org_obj:
                unit_obj = UnitOrganisasi.objects.filter(nama=unit_nama, organisasi=org_obj).first()
            else:
                unit_obj = UnitOrganisasi.objects.filter(nama=unit_nama).first()

        # Cek apakah record sudah ada
        existing = CDNFileModel.objects.filter(file_path=file_path).first()

        if existing:
            existing.jenis_dokumen = jenis_obj
            existing.save(update_fields=["jenis_dokumen"])
            cdn_file = existing
        else:
            cdn_file = CDNFileModel.objects.create(
                file_path=file_path,
                file_name=file_name or file_path.split("/")[-1],
                jenis_dokumen=jenis_obj,
                organisasi=org_obj,
                unit_organisasi=unit_obj,
                tahun=tahun,
                uploaded_by=request.user,
            )

        jenis_nama = jenis_obj.nama if jenis_obj else "(tidak ada)"

        # Log aktivitas
        _log_cdn_activity(
            request, "set_jenis", file_path,
            cdn_file.file_name,
            detail=f"Jenis diset ke: {jenis_nama}"
        )

        return JsonResponse({
            "success": True,
            "message": f"Jenis dokumen '{cdn_file.file_name}' diset ke: {jenis_nama}",
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": f"Gagal menyimpan: {e}"}, status=500)
