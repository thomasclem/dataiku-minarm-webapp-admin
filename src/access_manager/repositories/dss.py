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

    def reader_capacity(self):
        def read(client):
            status = client.get_licensing_status()
            base = status.get('base', {})
            if base.get('valid') is not True or base.get('expired') is True:
                return {'available': False, 'message': 'La licence DSS n’est pas valide.'}
            if 'READER' not in base.get('userProfiles', []):
                return {'available': False, 'message': 'Le profil READER n’est pas disponible dans la licence de cette instance. Aucun autre profil ne sera utilisé.'}
            limits = status.get('limits', {}).get('profileLimits', {}).get('READER', {})
            limit = limits.get('licensed', {}).get('licensedLimit')
            used = limits.get('countWithDemotedTo')
            if not isinstance(limit, int) or not isinstance(used, int) or (limit != -1 and used >= limit):
                return {'available': False, 'message': 'Aucune place Reader disponible ou capacité non vérifiable.'}
            return {'available': True, 'message': 'Création avec le profil READER uniquement, sans groupe initial. Instance DSS standard requise ; Dataiku Cloud utilise les invitations Launchpad.'}
        return self._call('vérification de la capacité Reader', read)

    def create_reader(self, login, display_name, email, password, source_type):
        def create(client):
            if any(row.get('login') == login for row in client.list_users()):
                raise ValueError('Cet identifiant existe déjà.')
            client.create_user(login, password, display_name=display_name,
                               source_type=source_type, groups=[], profile='READER', email=email)
        return self._call('création du compte Reader', create)

    def add_groups(self, login, groups, required_profile='READER'):
        """One fresh additive save for the entire plan; no per-group partial writes."""
        def update(client):
            settings = client.get_user(login).get_settings()
            raw = settings.get_raw()
            if not user_enabled_from_raw(raw) or raw.get('userProfile') != required_profile:
                raise ValueError('Le compte doit être actif et conserver son profil Reader.')
            expected = sorted(set(raw_user_groups(raw)) | set(groups))
            if expected == raw_user_groups(raw):
                return False
            raw['groups'] = expected
            settings.save()
            readback = client.get_user(login).get_settings().get_raw()
            if (not set(expected).issubset(set(raw_user_groups(readback)))
                    or readback.get('userProfile') != required_profile):
                raise RuntimeError('Écriture effectuée, mais vérification incomplète. Faites contrôler le compte avant de réessayer.')
            return True
        return self._call('attribution des groupes Reader et vérification', update)
