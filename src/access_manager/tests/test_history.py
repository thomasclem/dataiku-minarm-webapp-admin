"""Managed history setup, append semantics, and grant/history partial failures."""
import copy
import json
from datetime import datetime
from types import SimpleNamespace
import unittest

from access_manager.services.history import HISTORY_SCHEMA, history_rows
from access_manager.services.onboarding import ReaderOnboarding
from access_manager.services.access import AccessService
from access_manager.services.previews import PreviewSigner
from access_manager.repositories.dss import DSSRepository
from access_manager.tests.fakes import FakeRepository


class GrantHistoryTest(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepository()
        self.service=AccessService(self.repo,policy={'P':['viewer']},signer=PreviewSigner(secret=b'history-test'))
        self.flow=ReaderOnboarding(self.service)
        self.actor=self.service.authenticate({'Test-Actor':'operator'})

    def submit(self, projects=None):
        projects=projects or ['P']
        preview=self.flow.preview(self.actor,projects,'target')
        return self.flow.submit(self.actor,preview['token'],True,projects,'target')

    def test_grants_are_recorded_with_actor_target_project_and_scope(self):
        result=self.submit()
        self.assertTrue(result['ok'])
        self.assertEqual([row['outcome'] for row in self.repo.history],['REQUESTED','GRANTED'])
        for row in self.repo.history:
            self.assertEqual(row['event_id'],result['eventId'])
            self.assertEqual(row['actor_login'],'operator')
            self.assertEqual(row['beneficiary_login'],'target')
            self.assertEqual(row['project_key'],'P')
            self.assertEqual(row['group_name'],'viewer')
            self.assertEqual(row['user_profile'],'READER')
            self.assertEqual(json.loads(row['project_permissions_json']),{'readProjectContent':True})
            self.assertEqual(json.loads(row['affected_projects_json']),['P'])
            self.assertIsNotNone(datetime.fromisoformat(row['ts_utc'].replace('Z','+00:00')).tzinfo)
        self.assertNotEqual(self.repo.history[0]['record_id'],self.repo.history[1]['record_id'])

    def test_no_password_headers_preview_or_raw_user_settings_in_history(self):
        self.repo.users['target']['password']='SENSITIVE_PASSWORD'
        self.actor['raw']['privateCredential']='PRIVATE_CREDENTIAL'
        self.submit()
        payload=json.dumps(self.repo.history)
        self.assertNotIn('SENSITIVE_PASSWORD',payload)
        self.assertNotIn('PRIVATE_CREDENTIAL',payload)
        self.assertNotIn('token',payload)
        self.assertEqual(set(self.repo.history[0]),{column['name'] for column in HISTORY_SCHEMA})

    def test_multiple_projects_recorded_even_when_group_is_added_only_once(self):
        self.repo.projects['Q']={'owner':'operator','permissions':[{'group':'viewer','readProjectContent':True}]}
        self.service.policy['Q']=['viewer']
        self.submit(['P','Q'])
        granted=[row for row in self.repo.history if row['outcome']=='GRANTED']
        self.assertEqual({row['project_key'] for row in granted},{'P','Q'})
        self.assertEqual(self.repo.writes,1)
        self.assertEqual(len({row['event_id'] for row in self.repo.history}),1)

    def test_previews_and_rejected_requests_write_no_history(self):
        preview=self.flow.preview(self.actor,['P'],'target')
        self.assertEqual(self.repo.history,[])
        with self.assertRaises(PermissionError):
            self.flow.submit(self.actor,preview['token'],False,['P'],'target')
        self.assertEqual(self.repo.history,[])

    def test_unavailable_history_prevents_membership_change(self):
        def fail(rows): raise RuntimeError('unavailable')
        self.repo.append_access_history=fail
        result=self.submit()
        self.assertFalse(result['ok'])
        self.assertEqual(self.repo.writes,0)
        self.assertEqual(self.repo.users['target']['groups'],['existing'])

    def test_history_completion_failure_does_not_report_full_success(self):
        append=self.repo.append_access_history
        def fail_completion(rows):
            if rows[0]['outcome']=='GRANTED': raise RuntimeError('unavailable')
            append(rows)
        self.repo.append_access_history=fail_completion
        result=self.submit()
        self.assertFalse(result['ok'])
        self.assertEqual(self.repo.writes,1)
        self.assertIn('Ne relancez pas',result['message'])
        self.assertEqual(self.repo.history[0]['outcome'],'REQUESTED')
        self.assertEqual(self.repo.history[0]['event_id'],result['eventId'])

    def test_uncertain_save_is_not_recorded_as_granted(self):
        def uncertain(*args,**kwargs): raise RuntimeError('save/readback failed')
        self.repo.add_groups=uncertain
        result=self.submit()
        self.assertFalse(result['ok'])
        self.assertEqual([r['outcome'] for r in self.repo.history],['REQUESTED','UNVERIFIED'])

    def test_membership_added_concurrently_is_not_reported_as_new_grant(self):
        def concurrent(*args,**kwargs):
            self.repo.users['target']['groups'].append('viewer')
            return False
        self.repo.add_groups=concurrent
        result=self.submit()
        self.assertTrue(result['noOp'])
        self.assertEqual(self.repo.history[-1]['outcome'],'ALREADY_MEMBER')
        self.assertEqual(self.repo.writes,0)

    def test_repeated_attribution_preserves_history_and_marks_noop(self):
        first=self.submit()
        before=copy.deepcopy(self.repo.history)
        second=self.submit()
        self.assertTrue(second['ok'])
        self.assertTrue(second['noOp'])
        self.assertEqual(self.repo.history[:2],before)
        self.assertEqual([r['outcome'] for r in self.repo.history],['REQUESTED','GRANTED','REQUESTED','ALREADY_MEMBER'])
        self.assertNotEqual(first['eventId'],second['eventId'])
        self.assertEqual(self.repo.writes,1)


class FakeHistoryDataset:
    def __init__(self):
        self.rows=[{'existing':'untouched'}]
        self.columns=copy.deepcopy(HISTORY_SCHEMA)
        self.raw={'managed':True,'params':{'connection':'managed-test'}}
        self.spec_item={}
        self.writer_opened=0
        self.schema_writes=0
    def get_settings(self): return SimpleNamespace(get_raw=lambda:self.raw)
    def get_schema(self): return {'columns':copy.deepcopy(self.columns)}
    def set_schema(self,schema):
        self.columns=copy.deepcopy(schema['columns']); self.schema_writes+=1
    def get_as_core_dataset(self): return self
    def get_writer(self):
        self.writer_opened+=1
        if self.spec_item.get('appendMode') is not True: raise AssertionError('Append mode not enabled')
        return self
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def write_row_dict(self,row): self.rows.append(copy.deepcopy(row))


class HistoryRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.dataset=FakeHistoryDataset()
        self.exists=True
        self.created=[]
        self.stores=[]
        class Builder:
            def __init__(inner,outer): inner.outer=outer
            def already_exists(inner): return inner.outer.exists
            def with_store_into(inner,name): inner.outer.stores.append(name)
            def create(inner,overwrite=False):
                self.created.append(overwrite)
                self.exists=True
                return self.dataset
        self.project=SimpleNamespace(
            get_dataset=lambda name:self.dataset,
            new_managed_dataset=lambda name:Builder(self),
        )
        self.repo=DSSRepository(lambda:SimpleNamespace(get_project=lambda key:self.project))
        self.row={c['name']:'test' for c in HISTORY_SCHEMA}

    def test_append_preserves_prior_rows_without_schema_rewrite(self):
        self.repo.append_access_history([self.row])
        self.repo.append_access_history([dict(self.row,record_id='second')])
        self.assertEqual(self.dataset.rows[0],{'existing':'untouched'})
        self.assertEqual(len(self.dataset.rows),3)
        self.assertEqual(self.dataset.writer_opened,2)
        self.assertEqual(self.dataset.schema_writes,0)

    def test_existing_compatible_dataset_is_not_recreated(self):
        result=self.repo.provision_access_history('managed-test')
        self.assertFalse(result['created'])
        self.assertEqual(self.created,[])
        self.assertEqual(self.dataset.schema_writes,0)
        self.assertEqual(self.dataset.writer_opened,0)

    def test_new_dataset_is_managed_and_never_overwrites(self):
        self.exists=False
        result=self.repo.provision_access_history('managed-test')
        self.assertTrue(result['created'])
        self.assertEqual(self.created,[False])
        self.assertEqual(self.stores,['managed-test'])
        self.assertEqual(self.dataset.columns,HISTORY_SCHEMA)

    def test_unmanaged_incompatible_or_different_connection_are_refused(self):
        self.dataset.raw['managed']=False
        with self.assertRaises(RuntimeError): self.repo.append_access_history([self.row])
        self.dataset.raw['managed']=True
        self.dataset.columns=[]
        with self.assertRaises(RuntimeError): self.repo.append_access_history([self.row])
        self.dataset.columns=copy.deepcopy(HISTORY_SCHEMA)
        with self.assertRaises(RuntimeError): self.repo.provision_access_history('different-connection')
        self.assertEqual(self.dataset.writer_opened,0)
        self.assertEqual(self.created,[])

    def test_unexpected_row_fields_are_rejected_before_write(self):
        with self.assertRaises(ValueError): self.repo.append_access_history([dict(self.row,password='secret')])
        self.assertEqual(self.dataset.writer_opened,0)
