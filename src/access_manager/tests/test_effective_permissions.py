"""UIF-dependent rights, conservative unknown settings and English DSS names."""
from types import SimpleNamespace
import unittest
from access_manager.repositories.dss import DSSRepository
from access_manager.services.access import AccessService
from access_manager.services.onboarding import ReaderOnboarding
from access_manager.services.permissions import group_global_capabilities
from access_manager.services.previews import PreviewSigner
from access_manager.tests.fakes import FakeRepository
from access_manager.ui.labels import permission_label


class EffectivePermissionTest(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepository()
        self.repo.groups['viewer']['mayWriteSafeCode']=True
        self.service=AccessService(self.repo,policy={'P':['viewer']},signer=PreviewSigner(secret=b'effective-permissions'))
        self.actor=self.service.authenticate({'Test-Actor':'operator'})
        self.flow=ReaderOnboarding(self.service)

    def test_saved_safe_code_flag_does_not_block_when_uif_disabled(self):
        self.repo.isolation_enabled=False
        plan=self.flow.preview(self.actor,['P'],'target')
        self.assertTrue(plan['allowedToSubmit'])
        group=plan['detectedGroups'][0]
        self.assertEqual(group['globalCapabilities'],[])
        self.assertEqual(group['inactiveGlobalCapabilities'],['mayWriteSafeCode'])
        self.assertTrue(self.repo.groups['viewer']['mayWriteSafeCode'])
        result=self.flow.submit(self.actor,plan['token'],True,['P'],'target')
        self.assertTrue(result['ok'])
        self.assertEqual(self.repo.writes,1)

    def test_enabled_or_unknown_uif_keeps_safe_code_visible_without_blocking(self):
        for enabled in (True,None):
            with self.subTest(enabled=enabled):
                self.repo.isolation_enabled=enabled
                plan=self.flow.preview(self.actor,['P'],'target')
                self.assertTrue(plan['allowedToSubmit'])
                self.assertIn('mayWriteSafeCode',plan['detectedGroups'][0]['globalCapabilities'])
                self.assertEqual(plan['detectedGroups'][0]['inactiveGlobalCapabilities'],[])
                with self.assertRaises(PermissionError): self.flow.submit(self.actor,plan['token'],False,['P'],'target')
                self.assertEqual(self.repo.writes,0)

    def test_enabling_uif_after_preview_blocks_submission_before_history_or_grant(self):
        self.repo.isolation_enabled=False
        preview=self.flow.preview(self.actor,['P'],'target')
        self.repo.isolation_enabled=True
        with self.assertRaises(PermissionError): self.flow.submit(self.actor,preview['token'],True,['P'],'target')
        self.assertEqual(self.repo.writes,0)
        self.assertEqual(self.repo.history,[])

    def test_other_global_capabilities_are_never_suppressed(self):
        definition={'mayWriteSafeCode':True,'mayWriteUnsafeCode':True,'mayCreateProjects':True,'mayFuturePermission':True}
        expected=['mayCreateProjects','mayFuturePermission','mayWriteUnsafeCode']
        self.assertEqual(group_global_capabilities(definition,isolation_enabled=False),expected)
        for unknown in (None,0,'false'):
            self.assertIn('mayWriteSafeCode',group_global_capabilities(definition,isolation_enabled=unknown))
        self.repo.groups['viewer']['mayWriteUnsafeCode']=True
        self.repo.isolation_enabled=False
        plan=self.flow.plan(self.actor,['P'],'target')
        self.assertTrue(plan['allowedToSubmit'])
        self.assertIn('mayWriteUnsafeCode',plan['detectedGroups'][0]['globalCapabilities'])

    def test_permission_names_are_english_and_use_current_dss_terminology(self):
        self.assertEqual(permission_label('readProjectContent'),'Read project content')
        self.assertEqual(permission_label('editPermissions'),'Edit permissions')
        self.assertEqual(permission_label('mayWriteSafeCode'),'Write isolated code')
        self.assertEqual(permission_label('mayWriteUnsafeCode'),'Write unisolated code')
        self.assertEqual(permission_label('futurePermission'),'Unknown permission: futurePermission')


class IsolationRepositoryTest(unittest.TestCase):
    def test_only_explicit_boolean_settings_are_trusted(self):
        for value in (False,True,None,0,1,'false'):
            with self.subTest(value=value):
                settings=SimpleNamespace(get_raw=lambda:{'impersonation':{'enabled':value},'sensitiveOtherSettings':'never-returned'})
                repository=DSSRepository(lambda:SimpleNamespace(get_general_settings=lambda:settings))
                self.assertIs(repository.get_isolation_enabled(),value if type(value) is bool else None)

    def test_missing_settings_or_read_failure_are_unknown(self):
        for raw in ({},{'impersonation':None},{'impersonation':{}},{'impersonation':'false'}):
            repository=DSSRepository(lambda:SimpleNamespace(get_general_settings=lambda:SimpleNamespace(get_raw=lambda:raw)))
            self.assertIsNone(repository.get_isolation_enabled())
        def unavailable(): raise PermissionError('unavailable')
        repository=DSSRepository(lambda:SimpleNamespace(get_general_settings=unavailable))
        self.assertIsNone(repository.get_isolation_enabled())
