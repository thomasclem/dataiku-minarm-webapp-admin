"""English DSS permission names in the French interface; SDK keys are unchanged."""
from typing import Any, Dict, List, Optional, Tuple
PERMISSION_LABELS = {
    'readDashboards': 'Read dashboards',
    'readProjectContent': 'Read project content',
    'writeDashboards': 'Write dashboards',
    'writeProjectContent': 'Write project content',
    'runScenarios': 'Run scenarios',
    'executeApp': 'Execute app',
    'exportDatasetsData': 'Export datasets',
    'manageDashboardAuthorizations': 'Manage authorized objects',
    'manageExposedElements': 'Manage shared objects',
    'manageAdditionalDashboardUsers': 'Manage additional dashboard users',
    'editPermissions': 'Edit permissions',
    'admin': 'Admin',
    'mayCreateProjects': 'Create projects',
    'mayCreateProjectsFromMacros': 'Create projects using macros',
    'mayCreateProjectsFromTemplates': 'Create projects using templates',
    'mayCreateProjectsFromDataikuApps': 'Create projects from Dataiku applications',
    'mayCreateCodeEnvs': 'Create code envs',
    'mayCreatePublishedAPIServices': 'Create published API services',
    'mayCreatePublishedProjects': 'Create published projects',
    'mayWriteSafeCode': 'Write isolated code',
    'mayWriteUnsafeCode': 'Write unisolated code',
    'mayCreateActiveWebContent': 'Create active Web content',
    'mayCreateWorkspaces': 'Create workspaces',
    'mayShareToWorkspaces': 'Publish on workspaces',
    'mayPublishToDataCollections': 'Publish to Catalog Collections',
    'isAdmin': 'Administrator',
    'superAdmin': 'Super administrator',
    'publishToDataCollections': 'Publish to Catalog Collections',
    'shareToWorkspaces': 'Publish on workspaces',
    'mayCreateDataCollections': 'Create Catalog Collections',
    'mayWriteInRootProjectFolder': 'Write in root project folder',
    'mayManageUDM': 'Manage user-defined meanings',
    'mayCreateAuthenticatedConnections': 'Create personal connections',
    'mayDevelopPlugins': 'Develop plugins',
    'mayEditLibFolders': 'Edit lib folders',
    'mayManageCodeEnvs': 'Manage all code envs',
    'mayManageClusters': 'Manage all clusters',
    'mayCreateClusters': 'Create clusters',
    'mayManageCodeStudioTemplates': 'Manage all Code Studio templates',
    'mayCreateCodeStudioTemplates': 'Create Code Studio templates',
    'mayViewIndexedHiveConnections': 'View indexed Hive connections',
    'mayManageFeatureStore': 'Manage Feature Store',
    'mayManageEnterpriseAssetLibrary': 'Manage Enterprise Asset Library',
    'mayCreateEnterpriseAssetCollections': 'Create Enterprise Asset Collections',
}

DROPDOWN_LABELS = {
    "search": "Rechercher…",
    "select_all": "Tout sélectionner",
    "selected_count": "{num_selected} sélectionnés",
    "deselect_all": "Tout désélectionner",
    "clear_search": "Effacer la recherche",
    "clear_selection": "Effacer la sélection",
    "no_options_found": "Aucun résultat",
}

def group_option_label(group, affected_projects):
    """Concise selection label; full permissions belong in the review panel."""
    count = len(affected_projects)
    scope = "1 projet" if count == 1 else f"{count} projets"
    parts = [group["name"], scope]
    if group["isAdmin"]:
        parts.append("Non attribuable")
    elif group.get("globalCapabilities"):
        parts.append("Droits globaux")
    return " · ".join(parts)

def permission_label(name: str) -> str:
    return PERMISSION_LABELS.get(name, f"Unknown permission: {name}")


def permission_labels(names) -> List[str]:
    return [permission_label(name) for name in sorted(names or [])]
