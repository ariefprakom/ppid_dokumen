import paramiko, stat
from decouple import config
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import DokumenPPID, UnitKerja, KategoriInformasi


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
    """Rekursif membaca semua file dari SFTP."""
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
            # Folder = bagian path sebelum filename
            folder = "/".join(rel.split("/")[:-1]) if "/" in rel else ""
            # Ekstensi file
            ext = entry.filename.rsplit(".", 1)[-1].lower() if "." in entry.filename else ""
            files.append({
                "name": entry.filename,
                "folder": folder,
                "path": rel,
                "url": f"{base_url}/{rel}",
                "size": entry.st_size,
                "ext": ext,
            })
    return files


def cdn_files_table(request):
    """View tabel semua file CDN dengan filter (folder, ekstensi, kata kunci)."""
    import time

    host = config('SFTP_HOST')
    port = config('SFTP_PORT', default=22, cast=int)
    username = config('SFTP_USERNAME')
    password = config('SFTP_PASSWORD')
    base_url = config('CDN_BASE_URL')
    root_path = config('CDN_ROOT_PATH')

    # Koneksi SFTP
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        all_files = _sftp_walk(sftp, root_path, base_url, root_path)
    finally:
        sftp.close()
        transport.close()

    # Kumpulkan opsi filter
    folder_set = sorted(set(f["folder"] for f in all_files if f["folder"]))
    ext_set = sorted(set(f["ext"] for f in all_files if f["ext"]))

    # Ambil filter dari query string
    filter_folder = request.GET.get("folder", "")
    filter_ext = request.GET.get("ext", "")
    filter_q = request.GET.get("q", "")

    # Terapkan filter
    filtered = all_files
    if filter_folder:
        filtered = [f for f in filtered if f["folder"] == filter_folder]
    if filter_ext:
        filtered = [f for f in filtered if f["ext"] == filter_ext]
    if filter_q:
        q_lower = filter_q.lower()
        filtered = [f for f in filtered if q_lower in f["name"].lower()]

    context = {
        "files": filtered,
        "total_files": len(all_files),
        "folder_list": folder_set,
        "ext_list": ext_set,
        "filter_values": {
            "folder": filter_folder,
            "ext": filter_ext,
            "q": filter_q,
        },
    }
    return render(request, "ppid_dokumen/cdn_files_table.html", context)
