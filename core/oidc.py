"""
Custom OIDC Authentication Backend for Keycloak.

Handles:
- Auto-creation of Django user on first login
- Mapping Keycloak roles/groups to Django is_staff / is_superuser
- Syncing user profile (email, nama) from Keycloak claims
"""

import json
import logging
import base64

from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def get_userinfo(self, access_token, id_token, payload):
        """Override: gabungkan userinfo dengan claims dari access token
        agar realm_access/resource_access roles tersedia."""
        userinfo = super().get_userinfo(access_token, id_token, payload)

        # Simpan id_token untuk dipakai saat logout
        userinfo["_id_token"] = id_token

        # Decode access token untuk ambil roles (tanpa verifikasi,
        # karena sudah diverifikasi oleh library)
        token_claims = self._decode_token_payload(access_token)
        if token_claims:
            # Merge role-related claims dari access token ke userinfo
            for key in ("realm_access", "resource_access", "groups"):
                if key in token_claims and key not in userinfo:
                    userinfo[key] = token_claims[key]

        logger.debug("OIDC merged claims: %s", json.dumps(userinfo, indent=2, default=str))
        return userinfo

    def _decode_token_payload(self, token):
        """Decode payload JWT tanpa verifikasi (untuk ambil claims)."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            # Padding base64
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            logger.warning("Failed to decode access token: %s", e)
            return None

    def create_user(self, claims):
        """Buat user baru dari claims Keycloak."""
        user = super().create_user(claims)
        self._update_user_from_claims(user, claims)
        self._store_id_token(claims)
        return user

    def update_user(self, user, claims):
        """Update user yang sudah ada setiap kali login."""
        self._update_user_from_claims(user, claims)
        self._store_id_token(claims)
        return user

    def _store_id_token(self, claims):
        """Simpan id_token ke instance variable agar bisa disimpan ke session."""
        # id_token disimpan di claims oleh get_userinfo
        self._id_token = claims.get("_id_token", "")

    def _update_user_from_claims(self, user, claims):
        """Sinkronisasi data user dari Keycloak claims."""
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.email = claims.get("email", "")

        # Ambil roles dari Keycloak (realm_access.roles + resource_access)
        roles = self._get_keycloak_roles(claims)
        logger.info("OIDC roles for %s: %s", user.username, roles)

        # Mapping role ke permission Django
        staff_roles = set(getattr(settings, "OIDC_STAFF_ROLES", []))
        superuser_roles = set(getattr(settings, "OIDC_SUPERUSER_ROLES", []))

        user.is_staff = bool(roles & staff_roles) or bool(roles & superuser_roles)
        user.is_superuser = bool(roles & superuser_roles)

        user.save()
        logger.info(
            "OIDC user synced: %s (staff=%s, superuser=%s, roles=%s)",
            user.username, user.is_staff, user.is_superuser, roles
        )

    def _get_keycloak_roles(self, claims):
        """Ekstrak semua roles dari token claims Keycloak."""
        roles = set()

        # Realm-level roles
        realm_access = claims.get("realm_access", {})
        roles.update(realm_access.get("roles", []))

        # Client-level roles
        resource_access = claims.get("resource_access", {})
        client_id = getattr(settings, "OIDC_RP_CLIENT_ID", "")
        client_roles = resource_access.get(client_id, {})
        roles.update(client_roles.get("roles", []))

        # Groups (jika di-map sebagai claim)
        groups = claims.get("groups", [])
        roles.update(groups)

        return roles

    def filter_users_by_claims(self, claims):
        """Cari user berdasarkan preferred_username atau email."""
        username = claims.get("preferred_username")
        if username:
            users = self.UserModel.objects.filter(username=username)
            if users.exists():
                return users

        email = claims.get("email")
        if email:
            return self.UserModel.objects.filter(email=email)

        return self.UserModel.objects.none()

    def get_username(self, claims):
        """Gunakan preferred_username dari Keycloak sebagai username Django."""
        return claims.get("preferred_username", claims.get("sub"))
