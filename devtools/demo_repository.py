"""Local demonstration data; no network or real DSS membership operations."""
from copy import deepcopy


class DemoRepository:
    def __init__(self):
        self.users = {
            "agent.demo": {
                "login": "agent.demo", "enabled": True, "groups": ["administrators"]
            },
            "beneficiaire.demo": {
                "login": "beneficiaire.demo", "enabled": True, "groups": []
            },
        }
        self.groups = {
            "administrators": {
                "name": "administrators", "admin": True, "sourceType": "LOCAL"
            },
            "consultation_app": {
                "name": "consultation_app", "admin": False, "sourceType": "LOCAL"
            },
            "contributeurs_app": {
                "name": "contributeurs_app", "admin": False, "sourceType": "LOCAL"
            },
        }
        self.projects = {
            "PROJET_DEMONSTRATION": {
                "owner": "agent.demo",
                "permissions": [
                    {"group": "consultation_app", "readDashboards": True},
                    {
                        "group": "contributeurs_app", "readProjectContent": True,
                        "writeProjectContent": True,
                    },
                ],
            }
        }

    def auth_info(self, headers):
        return {"authIdentifier": "agent.demo"}

    def list_users(self):
        return deepcopy(list(self.users.values()))

    def get_user_raw(self, login):
        return deepcopy(self.users[login])

    def list_groups(self):
        return deepcopy(list(self.groups.values()))

    def get_group_definition(self, name):
        return deepcopy(self.groups[name])

    def list_projects(self):
        return [{"projectKey": key} for key in self.projects]

    def get_project_permissions(self, key):
        return deepcopy(self.projects[key])

    def add_group(self, login, group):
        memberships = self.users[login]["groups"]
        if group in memberships:
            return False
        memberships.append(group)
        return True
