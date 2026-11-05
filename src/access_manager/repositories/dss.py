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

    def provision_access_history(self, connection):
        """Explicit administrator setup: create a managed Flow dataset, never replace data.

        Run on the target DSS instance after choosing an existing managed-storage
        connection. This is not called by layout builders or request callbacks.
        """
        from ..config import ACCESS_HISTORY_PROJECT_KEY, ACCESS_HISTORY_DATASET
        from ..services.history import HISTORY_SCHEMA
        if not isinstance(connection, str) or not connection.strip():
            raise ValueError('Une connexion de stockage managé est obligatoire.')
        def provision(client):
            project = client.get_project(ACCESS_HISTORY_PROJECT_KEY)
            builder = project.new_managed_dataset(ACCESS_HISTORY_DATASET)
            if builder.already_exists():
                dataset = project.get_dataset(ACCESS_HISTORY_DATASET)
                self._validate_history_handle(dataset)
                current = dataset.get_settings().get_raw().get('params', {}).get('connection')
                if current != connection:
                    raise ValueError('Le dataset existe sur une autre connexion ; aucune modification effectuée.')
                return {'created': False, 'dataset': ACCESS_HISTORY_DATASET}
            builder.with_store_into(connection)
            dataset = builder.create(overwrite=False)
            dataset.set_schema({'columns': [dict(column) for column in HISTORY_SCHEMA]})
            self._validate_history_handle(dataset)
            return {'created': True, 'dataset': ACCESS_HISTORY_DATASET}
        return self._call('création du dataset managé d’historique', provision)

    @staticmethod
    def _validate_history_handle(dataset):
        from ..services.history import HISTORY_SCHEMA
        if dataset.get_settings().get_raw().get('managed') is not True:
            raise ValueError('Le dataset d’historique doit être managé.')
        columns = dataset.get_schema().get('columns', [])
        actual = [(column['name'], column['type']) for column in columns]
        expected = [(column['name'], column['type']) for column in HISTORY_SCHEMA]
        if actual != expected:
            raise ValueError('Le schéma du dataset d’historique est incompatible ; aucune donnée modifiée.')

    def append_access_history(self, rows):
        """Append rows without rewriting the schema or reading/replacing existing history."""
        from ..config import ACCESS_HISTORY_PROJECT_KEY, ACCESS_HISTORY_DATASET
        from ..services.history import HISTORY_SCHEMA
        if not rows:
            return
        expected = {column['name'] for column in HISTORY_SCHEMA}
        if any(set(row) != expected for row in rows):
            raise ValueError('Une ligne d’historique ne respecte pas le schéma attendu.')
        def append(client):
            dataset = client.get_project(ACCESS_HISTORY_PROJECT_KEY).get_dataset(ACCESS_HISTORY_DATASET)
            self._validate_history_handle(dataset)
            core = dataset.get_as_core_dataset()
            core.spec_item['appendMode'] = True
            with core.get_writer() as writer:
                for row in rows:
                    writer.write_row_dict(row)
        return self._call('écriture de l’historique des habilitations', append)

    def get_isolation_enabled(self):
        """Return True/False only for an explicit DSS UIF setting; otherwise unknown.

        Never expose, cache or modify the rest of the general settings.
        """
        def read(client):
            raw = client.get_general_settings().get_raw()
            impersonation = raw.get('impersonation')
            if not isinstance(impersonation, dict):
                return None
            enabled = impersonation.get('enabled')
            return enabled if type(enabled) is bool else None
        try:
            return self._call('lecture de l’activation du User Isolation Framework', read)
        except RuntimeError:
            return None
