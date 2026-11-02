"""The only module allowed to call the Dataiku SDK.

The client factory is lazy: importing the package never contacts DSS.
"""
import logging
from ..services.permissions import user_enabled_from_raw, raw_user_groups

LOGGER = logging.getLogger(__name__)

def default_client_factory():
    import dataiku
    return dataiku.api_client()

class DSSRepository:
    def __init__(self, client_factory=None):
        self.client_factory = client_factory or default_client_factory

    def _call(self, operation, fn):
        try:
            return fn(self.client_factory())
        except Exception as exc:
            LOGGER.error("DSS operation %s failed (%s)", operation, type(exc).__name__)
            raise RuntimeError("L’opération DSS a échoué : " + operation) from exc

    def auth_info(self, headers):
        return self._call('authentification', lambda c: c.get_auth_info_from_browser_headers(headers))

    def list_users(self):
        return self._call('liste des utilisateurs', lambda c: c.list_users())

    def get_user_raw(self, login):
        return self._call('lecture utilisateur', lambda c: c.get_user(login).get_settings().get_raw())

    def list_groups(self):
        return self._call('liste des groupes', lambda c: c.list_groups())

    def get_group_definition(self, name):
        return self._call('lecture groupe', lambda c: c.get_group(name).get_definition())

    def list_projects(self):
        return self._call('liste des projets', lambda c: c.list_projects())

    def get_project_permissions(self, key):
        return self._call('lecture des droits du projet', lambda c: c.get_project(key).get_permissions())

    def add_group(self, login, group):
        """Fresh additive update, preserving the SDK's mutable raw settings."""
        def update(client):
            settings = client.get_user(login).get_settings()
            raw = settings.get_raw()
            if not user_enabled_from_raw(raw):
                raise ValueError("L’utilisateur cible est désactivé.")
            existing = raw_user_groups(raw)
            if group in existing:
                return False
            expected = sorted(set(existing + [group]))
            raw['groups'] = expected
            settings.save()
            readback = client.get_user(login).get_settings().get_raw()
            if not set(expected).issubset(set(raw_user_groups(readback))):
                raise RuntimeError("La vérification après sauvegarde a échoué.")
            return True
        return self._call('ajout au groupe et vérification', update)
