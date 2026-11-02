"""Pure authorization and least-privilege rules; no I/O or UI imports."""
from typing import Any, Dict, List, Optional, Tuple
from ..config import (ADMIN_GROUP_NAMES, LOCAL_ORIGIN, UNKNOWN_ORIGIN, LOW_PRIVILEGES, READ_PRIVILEGES, WRITE_PRIVILEGES, ADMIN_PRIVILEGES, IDENTITY_FIELDS)

def normalize_login(value: Any) -> str:
    return str(value or "").strip()


def user_enabled_from_raw(raw: Dict[str, Any]) -> bool:
    if raw.get("disabled") is True:
        return False
    for key in ("enabled", "active"):
        if key in raw:
            return bool(raw.get(key))
    return False


def raw_user_groups(raw: Dict[str, Any]) -> List[str]:
    groups = raw.get("groups", [])
    if groups is None:
        return []
    return sorted({str(g) for g in groups})


def group_name(row: Dict[str, Any]) -> str:
    return normalize_login(row.get("name") or row.get("group") or row.get("id"))


def normalize_group_definition(group_def: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in group_def.items():
        if isinstance(value, (dict, list)) and "permission" in key.lower():
            raise ValueError("Forme de droits de groupe non prise en charge ; seules les définitions plates documentées sont acceptées.")
    return group_def


def group_is_admin(group_def: Dict[str, Any]) -> bool:
    name = str(group_def.get("name") or "").lower()
    if name in ADMIN_GROUP_NAMES:
        return True
    for field in ("admin", "isAdmin", "superAdmin"):
        if group_def.get(field) is True:
            return True
    return False


def group_origin(group_def: Dict[str, Any]) -> str:
    return str(group_def.get("sourceType") or group_def.get("type") or group_def.get("origin") or UNKNOWN_ORIGIN)


def group_global_capabilities(group_def: Dict[str, Any]) -> List[str]:
    caps = []
    for key, value in group_def.items():
        if value is True and (key.startswith("may") or key in {"admin", "isAdmin", "superAdmin"}):
            caps.append(key)
    return sorted(caps)


def global_privilege_severity(caps: List[str]) -> int:
    severity = 0
    for cap in caps:
        low = cap.lower()
        if "admin" in low or "manage" in low or "unsafe" in low or "cluster" in low:
            severity = max(severity, 3)
        elif "create" in low or "write" in low or "develop" in low or "publish" in low:
            severity = max(severity, 2)
        elif "read" in low or "view" in low:
            severity = max(severity, 1)
        else:
            severity = max(severity, 3)
    return severity


def true_grants(row: Dict[str, Any]) -> Dict[str, bool]:
    return {str(k): True for k, v in row.items() if v is True and k not in IDENTITY_FIELDS}


def row_has_any_true_permission(row: Dict[str, Any]) -> bool:
    return bool(true_grants(row))


def merge_grants(rows: List[Dict[str, Any]]) -> Dict[str, bool]:
    merged = {}
    for row in rows:
        merged.update(true_grants(row))
    return dict(sorted(merged.items()))


def permission_admin_for_login_or_groups(perms: Dict[str, Any], login: str, user_groups: List[str]) -> bool:
    if perms.get("owner") == login:
        return True
    group_set = set(user_groups)
    for row in perms.get("permissions", []):
        if row.get("admin") is not True:
            continue
        if normalize_login(row.get("user")) == login:
            return True
        if normalize_login(row.get("group")) in group_set:
            return True
    return False


def is_instance_admin(user_raw: Dict[str, Any], user_groups: List[str], group_defs: Dict[str, Dict[str, Any]]) -> bool:
    if user_raw.get("admin") is True or user_raw.get("isAdmin") is True or user_raw.get("superAdmin") is True:
        return True
    return any(group_is_admin(group_defs.get(g, {"name": g})) for g in user_groups)


def group_grants_project_read(grants: Dict[str, bool]) -> bool:
    return bool(grants.get("admin") or grants.get("readProjectContent") or grants.get("readDashboards"))


def project_permission_tier(grants: Dict[str, bool]) -> int:
    if any(k not in LOW_PRIVILEGES | READ_PRIVILEGES | WRITE_PRIVILEGES | ADMIN_PRIVILEGES for k in grants):
        return 4
    if any(grants.get(k) for k in ADMIN_PRIVILEGES):
        return 3
    if any(grants.get(k) for k in WRITE_PRIVILEGES):
        return 2
    if any(grants.get(k) for k in READ_PRIVILEGES):
        return 1
    if any(grants.get(k) for k in LOW_PRIVILEGES):
        return 0
    return -1


def group_acl_rows_by_name(perms: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    by_group: Dict[str, List[Dict[str, Any]]] = {}
    for row in perms.get("permissions", []):
        g = normalize_login(row.get("group"))
        if g:
            by_group.setdefault(g, []).append(row)
    return by_group


def rank_group(group_info: Dict[str, Any], affected: List[Dict[str, Any]], target_project: str) -> Tuple[Any, ...]:
    caps = group_info.get("globalCapabilities", [])
    other_project_count = len([p for p in affected if p["projectKey"] != target_project])
    all_grants = set(group_info.get("grants", {}).keys())
    for p in affected:
        all_grants.update(p.get("grants", {}).keys())
    return (
        int(group_info.get("isAdmin", False)),
        group_info.get("globalSeverity", 3),
        len(caps),
        other_project_count,
        group_info.get("tier", 4),
        len(all_grants),
        group_info.get("name", "").lower(),
    )


def validate_group_assignable(group_def: Dict[str, Any]) -> None:
    if group_is_admin(group_def):
        raise PermissionError("Les groupes administrateurs sont bloqués.")
    if group_origin(group_def).upper() != LOCAL_ORIGIN:
        raise PermissionError("Seuls les groupes dont l’origine locale est confirmée peuvent être attribués par cette application.")
