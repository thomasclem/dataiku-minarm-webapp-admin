"""In-memory collaborators; never connect to a DSS instance."""
import copy
from types import SimpleNamespace

class FakeRepository:
    def __init__(self):
        self.users = {
            'root': {'login':'root','enabled':True,'groups':['administrators']},
            'operator': {'login':'operator','enabled':True,'groups':[]},
            'target': {'login':'target','enabled':True,'userProfile':'READER','groups':['existing'],'email':'preserved'},
        }
        self.groups = {
            'administrators': {'name':'administrators','admin':True,'sourceType':'LOCAL'},
            'viewer': {'name':'viewer','admin':False,'sourceType':'LOCAL'},
        }
        self.projects = {'P': {'owner':'operator','permissions':[{'group':'viewer','readProjectContent':True}]}}
        self.writes = 0
        self.capacity = True

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

    def reader_capacity(self):
        return {'available':self.capacity, 'message':'Reader disponible' if self.capacity else 'READER indisponible'}
    def create_reader(self, login, name, email, password, source_type):
        if login in self.users: raise ValueError('Duplicate')
        self.users[login]={'login':login,'enabled':True,'userProfile':'READER','groups':[],'displayName':name,'email':email,'sourceType':source_type}
        self.writes+=1
    def add_groups(self, login, groups, required_profile='READER'):
        if self.users[login].get('userProfile') != required_profile: raise ValueError('Profile')
        self.users[login]['groups']=sorted(set(self.users[login]['groups'])|set(groups))
        self.writes+=1
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
        self.users = {'target': {'login':'target','enabled':True,'userProfile':'READER','groups':['existing'],'email':'preserved','other':{'nested':True}}}
        self.writes = 0
    def get_user(self, login): return SimpleNamespace(get_settings=lambda: FakeSettings(self, login))
