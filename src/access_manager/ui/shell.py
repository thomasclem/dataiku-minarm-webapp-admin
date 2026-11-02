"""Institutional French layout; no SDK calls or service lookups."""
from dash import dcc, html
from ..features.access import ids
from ..features.access.layout import build_access_form, build_access_summary

def build_layout():
    return html.Div([
        dcc.Location(id=ids.URL, refresh=False),
        dcc.Store(id=ids.PREVIEW_TOKEN),
        dcc.Store(id=ids.PREVIEW_ALLOWED, data=False),
        html.Div([
            html.Header([
                html.Div([
                    html.H1("Gestion des habilitations"),
                    html.P("Attribution des accès aux applications et aux projets.", className="subtitle"),
                ]),
                html.Div([
                    html.Div(id=ids.OPERATOR, className="operator-pill"),
                    html.Button("Actualiser les données", id=ids.LOAD_BUTTON, n_clicks=0, className="secondary-button"),
                ], className="hero-actions"),
            ], className="hero"),
            html.Main([
                build_access_form(),
                build_access_summary(),
            ], className="workspace"),
        ], className="app-shell"),
    ])
