"""Exercise actual Dash HTTP callbacks against an in-memory repository."""
import unittest
from dash import Dash
from access_manager.features.access.callbacks import register_callbacks
from access_manager.services.access import AccessService
from access_manager.services.previews import PreviewSigner
from access_manager.ui.shell import build_layout
from access_manager.tests.fakes import FakeRepository

class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepository()
        self.service=AccessService(self.repo,signer=PreviewSigner(secret=b'callback-tests'))
        self.app=Dash(__name__)
        self.app.layout=build_layout
        register_callbacks(self.app,self.service)
        self.client=self.app.server.test_client()

    def post(self, name, inputs, state=None, actor=None):
        key,meta=next((key,meta) for key,meta in self.app.callback_map.items() if meta['callback'].__name__==name)
        outputs=meta['output']
        if isinstance(outputs,list):
            outputs=[{'id':o.component_id,'property':o.component_property} for o in outputs]
        else:
            outputs={'id':outputs.component_id,'property':outputs.component_property}
        payload={'output':key,'outputs':outputs,'inputs':inputs,'state':state or [],'changedPropIds':[inputs[0]['id']+'.'+inputs[0]['property']]}
        return self.client.post('/_dash-update-component',json=payload,headers={'Test-Actor':actor} if actor else {})

    def test_progression_unlocks_only_completed_predecessors(self):
        for project, user, group, reviewed, expected in [
            (None, None, None, False, (True, True, True, True)),
            ('P', None, None, False, (False, True, True, True)),
            ('P', 'target', None, False, (False, False, True, True)),
            ('P', 'target', 'viewer', False, (False, False, False, True)),
            ('P', 'target', 'viewer', True, (False, False, False, False)),
            (None, 'target', 'viewer', True, (True, True, True, True)),
        ]:
            with self.subTest(project=project, user=user, group=group, reviewed=reviewed):
                inputs=[{'id':i, 'property':p, 'value':v} for i,p,v in [
                    ('project-dropdown','value',project), ('target-user-dropdown','value',user),
                    ('group-dropdown','value',group), ('preview-allowed','data',reviewed)]]
                response=self.post('update_progression', inputs)
                self.assertEqual(response.status_code,200)
                result=response.get_json()['response']
                actual=tuple(result[i]['disabled'] for i in ['target-user-dropdown','group-dropdown','preview-button','ack-section'])
                self.assertEqual(actual,expected)

    def test_clearing_predecessor_clears_groups_without_repository_access(self):
        response=self.post('load_groups_for_project',[
            {'id':'project-dropdown','property':'value','value':None},
            {'id':'target-user-dropdown','property':'value','value':'target'}])
        self.assertEqual(response.status_code,200)
        result=response.get_json()['response']['group-dropdown']
        self.assertEqual(result,{'options':[], 'value':None})
        self.assertEqual(self.repo.writes,0)

    def test_unauthenticated_load_returns_no_accounts(self):
        response=self.post('load_projects_and_users',[{'id':'load-button','property':'n_clicks','value':1}])
        self.assertEqual(response.status_code,200)
        result=response.get_json()['response']
        self.assertEqual(result['project-dropdown']['options'],[])
        self.assertEqual(result['target-user-dropdown']['options'],[])
        self.assertEqual(self.repo.writes,0)

    def test_authenticated_load_filters_administered_projects(self):
        self.repo.projects['PRIVATE']={'owner':'someone','permissions':[]}
        response=self.post('load_projects_and_users',[{'id':'load-button','property':'n_clicks','value':1}],actor='operator')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.get_json()['response']['project-dropdown']['options'],[{'label':'P','value':'P'}])

    def test_changed_browser_selection_blocks_signed_submit(self):
        actor=self.service.authenticate({'Test-Actor':'root'})
        preview=self.service.compute_preview(actor,'P','target','viewer')
        values=[('preview-token','data',preview['token']),('ack-scope','value',['ack']),('project-dropdown','value','P'),('target-user-dropdown','value','different'),('group-dropdown','value','viewer')]
        response=self.post('submit_assignment',[{'id':'add-button','property':'n_clicks','value':1}],state=[{'id':i,'property':p,'value':v} for i,p,v in values],actor='root')
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.repo.writes,0)

if __name__=='__main__': unittest.main()
