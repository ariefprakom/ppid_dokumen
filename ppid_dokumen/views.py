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
