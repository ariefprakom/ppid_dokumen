from django.conf import settings


class OIDCSessionMiddleware:
    """Middleware untuk menyimpan id_token dari OIDC authentication backend
    ke session, agar bisa dipakai saat logout dari Keycloak."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Setelah OIDC callback, simpan id_token ke session
        if (
            getattr(settings, "OIDC_ENABLED", False)
            and hasattr(request, "user")
            and request.user.is_authenticated
            and "oidc_id_token" not in request.session
        ):
            # Cek apakah ada id_token yang disimpan backend di request
            id_token = getattr(request, "_oidc_id_token", None)
            if id_token:
                request.session["oidc_id_token"] = id_token

        return response
