import unittest
from access_manager.services.access import AccessService
from access_manager.services.previews import PreviewSigner
from access_manager.services import permissions
from access_manager.tests.fakes import FakeRepository

class AccessServiceTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.service = AccessService(self.repo, signer=PreviewSigner(secret=b'test-only-secret'))
        self.actor = self.service.authenticate({'Test-Actor':'root'})

    def preview(self, actor=None, group='viewer'):
        return self.service.compute_preview(actor or self.actor,'P','target',group)

    def submit(self, token=None, actor=None, ack=True, target='target'):
        return self.service.add_group_to_user(actor or self.actor,token or self.preview()['token'],ack,'P',target,'viewer')

    def test_add_preserves_memberships(self):
        self.assertTrue(self.submit()['ok'])
        self.assertEqual(set(self.repo.users['target']['groups']), {'existing','viewer'})
        self.assertEqual(self.repo.users['target']['email'],'preserved')
        self.assertEqual(self.repo.writes,1)
    def test_already_member_is_noop(self):
        self.repo.users['target']['groups'].append('viewer')
        self.assertTrue(self.submit()['noOp'])
        self.assertEqual(self.repo.writes,0)
    def test_admin_group_denied(self):
        with self.assertRaises(PermissionError): self.preview(group='administrators')
    def test_forged_group_denied(self):
        with self.assertRaises(ValueError): self.preview(group='forged')
    def test_forged_project_denied(self):
        with self.assertRaises(KeyError): self.service.compute_preview(self.actor,'forged','target','viewer')
    def test_default_delegate_denied(self):
        actor=self.service.authenticate({'Test-Actor':'operator'})
        with self.assertRaises(PermissionError): self.submit(self.preview(actor)['token'],actor)
        self.assertEqual(self.repo.writes,0)
    def test_explicit_delegate_can_assign(self):
        self.service.policy={'P':['viewer']}
        actor=self.service.authenticate({'Test-Actor':'operator'})
        self.assertTrue(self.submit(self.preview(actor)['token'],actor)['ok'])
    def test_cross_project_denied(self):
        self.service.policy={'P':['viewer']}
        self.repo.projects['OTHER']={'owner':'other','permissions':[{'group':'viewer','readProjectContent':True}]}
        actor=self.service.authenticate({'Test-Actor':'operator'})
        with self.assertRaises(PermissionError): self.submit(self.preview(actor)['token'],actor)
        self.assertEqual(self.repo.writes,0)
    def test_nonread_cross_project_grants_detected(self):
        self.service.policy={'P':['viewer']}
        self.repo.projects['OTHER']={'owner':'other','permissions':[{'group':'viewer','editPermissions':True}]}
        actor=self.service.authenticate({'Test-Actor':'operator'})
        self.assertTrue(any('OTHER' in reason for reason in self.preview(actor)['blockedReasons']))
    def test_stale_membership_denied(self):
        token=self.preview()['token']
        self.repo.users['target']['groups'].append('new')
        with self.assertRaises(PermissionError): self.submit(token)
    def test_stale_acl_denied(self):
        token=self.preview()['token']
        self.repo.projects['P']['permissions'][0]['writeProjectContent']=True
        with self.assertRaises(PermissionError): self.submit(token)
    def test_disabled_target_denied(self):
        self.repo.users['target']['enabled']=False
        with self.assertRaises(ValueError): self.preview()
    def test_missing_enabled_status_denied(self):
        del self.repo.users['target']['enabled']
        with self.assertRaises(ValueError): self.preview()
    def test_token_bound_to_actor(self):
        actor=self.service.authenticate({'Test-Actor':'operator'})
        with self.assertRaises(PermissionError): self.submit(self.preview()['token'],actor)
    def test_token_bound_to_selection(self):
        with self.assertRaises(PermissionError): self.submit(self.preview()['token'],target='different')
    def test_ack_required(self):
        with self.assertRaises(PermissionError): self.submit(ack=False)
    def test_forged_signature_denied(self):
        with self.assertRaises(PermissionError): self.submit(self.preview()['token']+'x')
    def test_expired_preview_denied(self):
        self.service.signer.ttl=-1
        with self.assertRaises(PermissionError): self.submit(self.preview()['token'])
    def test_missing_browser_identity_denied(self):
        with self.assertRaises(PermissionError): self.service.authenticate({})
    def test_exact_login_required(self):
        self.repo.users['jane']={'login':'jane','enabled':True,'groups':[]}
        with self.assertRaises(PermissionError): self.service.authenticate({'Test-Actor':'jane@example.org'})
    def test_superadmin_denied(self):
        self.repo.groups['viewer']['superAdmin']=True
        with self.assertRaises(PermissionError): self.preview()
    def test_unknown_origin_denied(self):
        del self.repo.groups['viewer']['sourceType']
        with self.assertRaises(PermissionError): self.preview()
    def test_unreadable_group_fails_closed(self):
        self.repo.get_group_definition=lambda name: (_ for _ in ()).throw(RuntimeError('unreadable'))
        with self.assertRaises(RuntimeError): self.preview()
    def test_edit_permissions_is_not_admin(self):
        perms={'owner':'other','permissions':[{'group':'g','editPermissions':True}]}
        self.assertFalse(permissions.permission_admin_for_login_or_groups(perms,'operator',['g']))
    def test_duplicate_acl_rows_merged(self):
        self.repo.projects['P']['permissions'].append({'group':'viewer','writeProjectContent':True})
        group=self.service.groups_on_project_acl('P',self.repo.groups)['viewer']
        self.assertEqual(group['tier'],2)
        self.assertTrue(group['grants']['readProjectContent'])
    def test_rank_considers_scope(self):
        group=self.service.ranked_groups(self.actor,'P')[0][1]
        rank=permissions.rank_group
        self.assertLess(rank(group,[],'P'),rank(group,[{'projectKey':'OTHER','grants':{'readProjectContent':True}}],'P'))
    def test_all_global_powers_disclosed(self):
        caps=permissions.group_global_capabilities({'mayManageClusters':True,'mayCreateEnterpriseAssetCollections':True})
        self.assertEqual(len(caps),2)

if __name__=='__main__': unittest.main()
