"""In-memory collaborators; never connect to a DSS instance."""
import copy
from types import SimpleNamespace

class FakeRepository:
    def __init__(self):
        self.users = {
            'root': {'login':'root','enabled':True,'groups':['administrators']},
            'operator': {'login':'operator','enabled':True,'groups':[]},
            'target': {'login':'target','enabled':True,'groups':['existing'],'email':'preserved'},
        }
        self.groups = {
            'administrators': {'name':'administrators','admin':True,'sourceType':'LOCAL'},
            'viewer': {'name':'viewer','admin':False,'sourceType':'LOCAL'},
        }
        self.projects = {'P': {'owner':'operator','permissions':[{'group':'viewer','readProjectContent':True}]}}
        self.writes = 0

    def auth_info(self, headers): return {'authIdentifier': headers.get('Test-Actor', '')}
    def list_users(self): return copy.deepcopy(list(self.users.values()))
    def get_user_raw(self, login): return copy.deepcopy(self.users[login])
    def list_groups(self): return copy.deepcopy(list(self.groups.values()))
    def get_group_definition(self, name): return copy.deepcopy(self.groups[name])
    def list_projects(self): return [{'projectKey': key} for key in self.projects]
    def get_project_permissions(self, key): return copy.deepcopy(self.projects[key])
    def add_group(self, login, group):
        if group in self.users[login]['groups']: return False
        self.users[login]['groups'].append(group)
        self.writes += 1
        return True

class FakeSettings:
    def __init__(self, client, login):
        self.client, self.login = client, login
        self.payload = copy.deepcopy(client.users[login])
    def get_raw(self): return self.payload
    def save(self):
        self.client.users[self.login] = copy.deepcopy(self.payload)
        self.client.writes += 1

class FakeSDKClient:
    def __init__(self):
        self.users = {'target': {'login':'target','enabled':True,'groups':['existing'],'email':'preserved','other':{'nested':True}}}
        self.writes = 0
    def get_user(self, login): return SimpleNamespace(get_settings=lambda: FakeSettings(self, login))
