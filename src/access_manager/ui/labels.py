"""French permission labels; raw SDK keys remain unchanged."""
from typing import Any, Dict, List, Optional, Tuple
PERMISSION_LABELS = {
    "readDashboards": "Consultation des tableaux de bord",
    "readProjectContent": "Lecture du projet",
    "writeDashboards": "Modification des tableaux de bord",
    "writeProjectContent": "Modification du projet",
    "runScenarios": "Exécution des scénarios",
    "executeApp": "Exécution des applications",
    "exportDatasetsData": "Export des données",
    "manageDashboardAuthorizations": "Gestion des autorisations de tableaux de bord",
    "manageExposedElements": "Gestion des éléments exposés",
    "manageAdditionalDashboardUsers": "Gestion des utilisateurs supplémentaires de tableaux de bord",
    "editPermissions": "Gestion des permissions",
    "admin": "Administration du projet",
    "mayCreateProjects": "Création de projets",
    "mayCreateProjectsFromMacros": "Création de projets depuis des macros",
    "mayCreateProjectsFromTemplates": "Création de projets depuis des modèles",
    "mayCreateCodeEnvs": "Création d’environnements de code",
    "mayCreatePublishedAPIServices": "Création de services d’API publiés",
    "mayWriteSafeCode": "Écriture de code sûr",
    "mayWriteUnsafeCode": "Écriture de code non restreint",
    "mayCreateActiveWebContent": "Création de contenu web actif",
    "mayCreateWorkspaces": "Création d’espaces de travail",
    "mayShareToWorkspaces": "Partage vers les espaces de travail",
    "mayPublishToDataCollections": "Publication dans les collections de données",
    "isAdmin": "Administration de l’instance",
    "superAdmin": "Super-administration de l’instance",
    "publishToDataCollections": "Publication dans les collections de données",
    "shareToWorkspaces": "Partage vers les espaces de travail",
    "mayCreateDataCollections": "Création de collections de données",
    "mayWriteInRootProjectFolder": "Écriture dans le dossier racine des projets",
}

DROPDOWN_LABELS = {
    "search": "Rechercher…",
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
    return PERMISSION_LABELS.get(name, f"Droit technique non reconnu : {name}")


def permission_labels(names) -> List[str]:
    return [permission_label(name) for name in sorted(names or [])]
