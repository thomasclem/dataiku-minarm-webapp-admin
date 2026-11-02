"""Access feature layouts, colocated with callbacks and component IDs."""
from dash import dcc, html
from . import ids
from ...ui.components import render_empty_summary
from ...ui.labels import DROPDOWN_LABELS

def build_access_form():
    return html.Section([
        html.H2("Paramètres de l’attribution", className="card-heading"),
        html.P("Sélectionnez le projet, le bénéficiaire et le groupe, puis vérifiez les droits avant confirmation.", className="card-copy"),
        html.Div([
            html.Label([html.Span("01", className="step-number"), html.Span("Projet")], className="step-label", htmlFor=ids.PROJECT_DROPDOWN),
            dcc.Dropdown(id=ids.PROJECT_DROPDOWN, placeholder="Actualisez les données pour charger les projets administrables", className="access-dropdown", labels=DROPDOWN_LABELS),
            html.P("Seuls les projets administrés par l’utilisateur connecté sont proposés, sauf administrateur d’instance.", className="step-help"),
        ], className="step"),
        html.Div([
            html.Label([html.Span("02", className="step-number"), html.Span("Utilisateur bénéficiaire")], className="step-label", htmlFor=ids.TARGET_USER_DROPDOWN),
            dcc.Dropdown(id=ids.TARGET_USER_DROPDOWN, placeholder="Actualisez les données pour charger les utilisateurs actifs", className="access-dropdown", labels=DROPDOWN_LABELS),
            html.P("Le compte doit exister et être actif au moment de la vérification puis de l’attribution.", className="step-help"),
        ], className="step"),
        html.Div([
            html.Label([html.Span("03", className="step-number"), html.Span("Groupe concerné")], className="step-label", htmlFor=ids.GROUP_DROPDOWN),
            dcc.Dropdown(id=ids.GROUP_DROPDOWN, placeholder="Sélectionnez un groupe", className="access-dropdown", labels=DROPDOWN_LABELS, search_order="original"),
            html.P("Les groupes sont classés du moins privilégié au plus privilégié. Le détail des droits est présenté après vérification.", className="step-help"),
        ], className="step"),
        html.Div([
            html.Button("Vérifier les droits", id=ids.PREVIEW_BUTTON, n_clicks=0, className="primary-button"),
        ], className="form-actions"),
        html.Div([
            dcc.Checklist(id=ids.ACK_SCOPE, options=[{"label": "Je confirme avoir pris connaissance des droits associés au groupe et de leur portée sur l’ensemble de l’instance.", "value": "ack"}], value=[]),
        ], className="ack-area"),
        html.Div([
            html.Button("Confirmer l’attribution", id=ids.ADD_BUTTON, n_clicks=0, disabled=True, className="primary-button"),
        ], className="form-actions"),
        html.Details([
            html.Summary("Configuration administrateur"),
            html.Ul([
                html.Li("L’application doit s’exécuter avec un compte disposant des droits nécessaires à la gestion des groupes."),
                html.Li("Les réglages forceAuthentication et backend API access doivent rester configurés dans les paramètres de l’application web."),
                html.Li("La délégation hors administrateur d’instance reste désactivée tant que DELEGABLE_GROUPS_BY_PROJECT est vide."),
                html.Li("Aucune écriture n’est effectuée sans aperçu valide, confirmation explicite et action sur le bouton d’attribution."),
            ]),
        ], className="admin-config")
    ], className="card selection-card")

def build_access_summary():
    return html.Aside([
        dcc.Loading(html.Div(id=ids.RESULT, children=render_empty_summary()), type="circle"),
    ], className="card summary-card")

