from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect


class PPIDAdminSite(admin.AdminSite):
    site_header = "PPID UIN Ar-Raniry"
    site_title = "PPID Admin"
    index_title = "Manajemen Dokumen PPID"

    def logout(self, request, extra_context=None):
        """Override logout: jika OIDC aktif, logout dari Keycloak juga."""
        if getattr(settings, "OIDC_ENABLED", False):
            return redirect("/oidc/logout/")
        return super().logout(request, extra_context)


# Replace default admin site
admin.site.__class__ = PPIDAdminSite
