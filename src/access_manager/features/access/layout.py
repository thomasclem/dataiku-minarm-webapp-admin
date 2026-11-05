"""Progressive Reader onboarding form; data loading belongs to callbacks."""
from dash import dcc, html
from . import ids
from ...config import READER_SOURCE_TYPE
from ...ui.components import render_empty_summary
from ...ui.labels import DROPDOWN_LABELS


def step_label(number, label, control=None):
    return html.Label([html.Span(number, className='step-number'), html.Span(label)],
                      className='step-label', htmlFor=control)


def build_access_form():
    return html.Section([
        html.H2('Paramètres de l’habilitation', className='card-heading'),
        html.P('Créez ou sélectionnez un compte Reader, choisissez les projets, puis vérifiez les groupes proposés.', className='card-copy'),
        html.Div([
            step_label('01', 'Utilisateur bénéficiaire', ids.TARGET_USER_DROPDOWN),
            dcc.Dropdown(id=ids.TARGET_USER_DROPDOWN, options=[], placeholder='Actualisez les données pour charger les comptes Reader', labels=DROPDOWN_LABELS),
            html.Details([
                html.Summary('Créer un utilisateur Reader'),
                html.P('Le compte est créé sans groupe. Les accès sont attribués après vérification des projets.', className='step-help'),
                html.Div(id=ids.CREATE_STATUS, role='status'),
                html.Fieldset([
                    html.Label('Identifiant', htmlFor=ids.NEW_LOGIN),
                    dcc.Input(id=ids.NEW_LOGIN, type='text', maxLength=128, autoComplete='off'),
                    html.Label('Nom complet', htmlFor=ids.NEW_NAME),
                    dcc.Input(id=ids.NEW_NAME, type='text', maxLength=200),
                    html.Label('Adresse électronique', htmlFor=ids.NEW_EMAIL),
                    dcc.Input(id=ids.NEW_EMAIL, type='email', maxLength=254),
                    html.Div([
                        html.Label('Mot de passe initial', htmlFor=ids.NEW_PASSWORD),
                        dcc.Input(id=ids.NEW_PASSWORD, type='password', autoComplete='new-password'),
                    ], style={} if READER_SOURCE_TYPE == 'LOCAL' else {'display': 'none'}),
                    html.P('Profil imposé : Reader, consultation uniquement.', className='step-help'),
                    html.Button('Créer le compte Reader', id=ids.CREATE_BUTTON, n_clicks=0, disabled=True, className='secondary-button'),
                ], id=ids.NEW_USER_FORM, disabled=True, className='reader-fields'),
            ], className='create-user-panel'),
        ], className='step'),
        html.Div([
            step_label('02', 'Projets à partager', ids.PROJECT_DROPDOWN),
            dcc.Dropdown(id=ids.PROJECT_DROPDOWN, options=[], value=[], multi=True, disabled=True,
                         placeholder='Sélectionnez d’abord un utilisateur Reader', labels=DROPDOWN_LABELS),
            html.P('Sélectionnez un ou plusieurs projets que vous administrez.', className='step-help'),
        ], id=ids.PROJECT_SECTION, className='step is-disabled'),
        html.Div([
            step_label('03', 'Groupes du projet et accès proposés'),
            html.Div('Sélectionnez d’abord les projets à partager.', id=ids.GROUP_PLAN, role='status'),
            html.P('Les groupes admissibles sont classés en premier. Vérifiez les droits avant de confirmer l’attribution.', className='step-help'),
            html.Button('Vérifier les droits', id=ids.PREVIEW_BUTTON, n_clicks=0, disabled=True, className='primary-button'),
        ], id=ids.GROUP_SECTION, className='step is-disabled'),
        build_access_summary(),
        html.Fieldset([
            dcc.Checklist(id=ids.ACK_SCOPE, options=[{'label':'Je confirme avoir pris connaissance des groupes proposés et de leur portée sur les autres projets et ressources de l’instance.', 'value':'ack'}], value=[]),
        ], id=ids.ACK_SECTION, disabled=True, className='ack-area is-disabled'),
        html.Div([
            html.Button('Attribuer les accès', id=ids.ADD_BUTTON, n_clicks=0, disabled=True, className='primary-button'),
        ], className='form-actions'),
    ], className='card selection-card')


def build_access_summary():
    return html.Div([dcc.Loading(html.Div(id=ids.RESULT, children=render_empty_summary(), role='status'), type='circle')], className='review-slot')
