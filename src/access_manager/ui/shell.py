"""Institutional French layout; no SDK calls or service lookups."""
from dash import dcc, html
from ..features.access import ids
from ..features.access.layout import build_access_form

def build_layout():
    return html.Div([
        dcc.Location(id=ids.URL, refresh=False),
        dcc.Store(id=ids.PREVIEW_TOKEN),
        dcc.Store(id=ids.PREVIEW_ALLOWED, data=False),
        dcc.Store(id=ids.CREATION_AVAILABLE, data=False),
        html.Div([
            html.Header([
                html.Div([
                    html.H1("Gestion des habilitations"),
                    html.P("Création de comptes Reader et attribution des accès aux projets.", className="subtitle"),
                ]),
                html.Div([
                    html.Div(id=ids.OPERATOR, className="operator-pill"),
                    html.Button("Actualiser les données", id=ids.LOAD_BUTTON, n_clicks=0, className="secondary-button"),
                ], className="hero-actions"),
            ], className="hero"),
            html.Main([
                build_access_form(),
            ], className="workspace"),
        ], className="app-shell"),
    ])
