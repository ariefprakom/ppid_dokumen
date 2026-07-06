# Product Overview

PPID Dokumen is a public document repository for PPID (Pejabat Pengelola Informasi dan Dokumentasi) at UIN Ar-Raniry. It implements Indonesia's Freedom of Information Law (UU Keterbukaan Informasi Publik / KIP).

## Purpose
- Provide public access to institutional documents categorized by information type
- Allow filtering and searching documents by unit, category, classification, status, year, and keywords
- Track download counts per document
- Serve documents from local upload OR external CDN (https://cdn.ar-raniry.ac.id/ppid/data)
- Provide admin interface for managing documents and uploading files to CDN via SFTP
- SSO authentication via Keycloak OIDC for admin staff

## Domain Context
- "Unit Kerja" = organizational units (faculties, bureaus, institutions)
- "Kategori Informasi" = information categories per UU KIP (Serta Merta, Berkala, Tersedia Setiap Saat, Dikecualikan)
- "Klasifikasi" = classification level (Umum, Terbatas, Dikecualikan)
- "Organisasi" = CDN folder structure level 2 (e.g., AAKK, AUPK, LP2M, PPID, SPI)
- "Unit Organisasi" = CDN folder structure level 3, child of Organisasi
- CDN folder structure: `root / tahun / organisasi / unit_organisasi / file`

## Target Users
- Public visitors browsing/downloading documents at /ppid/
- Admin staff managing documents and uploading to CDN via Django admin (SSO via Keycloak)
- Intended to be embedded/linked from https://ppid.ar-raniry.ac.id/
