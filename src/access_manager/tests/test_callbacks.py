"""Exercise actual Dash HTTP adapters with an in-memory repository."""
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
        self.service=AccessService(self.repo, policy={'P':['viewer']}, signer=PreviewSigner(secret=b'callback-tests'))
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

    def test_unauthenticated_load_returns_no_accounts(self):
        response=self.post('load_projects_and_users',[{'id':'load-button','property':'n_clicks','value':1}])
        self.assertEqual(response.status_code,200)
        result=response.get_json()['response']
        self.assertEqual(result['project-dropdown']['options'],[])
        self.assertEqual(result['target-user-dropdown']['options'],[])
        self.assertEqual(self.repo.writes,0)

    def test_authenticated_load_filters_administered_projects_and_reader_profiles(self):
        self.repo.projects['PRIVATE']={'owner':'someone','permissions':[]}
        response=self.post('load_projects_and_users',[{'id':'load-button','property':'n_clicks','value':1}],actor='operator')
        self.assertEqual(response.status_code,200)
        result=response.get_json()['response']
        self.assertEqual(result['project-dropdown']['options'],[{'label':'P','value':'P'}])
        self.assertEqual(result['target-user-dropdown']['options'],[{'label':'target','value':'target'}])

    def test_progressive_sections_are_disabled_until_previous_filled(self):
        for target, projects, allowed, ack, expected in [
            (None,[],False,[],(True,True,True,True)),
            ('target',[],False,[],(False,True,True,True)),
            ('target',['P'],False,[],(False,False,True,True)),
            ('target',['P'],True,[],(False,False,False,True)),
            ('target',['P'],True,['ack'],(False,False,False,False)),
            (None,['P'],True,['ack'],(True,True,True,True)),
        ]:
            values=[('target-user-dropdown','value',target),('project-dropdown','value',projects),('preview-allowed','data',allowed),('ack-scope','value',ack)]
            response=self.post('update_progression',[{'id':i,'property':p,'value':v} for i,p,v in values])
            self.assertEqual(response.status_code,200)
            result=response.get_json()['response']
            self.assertEqual(tuple(result[i]['disabled'] for i in ['project-dropdown','preview-button','ack-section','add-button']),expected)

    def test_changed_selection_blocks_signed_submit(self):
        from access_manager.services.onboarding import ReaderOnboarding
        actor=self.service.authenticate({'Test-Actor':'operator'})
        preview=ReaderOnboarding(self.service).preview(actor,['P'],'target')
        state=[('preview-token','data',preview['token']),('ack-scope','value',['ack']),('target-user-dropdown','value','target'),('project-dropdown','value',['OTHER'])]
        response=self.post('submit_assignment',[{'id':'add-button','property':'n_clicks','value':1}],state=[{'id':i,'property':p,'value':v} for i,p,v in state],actor='operator')
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.repo.writes,0)

    def test_create_reader_selects_account_and_erases_password(self):
        values=[('new-login','value','new.reader'),('new-name','value','New Reader'),('new-email','value','new@example.org'),('new-password','value','input-password')]
        response=self.post('create_reader',[{'id':'create-button','property':'n_clicks','value':1}],state=[{'id':i,'property':p,'value':v} for i,p,v in values],actor='operator')
        self.assertEqual(response.status_code,200)
        data=response.get_json()['response']
        self.assertEqual(data['target-user-dropdown']['value'],'new.reader')
        self.assertEqual(data['new-password']['value'],'')
        self.assertNotIn('input-password',response.get_data(as_text=True))
        self.assertEqual(self.repo.users['new.reader']['userProfile'],'READER')
