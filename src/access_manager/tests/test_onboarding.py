"""Authorization, provisioning and signed multi-project plans with no real writes."""
import copy
import unittest
from access_manager.services.access import AccessService
from access_manager.services.onboarding import ReaderOnboarding
from access_manager.services.previews import PreviewSigner
from access_manager.tests.fakes import FakeRepository


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.repo.users['target']['userProfile'] = 'READER'
        self.service = AccessService(self.repo, policy={'P':['viewer']}, signer=PreviewSigner(secret=b'reader-tests'))
        self.flow = ReaderOnboarding(self.service)
        self.actor = self.service.authenticate({'Test-Actor':'operator'})

    def test_create_reader_is_empty_and_cannot_select_another_profile(self):
        login=self.flow.create_reader(self.actor,'new.reader','New Reader','reader@example.org','supplied-password')
        self.assertEqual(login,'new.reader')
        self.assertEqual(self.repo.users[login]['groups'],[])
        self.assertEqual(self.repo.users[login]['userProfile'],'READER')
        self.assertNotIn('password',self.repo.users[login])

    def test_duplicate_is_not_overwritten(self):
        before=copy.deepcopy(self.repo.users['target'])
        with self.assertRaises(ValueError):
            self.flow.create_reader(self.actor,'target','Name','reader@example.org','password')
        self.assertEqual(self.repo.users['target'],before)
        self.assertEqual(self.repo.writes,0)

    def test_profile_capacity_and_missing_password_block_creation(self):
        self.repo.capacity=False
        with self.assertRaises(PermissionError):
            self.flow.create_reader(self.actor,'new','Name','reader@example.org','password')
        self.repo.capacity=True
        with self.assertRaises(ValueError):
            self.flow.create_reader(self.actor,'new','Name','reader@example.org','')
        self.assertEqual(self.repo.writes,0)

    def test_non_project_admin_cannot_provision_or_preview(self):
        actor=self.service.authenticate({'Test-Actor':'target'})
        with self.assertRaises(PermissionError): self.flow.creation_status(actor)
        with self.assertRaises(PermissionError): self.flow.preview(actor,['P'],'target')

    def test_single_plan_deduplicates_group_for_multiple_projects(self):
        self.repo.projects['Q']={'owner':'operator','permissions':[{'group':'viewer','readProjectContent':True}]}
        self.service.policy['Q']=['viewer']
        plan=self.flow.preview(self.actor,['Q','P'],'target')
        self.assertEqual(len(plan['assignments']),2)
        self.assertEqual([g['name'] for g in plan['groups']],['viewer'])
        result=self.flow.submit(self.actor,plan['token'],True,['P','Q'],'target')
        self.assertTrue(result['ok'])
        self.assertEqual(self.repo.users['target']['groups'],['existing','viewer'])
        self.assertEqual(self.repo.writes,1)

    def test_least_privilege_dashboard_group_preferred_over_content(self):
        self.repo.groups['dashboard']={'name':'dashboard','sourceType':'LOCAL','admin':False}
        self.repo.projects['P']['permissions'].append({'group':'dashboard','readDashboards':True})
        self.service.policy['P'].append('dashboard')
        self.assertEqual(self.flow.plan(self.actor,['P'],'target')['assignments'][0]['group'],'dashboard')

    def test_admin_write_global_external_unknown_and_outside_scope_rejected(self):
        mutations=[
            lambda: self.repo.groups['viewer'].update(admin=True),
            lambda: self.repo.groups['viewer'].update(mayCreateProjects=True),
            lambda: self.repo.groups['viewer'].update(sourceType='LDAP'),
            lambda: self.repo.projects['P']['permissions'][0].update(writeProjectContent=True),
            lambda: self.repo.projects['P']['permissions'][0].update(futurePermission=True),
            lambda: self.repo.projects.update(Q={'owner':'other','permissions':[{'group':'viewer','readDashboards':True}]}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.setUp();mutate()
                plan=self.flow.preview(self.actor,['P'],'target')
                self.assertFalse(plan['allowedToSubmit'])
                with self.assertRaises(PermissionError): self.flow.submit(self.actor,plan['token'],True,['P'],'target')
                self.assertEqual(self.repo.writes,0)

    def test_every_selected_project_must_be_administered(self):
        self.repo.projects['Q']={'owner':'someone','permissions':[]}
        with self.assertRaises(PermissionError): self.flow.preview(self.actor,['P','Q'],'target')

    def test_target_must_remain_reader(self):
        self.repo.users['target']['userProfile']='FULL_DESIGNER'
        with self.assertRaises(PermissionError): self.flow.preview(self.actor,['P'],'target')

    def test_missing_project_group_blocks_entire_batch(self):
        self.repo.projects['Q']={'owner':'operator','permissions':[]}
        plan=self.flow.preview(self.actor,['P','Q'],'target')
        self.assertFalse(plan['allowedToSubmit'])
        with self.assertRaises(PermissionError): self.flow.submit(self.actor,plan['token'],True,['P','Q'],'target')
        self.assertEqual(self.repo.writes,0)

    def test_snapshot_changes_and_browser_tampering_block_all_writes(self):
        for change in ['acl','profile','membership','selection','ack','actor','policy']:
            with self.subTest(change=change):
                self.setUp();plan=self.flow.preview(self.actor,['P'],'target')
                actor,projects,ack=self.actor,['P'],True
                if change=='acl': self.repo.projects['P']['permissions'][0]['readDashboards']=True
                if change=='profile': self.repo.users['target']['userProfile']='FULL_DESIGNER'
                if change=='membership': self.repo.users['target']['groups'].append('viewer')
                if change=='selection': projects=['Q']
                if change=='ack': ack=False
                if change=='actor': actor=self.service.authenticate({'Test-Actor':'root'})
                if change=='policy': self.service.policy['P']=[]
                with self.assertRaises(PermissionError): self.flow.submit(actor,plan['token'],ack,projects,'target')
                self.assertEqual(self.repo.writes,0)

    def test_second_preview_is_noop_after_successful_assignment(self):
        plan=self.flow.preview(self.actor,['P'],'target')
        self.flow.submit(self.actor,plan['token'],True,['P'],'target')
        fresh=self.flow.preview(self.actor,['P'],'target')
        self.assertTrue(self.flow.submit(self.actor,fresh['token'],True,['P'],'target')['noOp'])
        self.assertEqual(self.repo.writes,1)

class RepositoryReaderTest(unittest.TestCase):
    def setUp(self):
        from access_manager.repositories.dss import DSSRepository
        from access_manager.tests.fakes import FakeSDKClient
        self.client=FakeSDKClient()
        self.client.users['target']['userProfile']='READER'
        self.status={'base':{'valid':True,'expired':False,'userProfiles':['READER']},'limits':{'profileLimits':{'READER':{'licensed':{'licensedLimit':2},'countWithDemotedTo':1}}}}
        self.client.get_licensing_status=lambda: copy.deepcopy(self.status)
        self.repo=DSSRepository(lambda:self.client)

    def test_multiple_groups_saved_once_preserving_other_settings(self):
        before=copy.deepcopy(self.client.users['target'])
        self.repo.add_groups('target',['alpha','beta'])
        self.assertEqual(self.client.writes,1)
        self.assertEqual(self.client.users['target'],dict(before,groups=['alpha','beta','existing']))
        self.assertFalse(self.repo.add_groups('target',['alpha','beta']))
        self.assertEqual(self.client.writes,1)

    def test_changed_profile_prevents_save(self):
        self.client.users['target']['userProfile']='FULL_DESIGNER'
        with self.assertRaises(RuntimeError): self.repo.add_groups('target',['viewer'])
        self.assertEqual(self.client.writes,0)

    def test_capacity_is_strict_and_never_substitutes_another_profile(self):
        self.assertTrue(self.repo.reader_capacity()['available'])
        self.status['limits']['profileLimits']['READER']['countWithDemotedTo']=2
        self.assertFalse(self.repo.reader_capacity()['available'])
        self.status['limits']['profileLimits']['READER']['licensed']['licensedLimit']=-1
        self.assertTrue(self.repo.reader_capacity()['available'])
        self.status['base']['userProfiles']=['FULL_DESIGNER']
        self.assertFalse(self.repo.reader_capacity()['available'])
        self.status['base']['valid']=False
        self.assertFalse(self.repo.reader_capacity()['available'])

    def test_create_passes_exact_reader_and_empty_groups_to_sdk(self):
        self.client.list_users=lambda:[]
        calls=[]
        self.client.create_user=lambda *args,**kwargs:calls.append((args,kwargs))
        self.repo.create_reader('reader','Reader','reader@example.org','supplied','LOCAL')
        self.assertEqual(calls[0][0],('reader','supplied'))
        self.assertEqual(calls[0][1]['profile'],'READER')
        self.assertEqual(calls[0][1]['groups'],[])

class GroupDetectionTest(unittest.TestCase):
    setUp = OnboardingTest.setUp

    def test_sales_project_dga_is_detected_with_explicit_exclusion_reasons(self):
        self.repo.groups['DGA']={'name':'DGA','sourceType':'LOCAL','admin':False,'mayCreateProjects':True,'mayWriteSafeCode':True}
        self.repo.projects['SALES_MIGRATION_HEADLESS']={'owner':'operator','permissions':[
            {'group':'DGA','admin':False,'editPermissions':True,'readProjectContent':True,
             'writeProjectContent':True,'exportDatasetsData':True,'readDashboards':False,
             'writeDashboards':False,'moderateDashboards':False,'publishToDataCollections':True,
             'shareToWorkspaces':True,'runScenarios':False,'executeApp':False}
        ]}
        plan=self.flow.preview(self.actor,['SALES_MIGRATION_HEADLESS'],'target')
        self.assertEqual(len(plan['detectedGroups']),1)
        group=plan['detectedGroups'][0]
        self.assertEqual(group['name'],'DGA')
        self.assertFalse(group['eligible'])
        self.assertFalse(group['recommended'])
        self.assertTrue(any('globales' in reason for reason in group['reasons']))
        self.assertTrue(any('écriture' in reason for reason in group['reasons']))
        self.assertFalse(plan['allowedToSubmit'])
        with self.assertRaises(PermissionError):
            self.flow.submit(self.actor,plan['token'],True,['SALES_MIGRATION_HEADLESS'],'target')
        self.assertEqual(self.repo.writes,0)
        from access_manager.ui.components import render_reader_plan
        from plotly.utils import PlotlyJSONEncoder
        import json
        rendered=json.dumps(render_reader_plan(plan),cls=PlotlyJSONEncoder,ensure_ascii=False)
        self.assertIn('DGA',rendered)
        self.assertIn('Non attribuable',rendered)
        self.assertIn('Write project content',rendered)

    def test_eligible_first_and_alternatives_remain_visible(self):
        self.repo.groups['another']={'name':'another','sourceType':'LOCAL','admin':False}
        self.repo.groups['writer']={'name':'writer','sourceType':'LOCAL','admin':False}
        self.repo.projects['P']['permissions'] += [
            {'group':'another','readProjectContent':True,'writeProjectContent':False,'moderateDashboards':False},
            {'group':'writer','readProjectContent':True,'writeProjectContent':True},
        ]
        self.service.policy['P'].append('another')
        plan=self.flow.plan(self.actor,['P'],'target')
        self.assertEqual({g['name'] for g in plan['detectedGroups']},{'viewer','another','writer'})
        self.assertEqual(plan['detectedGroups'][-1]['name'],'writer')
        self.assertEqual(sum(g['recommended'] for g in plan['detectedGroups']),1)
        self.assertEqual(sum(g['eligible'] for g in plan['detectedGroups']),2)
        self.assertTrue(plan['allowedToSubmit'])

    def test_missing_definition_and_missing_delegation_approval_are_not_hidden(self):
        self.repo.projects['P']['permissions'].append({'group':'missing','readProjectContent':True})
        self.service.policy={}
        plan=self.flow.plan(self.actor,['P'],'target')
        self.assertEqual({g['name'] for g in plan['detectedGroups']},{'missing','viewer'})
        viewer=next(g for g in plan['detectedGroups'] if g['name']=='viewer')
        missing=next(g for g in plan['detectedGroups'] if g['name']=='missing')
        self.assertTrue(any('politique' in reason for reason in viewer['reasons']))
        self.assertTrue(any('définition' in reason for reason in missing['reasons']))
        self.assertFalse(plan['allowedToSubmit'])

    def test_group_without_consultation_is_detected_but_not_eligible(self):
        self.repo.projects['P']['permissions'][0]={'group':'viewer','readProjectContent':False}
        plan=self.flow.plan(self.actor,['P'],'target')
        self.assertEqual(plan['detectedGroups'][0]['name'],'viewer')
        self.assertFalse(plan['detectedGroups'][0]['eligible'])
        self.assertIn('Aucun droit de consultation',plan['detectedGroups'][0]['reasons'][0])
