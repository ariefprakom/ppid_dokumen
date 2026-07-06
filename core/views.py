from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView


class KeycloakCallbackView(OIDCAuthenticationCallbackView):
    """Override callback agar id_token tersimpan di session untuk logout."""

    def login_success(self):
        """Setelah login berhasil, simpan id_token ke session."""
        response = super().login_success()

        # Ambil id_token dari session state yang di-set oleh mozilla-django-oidc
        # atau dari backend instance
        if hasattr(self, "request") and self.request.session:
            # mozilla-django-oidc v4+ menyimpan token di session via
            # SessionRefresh; kita juga simpan id_token sendiri
            token_info = self.request.session.get("oidc_id_token_expiration")
            if not self.request.session.get("oidc_id_token"):
                # Coba dapatkan dari backend
                from django.contrib.auth import get_backends
                for backend in get_backends():
                    if hasattr(backend, "_id_token") and backend._id_token:
                        self.request.session["oidc_id_token"] = backend._id_token
                        break

        return response


def keycloak_logout(request):
    """Logout dari Django + Keycloak sekaligus (RP-Initiated Logout)."""
    # Simpan id_token sebelum session dihapus
    id_token = request.session.get("oidc_id_token", "")

    # Logout Django (hapus session)
    auth_logout(request)

    # Jika OIDC tidak aktif atau tidak ada id_token, redirect ke admin login
    if not getattr(settings, "OIDC_ENABLED", False):
        return redirect("/admin/login/")

    # Redirect ke Keycloak logout endpoint (bahkan tanpa id_token_hint,
    # Keycloak akan tetap invalidate session via client_id)
    keycloak_logout_url = getattr(settings, "OIDC_OP_LOGOUT_ENDPOINT", "")
    post_logout_uri = request.build_absolute_uri("/admin/login/")

    params = {
        "client_id": getattr(settings, "OIDC_RP_CLIENT_ID", ""),
        "post_logout_redirect_uri": post_logout_uri,
    }
    if id_token:
        params["id_token_hint"] = id_token

    logout_url = f"{keycloak_logout_url}?{urlencode(params)}"
    return redirect(logout_url)
