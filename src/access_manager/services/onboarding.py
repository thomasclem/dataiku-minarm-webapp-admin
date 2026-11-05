"""Reader provisioning and multi-project plans, independent of UI and SDK."""
import hashlib
import re
import time
from .audit import structured_audit
from .permissions import (
    raw_user_groups, is_instance_admin, permission_admin_for_login_or_groups,
    validate_group_assignable, group_global_capabilities, group_grants_project_read,
    group_acl_rows_by_name, merge_grants, project_permission_tier,
)
from .previews import canonical_json
from ..config import LOW_PRIVILEGES, READ_PRIVILEGES, READER_SOURCE_TYPE

READ_ONLY_GRANTS = LOW_PRIVILEGES | READ_PRIVILEGES


class ReaderOnboarding:
    def __init__(self, access, source_type=READER_SOURCE_TYPE):
        self.access = access
        self.repository = access.repository
        self.source_type = source_type

    def context(self, actor):
        definitions = self.access.list_group_defs()
        projects = self.access.project_dropdown_options_for_actor(actor, definitions)
        if not projects:
            raise PermissionError("Vous devez administrer au moins un projet.")
        return definitions, projects

    def creation_status(self, actor):
        self.context(actor)
        if self.source_type not in {'LOCAL', 'LDAP', 'LOCAL_NO_AUTH'}:
            return False, "Le mode de création des comptes n’est pas configuré."
        status = self.repository.reader_capacity()
        return status['available'], status['message']

    def list_readers(self):
        out = []
        for row in self.repository.list_users():
            login = str(row.get('login') or row.get('name') or '').strip()
            if not login:
                continue
            raw = self.repository.get_user_raw(login)
            if raw.get('userProfile') == 'READER' and raw.get('enabled') is True and raw.get('disabled') is not True:
                out.append({'label': login, 'value': login})
        return sorted(out, key=lambda item: item['label'].lower())

    def create_reader(self, actor, login, display_name, email, password):
        with self.access.lock:
            available, message = self.creation_status(actor)
            if not available:
                raise PermissionError(message)
            login, display_name, email = (str(v or '').strip() for v in (login, display_name, email))
            if not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', login):
                raise ValueError("L’identifiant accepte uniquement les lettres, chiffres et caractères . _ @ -.")
            if not display_name or len(display_name) > 200:
                raise ValueError("Le nom complet est obligatoire (200 caractères maximum).")
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                raise ValueError("Renseignez une adresse électronique valide.")
            if self.source_type == 'LOCAL' and not password:
                raise ValueError("Un mot de passe initial est obligatoire pour un compte local.")
            if self.source_type != 'LOCAL' and password:
                raise ValueError("Le mot de passe est géré par le fournisseur d’identité.")
            if any(str(u.get('login') or u.get('name') or '') == login for u in self.repository.list_users()):
                raise ValueError("Cet identifiant existe déjà. Sélectionnez le compte Reader existant.")
            self.repository.create_reader(login, display_name, email, password, self.source_type)
            raw = self.access.get_user_raw(login)
            if raw.get('userProfile') != 'READER' or raw_user_groups(raw):
                raise RuntimeError("Le compte a été créé, mais son profil ou ses groupes doivent être contrôlés par un administrateur. Aucune attribution effectuée.")
            structured_audit(actor['login'], login, '', '', 'READER_CREATED')
            return login

    def plan(self, actor, projects, target):
        if not isinstance(projects, list) or not projects or len(projects) > 50:
            raise ValueError("Sélectionnez entre un et cinquante projets.")
        keys = sorted(set(projects))
        definitions, available = self.context(actor)
        if not set(keys).issubset({p['value'] for p in available}):
            raise PermissionError("Vous devez administrer chacun des projets sélectionnés.")
        raw = self.access.get_user_raw(target)
        if raw.get('userProfile') != 'READER':
            raise PermissionError("Seuls les comptes ayant exactement le profil READER sont admissibles.")
        actor_groups = raw_user_groups(actor['raw'])
        admin = is_instance_admin(actor['raw'], actor_groups, definitions)
        memberships = set(raw_user_groups(raw))
        all_acls = {key: self.access.get_project_permissions(key) for key in self.access.list_project_keys()}
        candidates, detected = self.inspect_groups(actor, keys, definitions, all_acls, memberships, admin)
        assignments, blocked = [], []
        for key in keys:
            choices = [c for c in candidates.values() if key in c['projects']]
            def rank(candidate):
                grants = next(a['grants'] for a in candidate['affectedProjects'] if a['projectKey'] == key)
                # Prefer existing equivalent membership, then fewer outside projects.
                return (
                    int('readProjectContent' in grants),
                    len([a for a in candidate['affectedProjects'] if a['projectKey'] not in keys]),
                    sum(len(a['grants']) for a in candidate['affectedProjects']),
                    candidate['name'] not in memberships,
                    candidate['name'].lower(),
                )
            if not choices:
                count = sum(item['project'] == key for item in detected)
                if count:
                    blocked.append(f"{key} : {count} groupe(s) détecté(s), mais aucun n’est admissible pour une attribution en consultation. Consultez les motifs ci-dessous.")
                else:
                    blocked.append(f"{key} : aucun groupe n’est présent dans la liste d’accès du projet.")
            else:
                chosen = min(choices, key=rank)
                grants = next(a['grants'] for a in chosen['affectedProjects'] if a['projectKey'] == key)
                assignments.append({'project': key, 'group': chosen['name'], 'grants': grants, 'alreadyMember': chosen['name'] in memberships})
        chosen_pairs = {(a['project'], a['group']) for a in assignments}
        for item in detected:
            item['recommended'] = (item['project'], item['name']) in chosen_pairs
        names = sorted({a['group'] for a in assignments})
        groups = [dict(candidates[name], alreadyMember=name in memberships) for name in names]
        # Full snapshot detects ACL, policy, identity, profile and membership changes.
        snapshot = {
            'actor': actor['login'], 'actorRaw': actor['raw'], 'target': target,
            'targetState': {'groups': sorted(memberships), 'profile': raw.get('userProfile'), 'enabled': True},
            'projects': keys, 'definitions': definitions, 'acls': all_acls,
            'policy': self.access.policy, 'assignments': assignments,
        }
        digest = hashlib.sha256(canonical_json(snapshot).encode()).hexdigest()
        return {'projects': keys, 'target': target, 'assignments': assignments, 'groups': groups,
                'blockedReasons': blocked, 'allowedToSubmit': not blocked, 'digest': digest, 'detectedGroups': detected}

    def inspect_groups(self, actor, projects, definitions, all_acls, memberships, admin):
        """Discover ACL groups first; report eligibility separately without hiding exclusions."""
        actor_groups = raw_user_groups(actor['raw'])
        selected = set(projects)
        by_project = {key: group_acl_rows_by_name(all_acls[key]) for key in projects}
        names = sorted({name for rows in by_project.values() for name in rows})
        candidates, detected = {}, []
        for name in names:
            definition = definitions.get(name)
            common_reasons = []
            if definition is None:
                common_reasons.append('La définition du groupe est absente ou inaccessible.')
                capabilities = []
            else:
                try:
                    validate_group_assignable(definition)
                except PermissionError as exc:
                    common_reasons.append(str(exc))
                capabilities = group_global_capabilities(definition)
                if capabilities:
                    common_reasons.append('Le groupe possède des capacités globales supplémentaires sur l’instance.')
            affected = []
            for key, acl in all_acls.items():
                grants = merge_grants(group_acl_rows_by_name(acl).get(name, []))
                if grants:
                    affected.append({'projectKey': key, 'grants': grants})
            if any(not set(item['grants']).issubset(READ_ONLY_GRANTS) for item in affected):
                common_reasons.append('Le groupe accorde des droits autres que la consultation sur au moins un projet (écriture, administration ou droit non pris en charge).')
            if not admin and any(not permission_admin_for_login_or_groups(all_acls[item['projectKey']], actor['login'], actor_groups) for item in affected):
                common_reasons.append('Vous n’administrez pas tous les projets également concernés par ce groupe.')
            eligible_projects = []
            for key in projects:
                if name not in by_project[key]:
                    continue
                grants = merge_grants(by_project[key][name])
                reasons = list(common_reasons)
                if not group_grants_project_read(grants):
                    reasons.append('Aucun droit de consultation suffisant sur ce projet.')
                if not admin and name not in self.access.policy.get(key, []):
                    reasons.append('Ce couple projet/groupe n’est pas approuvé dans la politique de délégation.')
                if not reasons:
                    eligible_projects.append(key)
                detected.append({
                    'project': key, 'name': name, 'grants': grants,
                    'globalCapabilities': capabilities, 'eligible': not reasons,
                    'reasons': reasons, 'alreadyMember': name in memberships,
                    'affectedProjectCount': len(affected),
                    'otherAffectedProjectCount': len([a for a in affected if a['projectKey'] not in selected]),
                })
            if eligible_projects:
                candidates[name] = {'name': name, 'projects': sorted(eligible_projects), 'affectedProjects': affected}
        detected.sort(key=lambda item: (
            item['project'], not item['eligible'], project_permission_tier(item['grants']),
            len(item['globalCapabilities']), item['otherAffectedProjectCount'],
            len(item['grants']), item['name'].lower(),
        ))
        return candidates, detected

    def preview(self, actor, projects, target):
        plan = self.plan(actor, projects, target)
        plan['token'] = self.access.signer.sign({
            'kind': 'reader-multi-project', 'actor': actor['login'], 'target': target,
            'projects': plan['projects'], 'digest': plan['digest'],
            'expires_at': int(time.time()) + self.access.signer.ttl,
        })
        return plan

    def submit(self, actor, token, acknowledge, projects, target):
        with self.access.lock:
            valid, signed, error = self.access.signer.verify(token)
            if not valid:
                raise PermissionError(error)
            if not acknowledge:
                raise PermissionError("Vous devez confirmer les droits et leur portée.")
            if (signed.get('kind') != 'reader-multi-project' or signed.get('actor') != actor['login']
                    or signed.get('target') != target or signed.get('projects') != sorted(set(projects or []))):
                raise PermissionError("La sélection ne correspond plus à l’aperçu. Relancez la vérification.")
            fresh = self.plan(actor, projects, target)
            if fresh['digest'] != signed.get('digest') or not fresh['allowedToSubmit']:
                raise PermissionError("Les droits, groupes ou appartenances ont changé. Relancez la vérification.")
            names = [g['name'] for g in fresh['groups'] if not g['alreadyMember']]
            if names:
                self.repository.add_groups(target, names, required_profile='READER')
            structured_audit(actor['login'], target, ','.join(fresh['projects']), ','.join(names), 'READER_GROUPS_ADDED' if names else 'NOOP_ALREADY_MEMBER')
            return {'ok': True, 'message': f"Habilitation vérifiée pour {len(fresh['projects'])} projet(s). {len(names)} groupe(s) ajouté(s).", 'noOp': not names}
