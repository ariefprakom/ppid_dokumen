# Product Overview

PPID Dokumen is a public document repository for PPID (Pejabat Pengelola Informasi dan Dokumentasi) at UIN Ar-Raniry. It implements Indonesia's Freedom of Information Law (UU Keterbukaan Informasi Publik / KIP).

## Purpose
- Provide public access to institutional documents categorized by information type
- Allow filtering and searching documents by unit, category, classification, status, year, and keywords
- Track download counts per document
- Support document management via Django admin

## Domain Context
- "Unit Kerja" = organizational units (faculties, bureaus, institutions)
- "Kategori Informasi" = information categories per UU KIP (Serta Merta, Berkala, Tersedia Setiap Saat, Dikecualikan)
- "Klasifikasi" = classification level (Umum, Terbatas, Dikecualikan)
- Documents are uploaded as files and served for download

## Target Users
- Public visitors browsing/downloading documents at /ppid/
- Admin staff managing documents via Django admin
- Intended to be embedded/linked from https://ppid.ar-raniry.ac.id/
