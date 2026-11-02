"""Application operations, injected repository; no Dash/Flask/Dataiku imports."""
import hashlib
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from .permissions import (normalize_login, user_enabled_from_raw, raw_user_groups, group_name, normalize_group_definition, group_is_admin, group_origin, group_global_capabilities, global_privilege_severity, true_grants, row_has_any_true_permission, merge_grants, permission_admin_for_login_or_groups, is_instance_admin, group_grants_project_read, project_permission_tier, group_acl_rows_by_name, rank_group, validate_group_assignable)
from .previews import PreviewSigner, canonical_json
from .audit import structured_audit

class AccessService:
    def __init__(self, repository, policy=None, signer=None, lock=None):
        self.repository = repository
        self.policy = {} if policy is None else policy
        self.signer = signer or PreviewSigner()
        self.lock = lock or threading.RLock()

    def authenticate(self, headers):
        auth = self.repository.auth_info(headers)
        identifier = normalize_login(auth.get('authIdentifier') if isinstance(auth, dict) else None)
        if not identifier:
            raise PermissionError("Aucun utilisateur DSS authentifié n’a été trouvé.")
        user = self.resolve_enabled_user(identifier)
        return {'auth': auth, 'login': user['login'], 'raw': user['raw']}

    def list_enabled_users(self):
        out = []
        for row in self.repository.list_users():
            login = normalize_login(row.get('login') or row.get('name') or row.get('id'))
            if login and user_enabled_from_raw(self.repository.get_user_raw(login)):
                out.append({'label': login, 'value': login})
        return sorted(out, key=lambda row: row['label'].lower())

    def resolve_enabled_user(self, identifier):
        logins = {normalize_login(row.get('login') or row.get('name') or row.get('id')) for row in self.repository.list_users()}
        login = normalize_login(identifier)
        if login not in logins:
            raise PermissionError("L’identifiant authentifié ne correspond pas exactement à un compte DSS actif.")
        raw = self.get_user_raw(login)
        return {'login': login, 'raw': raw}

    def get_user_raw(self, login):
        raw = self.repository.get_user_raw(login)
        if not user_enabled_from_raw(raw):
            raise ValueError("Le compte DSS est désactivé ou ne publie pas d’état actif exploitable.")
        return raw

    def list_group_defs(self):
        definitions = {}
        for row in self.repository.list_groups():
            name = group_name(row)
            if not name:
                raise RuntimeError("La liste des groupes contient une entrée sans nom.")
            definition = self.repository.get_group_definition(name)
            if not isinstance(definition, dict):
                raise RuntimeError("La définition du groupe n’est pas un dictionnaire.")
            definition = dict(definition, name=name)
            definitions[name] = normalize_group_definition(definition)
        return definitions

    def list_project_keys(self):
        keys = [normalize_login(p.get('projectKey') or p.get('key') or p.get('id')) for p in self.repository.list_projects()]
        return sorted(set(key for key in keys if key))

    def get_project_permissions(self, key):
        permissions = self.repository.get_project_permissions(key)
        owner = normalize_login(permissions.get('owner') or permissions.get('ownerLogin') or permissions.get('projectOwner'))
        rows = permissions.get('permissions', []) or permissions.get('acl', []) or []
        return {'owner': owner, 'permissions': rows}


    def groups_on_project_acl(self, project_key: str, group_defs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        perms = self.get_project_permissions(project_key)
        found = {}
        for group, rows in group_acl_rows_by_name(perms).items():
            grants = merge_grants(rows)
            if not group_grants_project_read(grants):
                continue
            gdef = group_defs.get(group)
            if not gdef:
                raise RuntimeError(f"La liste d’accès du projet référence un groupe illisible ou manquant : {group}.")
            caps = group_global_capabilities(gdef)
            found[group] = {
                "name": group,
                "grants": grants,
                "tier": project_permission_tier(grants),
                "globalCapabilities": caps,
                "globalSeverity": global_privilege_severity(caps),
                "isAdmin": group_is_admin(gdef),
                "origin": group_origin(gdef),
            }
        return found


    def group_affected_projects(self, group_name_: str) -> List[Dict[str, Any]]:
        affected = []
        for project_key in self.list_project_keys():
            perms = self.get_project_permissions(project_key)
            rows = [row for row in perms.get("permissions", []) if normalize_login(row.get("group")) == group_name_ and row_has_any_true_permission(row)]
            if rows:
                grants = merge_grants(rows)
                affected.append({"projectKey": project_key, "grants": grants, "tier": project_permission_tier(grants)})
        return sorted(affected, key=lambda x: x["projectKey"])


    def project_dropdown_options_for_actor(self, actor: Dict[str, Any], group_defs: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
        actor_groups = raw_user_groups(actor["raw"])
        instance_admin = is_instance_admin(actor["raw"], actor_groups, group_defs)
        out = []
        for key in self.list_project_keys():
            perms = self.get_project_permissions(key)
            if instance_admin or permission_admin_for_login_or_groups(perms, actor["login"], actor_groups):
                out.append({"label": key, "value": key})
        return sorted(out, key=lambda x: x["label"])


    def compute_preview(self, actor: Dict[str, Any], project_key: str, target_user: str, group_name_: str) -> Dict[str, Any]:
        group_defs = self.list_group_defs()
        actor_groups = raw_user_groups(actor["raw"])
        instance_admin = is_instance_admin(actor["raw"], actor_groups, group_defs)
        project_perms = self.get_project_permissions(project_key)
        if not instance_admin and not permission_admin_for_login_or_groups(project_perms, actor["login"], actor_groups):
            raise PermissionError("Vous devez être administrateur du projet sélectionné.")

        target_raw = self.get_user_raw(target_user)
        target_groups = raw_user_groups(target_raw)
        if group_name_ not in group_defs:
            raise ValueError("Le groupe sélectionné n’existe plus ou ne peut pas être inspecté.")
        group_def = group_defs[group_name_]
        validate_group_assignable(group_def)

        acl_groups = self.groups_on_project_acl(project_key, group_defs)
        if group_name_ not in acl_groups:
            raise PermissionError("Le groupe n’est pas déjà présent sur la liste d’accès du projet avec un droit de consultation suffisant.")

        affected = self.group_affected_projects(group_name_)
        group_info = acl_groups[group_name_]
        group_info["affectedProjectCount"] = len(affected)
        group_info["otherAffectedProjectCount"] = len([p for p in affected if p["projectKey"] != project_key])
        group_info["leastPrivilegeEstimate"] = rank_group(group_info, affected, project_key)

        blocked_reasons = []
        already_member = group_name_ in target_groups
        if already_member:
            blocked_reasons.append("L’utilisateur cible appartient déjà à ce groupe ; l’ajout sera sans effet.")
        if not instance_admin:
            allowed = set(self.policy.get(project_key, []))
            if group_name_ not in allowed:
                blocked_reasons.append("La délégation standard refuse cette attribution : un administrateur d’instance doit d’abord approuver ce couple projet/groupe dans la configuration.")
            for item in affected:
                other_perms = self.get_project_permissions(item["projectKey"])
                if not permission_admin_for_login_or_groups(other_perms, actor["login"], actor_groups):
                    blocked_reasons.append(f"Vous n’administrez pas le projet également concerné {item['projectKey']}.")

        allowed_to_submit = (not blocked_reasons) or already_member
        snapshot = {
            "actor": actor["login"],
            "project": project_key,
            "target": target_user,
            "group": group_name_,
            "target_groups_hash": hashlib.sha256(canonical_json(target_groups).encode()).hexdigest(),
            "project_acl_hash": hashlib.sha256(canonical_json(project_perms).encode()).hexdigest(),
            "group_def_hash": hashlib.sha256(canonical_json(group_def).encode()).hexdigest(),
            "affected_hash": hashlib.sha256(canonical_json(affected).encode()).hexdigest(),
            "policy_hash": hashlib.sha256(canonical_json(self.policy).encode()).hexdigest(),
            "instance_admin": instance_admin,
            "allowed_to_submit": allowed_to_submit,
            "expires_at": int(time.time()) + self.signer.ttl,
        }
        return {
            "snapshot": snapshot,
            "token": self.signer.sign(snapshot),
            "instanceAdmin": instance_admin,
            "targetAlreadyMember": already_member,
            "allowedToSubmit": allowed_to_submit,
            "blockedReasons": blocked_reasons,
            "project": project_key,
            "target": target_user,
            "group": group_info,
            "affectedProjects": affected,
        }


    def revalidate_snapshot(self, actor: Dict[str, Any], preview_token: str, acknowledge_scope: bool, current_project: str, current_target: str, current_group: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        valid, snapshot, err = self.signer.verify(preview_token)
        if not valid or snapshot is None:
            raise PermissionError(err)
        if snapshot.get("actor") != actor["login"]:
            raise PermissionError("Cet aperçu appartient à un autre opérateur.")
        if snapshot.get("project") != current_project or snapshot.get("target") != current_target or snapshot.get("group") != current_group:
            raise PermissionError("La sélection actuelle ne correspond plus à l’aperçu signé. Relancez la vérification des accès.")
        if not acknowledge_scope:
            raise PermissionError("Vous devez confirmer la portée de l’appartenance au groupe avant de continuer.")
        fresh = self.compute_preview(actor, snapshot["project"], snapshot["target"], snapshot["group"])
        fresh_snapshot = fresh["snapshot"]
        comparable_keys = ["actor", "project", "target", "group", "target_groups_hash", "project_acl_hash", "group_def_hash", "affected_hash", "policy_hash", "instance_admin", "allowed_to_submit"]
        for key in comparable_keys:
            if snapshot.get(key) != fresh_snapshot.get(key):
                raise PermissionError("La validation a changé depuis l’aperçu. Relancez la vérification des accès.")
        if not fresh.get("allowedToSubmit"):
            raise PermissionError("Attribution bloquée : " + "; ".join(fresh.get("blockedReasons", [])))
        return snapshot, fresh


    def ranked_groups(self, actor, project_key):
        definitions = self.list_group_defs()
        projects = {p['value'] for p in self.project_dropdown_options_for_actor(actor, definitions)}
        if project_key not in projects:
            raise PermissionError("Vous n’administrez pas le projet sélectionné.")
        groups = self.groups_on_project_acl(project_key, definitions)
        ranked = []
        for group in groups.values():
            affected = self.group_affected_projects(group['name'])
            group['otherAffectedProjectCount'] = len([p for p in affected if p['projectKey'] != project_key])
            ranked.append((rank_group(group, affected, project_key), group, affected))
        return sorted(ranked, key=lambda item: item[0])

    def add_group_to_user(self, actor, preview_token, acknowledge_scope, current_project, current_target, current_group):
        with self.lock:
            snapshot, _ = self.revalidate_snapshot(actor, preview_token, acknowledge_scope, current_project, current_target, current_group)
            target, group, project = snapshot['target'], snapshot['group'], snapshot['project']
            raw = self.get_user_raw(target)
            added = False if group in raw_user_groups(raw) else self.repository.add_group(target, group)
            outcome = 'ADDED' if added else 'NOOP_ALREADY_MEMBER'
            structured_audit(actor['login'], target, project, group, outcome)
            message = "Le groupe a été ajouté. Toutes les appartenances ont été vérifiées." if added else "L’utilisateur appartient déjà à ce groupe ; aucune modification n’a été effectuée."
            return {'ok': True, 'message': message, 'noOp': not added}
