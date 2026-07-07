from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/ppid/', permanent=False)),
    path('admin/', admin.site.urls),
    path("ppid/", include("ppid_dokumen.urls")),
]

# OIDC URLs (login/callback/logout via Keycloak)
if getattr(settings, 'OIDC_ENABLED', False):
    from core.views import keycloak_logout, KeycloakCallbackView

    urlpatterns += [
        # Custom logout yang juga logout dari Keycloak
        path("oidc/logout/", keycloak_logout, name="oidc_logout"),
        # Custom callback untuk simpan id_token
        path("oidc/callback/", KeycloakCallbackView.as_view(), name="oidc_authentication_callback"),
        # Sisanya dari mozilla-django-oidc (authenticate, dll)
        path("oidc/", include("mozilla_django_oidc.urls")),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)