import ast
from collections import Counter
from pathlib import Path
import unittest
from dash import Dash
from access_manager.main import render_dash_webapp
from access_manager.features.access import ids

class WiringTest(unittest.TestCase):
    def setUp(self):
        self.app=Dash(__name__)
        self.service=render_dash_webapp(self.app)
        self.client=self.app.server.test_client()
    def test_initial_layout_and_dependencies_served(self):
        self.assertEqual(self.client.get('/_dash-layout').status_code,200)
        self.assertEqual(self.client.get('/_dash-dependencies').status_code,200)
        self.assertEqual(len(self.app.callback_map),8)
    def test_each_callback_component_exists_exactly_once(self):
        counts=Counter()
        def visit(node):
            if isinstance(node,(list,tuple)):
                for child in node: visit(child)
            elif hasattr(node,'to_plotly_json'):
                data=node.to_plotly_json()['props']
                if 'id' in data: counts[data['id']]+=1
                visit(data.get('children'))
        visit(self.app.layout())
        for name in vars(ids):
            if name.isupper(): self.assertEqual(counts[getattr(ids,name)],1)
        for callback in self.app.callback_map.values():
            for item in callback['inputs']+callback['state']:
                self.assertEqual(counts[item['id']],1)
    def test_formal_french_shell_and_preserved_placeholders(self):
        page=self.client.get('/').get_data(as_text=True)
        self.assertIn('Gestion des habilitations',page)
        self.assertIn('lang="fr"',page)
        self.assertNotIn('{%app_entry%}',page)
    def test_initializer_accepts_injected_repository(self):
        from access_manager.tests.fakes import FakeRepository
        repository = FakeRepository()
        app = Dash('injected_repository_test')
        service = render_dash_webapp(app, repository=repository, policy={'P':['viewer']})
        self.assertIs(service.repository, repository)
        self.assertEqual(service.policy, {'P':['viewer']})
        self.assertEqual(app.server.test_client().get('/_dash-layout').status_code, 200)
    def test_domain_does_not_import_ui_or_sdk(self):
        root=Path(__file__).parents[1]/'services'
        for file in root.glob('*.py'):
            tree=ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): names=[alias.name for alias in node.names]
                elif isinstance(node,ast.ImportFrom): names=[node.module or '']
                else: continue
                self.assertFalse(any(name.split('.')[0] in {'dash','flask','dataiku','dataikuapi'} for name in names),str(file))

if __name__=='__main__': unittest.main()
