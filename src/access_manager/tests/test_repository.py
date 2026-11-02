import copy
import unittest
from access_manager.repositories.dss import DSSRepository
from access_manager.tests.fakes import FakeSDKClient

class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.client=FakeSDKClient()
        self.repository=DSSRepository(lambda: self.client)
    def test_public_sdk_preserves_unrelated_settings(self):
        before=copy.deepcopy(self.client.users['target'])
        self.assertTrue(self.repository.add_group('target','viewer'))
        after=copy.deepcopy(self.client.users['target'])
        self.assertEqual(set(after.pop('groups')),{'existing','viewer'})
        before.pop('groups')
        self.assertEqual(before,after)
    def test_duplicate_no_save(self):
        self.assertFalse(self.repository.add_group('target','existing'))
        self.assertEqual(self.client.writes,0)
    def test_disabled_user_never_saved(self):
        self.client.users['target']['enabled']=False
        with self.assertRaises(RuntimeError): self.repository.add_group('target','viewer')
        self.assertEqual(self.client.writes,0)
    def test_readback_failure_reported(self):
        from types import SimpleNamespace
        self.client.get_user=lambda login: SimpleNamespace(get_settings=lambda: SimpleNamespace(get_raw=lambda: copy.deepcopy(self.client.users[login]),save=lambda: None))
        with self.assertRaises(RuntimeError): self.repository.add_group('target','viewer')

if __name__=='__main__': unittest.main()
