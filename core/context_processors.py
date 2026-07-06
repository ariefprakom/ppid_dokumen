from django.conf import settings


def oidc_settings(request):
    """Expose OIDC_ENABLED flag ke semua template."""
    return {
        "oidc_enabled": getattr(settings, "OIDC_ENABLED", False),
    }
