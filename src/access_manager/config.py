"""Admin-owned access policy and application constants."""
from typing import Dict, List
HOST_PROJECT_KEY = "WEBAPP_ACCESS_MANAGER"
DELEGABLE_GROUPS_BY_PROJECT: Dict[str, List[str]] = {}
PREVIEW_TTL_SECONDS = 300
ADMIN_GROUP_NAMES = {"administrators", "space_administrators"}
LOCAL_ORIGIN = "LOCAL"
UNKNOWN_ORIGIN = "UNKNOWN"
SAFE_ERROR_TYPES = (PermissionError, ValueError)

LOW_PRIVILEGES = {"readDashboards"}
READ_PRIVILEGES = {"readProjectContent"}
WRITE_PRIVILEGES = {
    "writeDashboards", "writeProjectContent", "runScenarios", "executeApp",
    "exportDatasetsData", "manageDashboardAuthorizations", "manageExposedElements",
}
ADMIN_PRIVILEGES = {"admin", "editPermissions", "manageAdditionalDashboardUsers"}
IDENTITY_FIELDS = {"user", "group", "login", "name", "type", "sourceType", "origin"}

# Target: standard DSS with an explicitly licensed READER profile.
# Admin-owned setting; never taken from browser input. Cloud needs Launchpad.
READER_SOURCE_TYPE = 'LOCAL'

# Managed Flow dataset, provisioned explicitly once before enabling grants.
ACCESS_HISTORY_PROJECT_KEY = HOST_PROJECT_KEY
ACCESS_HISTORY_DATASET = 'access_granted_history'
