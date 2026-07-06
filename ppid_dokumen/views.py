import paramiko, stat
from decouple import config
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import DokumenPPID, UnitKerja, KategoriInformasi


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
        # Ambil semua folder level-1 langsung (termasuk yang kosong)
        top_folders = []
        for entry in sftp.listdir_attr(root_path):
            if stat.S_ISDIR(entry.st_mode):
                top_folders.append(entry.filename)

        all_files = _sftp_walk(sftp, root_path, base_url, root_path)
    finally:
        sftp.close()
        transport.close()

    # Kumpulkan opsi filter — tahun dari folder level-1 (bukan hanya dari file)
    tahun_set = sorted(top_folders, reverse=True)
    organisasi_set = sorted(set(f["organisasi"] for f in all_files if f["organisasi"]))

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
        "filter_values": {
            "tahun": filter_tahun,
            "organisasi": filter_organisasi,
            "unit": filter_unit,
            "q": filter_q,
        },
    }
    return render(request, "ppid_dokumen/cdn_files_table.html", context)
