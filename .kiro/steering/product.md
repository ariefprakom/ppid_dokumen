# Product Overview

PPID Dokumen is a public document repository for PPID (Pejabat Pengelola Informasi dan Dokumentasi) at UIN Ar-Raniry. It implements Indonesia's Freedom of Information Law (UU Keterbukaan Informasi Publik / KIP).

## Purpose
- Provide public access to documents stored on CDN server (https://cdn.ar-raniry.ac.id/ppid/data)
- Allow filtering documents by tahun, organisasi, unit organisasi, and keyword
- Provide admin interface for managing organisasi/unit master data and uploading files to CDN via SFTP
- Support file management on CDN (upload, rename, delete) from admin
- SSO authentication via Keycloak OIDC for admin staff

## Domain Context
- "Organisasi" = organizational unit at CDN folder level 2 (e.g., AAKK, AUPK, LP2M, PPID, SPI)
- "Unit Organisasi" = sub-unit at CDN folder level 3, child of Organisasi
- CDN folder structure: `root / tahun / organisasi / unit_organisasi / file`
- Documents are served directly from CDN (public Nginx server), Django reads file listing via SFTP

## Target Users
- Public visitors browsing/downloading documents at /ppid/
- Admin staff managing organisasi/unit data and uploading files to CDN via Django admin (SSO via Keycloak)
- Intended to be embedded/linked from https://ppid.ar-raniry.ac.id/

## Deployment
- Dockerized: build image locally → push to Docker Hub → pull on server → docker run
- Image: ariefprakom/ppid-dokumen:latest
- Static files served via Whitenoise (no separate Nginx needed for Django)
- Production server: 192.168.176.23:8000
