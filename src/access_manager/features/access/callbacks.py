"""Dash request adapters for Reader provisioning and multi-project access."""
from dash import html, Input, Output, State, no_update
from flask import request
from . import ids
from ...services.onboarding import ReaderOnboarding
from ...ui.components import render_alert, render_empty_summary, render_reader_plan, render_reader_preview
from ...ui.messages import app_error, ok_message


def register_callbacks(app, service):
    workflow = ReaderOnboarding(service)

    def actor():
        return service.authenticate(dict(request.headers))

    @app.callback(
        [Output(ids.OPERATOR, 'children'), Output(ids.TARGET_USER_DROPDOWN, 'options'),
         Output(ids.TARGET_USER_DROPDOWN, 'value'), Output(ids.PROJECT_DROPDOWN, 'options'),
         Output(ids.CREATION_AVAILABLE, 'data'), Output(ids.CREATE_STATUS, 'children')],
        Input(ids.LOAD_BUTTON, 'n_clicks'), prevent_initial_call=True,
    )
    def load_projects_and_users(n_clicks):
        try:
            current = actor()
            _, projects = workflow.context(current)
            readers = workflow.list_readers()
            try:
                available, message = workflow.creation_status(current)
            except Exception:
                available, message = False, 'La capacité de création Reader n’a pas pu être vérifiée.'
            return (html.Div([html.Span('Utilisateur connecté : '), html.Strong(current['login'])]),
                    readers, None, projects, available, html.P(message, className='step-help'))
        except Exception as exc:
            return None, [], None, [], False, render_alert(app_error('Chargement', exc))

    @app.callback(
        [Output(ids.NEW_USER_FORM, 'disabled'), Output(ids.CREATE_BUTTON, 'disabled')],
        [Input(ids.CREATION_AVAILABLE, 'data'), Input(ids.NEW_LOGIN, 'value'),
         Input(ids.NEW_NAME, 'value'), Input(ids.NEW_EMAIL, 'value'), Input(ids.NEW_PASSWORD, 'value')],
    )
    def enable_creation(available, login, name, email, password):
        password_ok = bool(password) if workflow.source_type == 'LOCAL' else True
        return not bool(available), not (available and login and name and email and password_ok)

    @app.callback(
        [Output(ids.TARGET_USER_DROPDOWN, 'options', allow_duplicate=True),
         Output(ids.TARGET_USER_DROPDOWN, 'value', allow_duplicate=True),
         Output(ids.CREATE_STATUS, 'children', allow_duplicate=True), Output(ids.NEW_PASSWORD, 'value')],
        Input(ids.CREATE_BUTTON, 'n_clicks'),
        [State(ids.NEW_LOGIN, 'value'), State(ids.NEW_NAME, 'value'), State(ids.NEW_EMAIL, 'value'), State(ids.NEW_PASSWORD, 'value')],
        prevent_initial_call=True,
    )
    def create_reader(n_clicks, login, name, email, password):
        try:
            created = workflow.create_reader(actor(), login, name, email, password)
            return workflow.list_readers(), created, render_alert(ok_message('Le compte Reader a été créé sans groupe. Sélectionnez les projets à partager.')), ''
        except Exception as exc:
            return no_update, no_update, render_alert(app_error('Création du compte Reader', exc)), ''

    @app.callback(
        Output(ids.PROJECT_DROPDOWN, 'value'), Input(ids.TARGET_USER_DROPDOWN, 'value'),
        prevent_initial_call=True,
    )
    def reset_projects_on_user_change(target):
        return []

    @app.callback(
        [Output(ids.PROJECT_DROPDOWN, 'disabled'), Output(ids.PROJECT_DROPDOWN, 'placeholder'), Output(ids.PROJECT_SECTION, 'className'),
         Output(ids.GROUP_SECTION, 'className'), Output(ids.PREVIEW_BUTTON, 'disabled'),
         Output(ids.ACK_SECTION, 'disabled'), Output(ids.ACK_SECTION, 'className'), Output(ids.ADD_BUTTON, 'disabled')],
        [Input(ids.TARGET_USER_DROPDOWN, 'value'), Input(ids.PROJECT_DROPDOWN, 'value'),
         Input(ids.PREVIEW_ALLOWED, 'data'), Input(ids.ACK_SCOPE, 'value')],
    )
    def update_progression(target, projects, allowed, ack):
        selected = bool(target and projects)
        reviewed = bool(selected and allowed)
        return (not bool(target), 'Sélectionnez un ou plusieurs projets' if target else 'Sélectionnez d’abord un utilisateur Reader', 'step' if target else 'step is-disabled',
                'step' if selected else 'step is-disabled', not selected,
                not reviewed, 'ack-area' if reviewed else 'ack-area is-disabled',
                not (reviewed and 'ack' in (ack or [])))

    @app.callback(
        [Output(ids.GROUP_PLAN, 'children'), Output(ids.RESULT, 'children'),
         Output(ids.PREVIEW_TOKEN, 'data'), Output(ids.PREVIEW_ALLOWED, 'data'), Output(ids.ACK_SCOPE, 'value')],
        [Input(ids.TARGET_USER_DROPDOWN, 'value'), Input(ids.PROJECT_DROPDOWN, 'value')],
        prevent_initial_call=True,
    )
    def propose_groups(target, projects):
        if not target or not projects:
            return 'Sélectionnez d’abord un compte Reader et les projets à partager.', render_empty_summary(), None, False, []
        try:
            plan = workflow.plan(actor(), projects, target)
            return render_reader_plan(plan), render_empty_summary(), None, False, []
        except Exception as exc:
            return render_alert(app_error('Proposition des groupes', exc)), render_empty_summary(), None, False, []

    @app.callback(
        [Output(ids.RESULT, 'children', allow_duplicate=True), Output(ids.PREVIEW_TOKEN, 'data', allow_duplicate=True),
         Output(ids.PREVIEW_ALLOWED, 'data', allow_duplicate=True), Output(ids.ACK_SCOPE, 'value', allow_duplicate=True)],
        Input(ids.PREVIEW_BUTTON, 'n_clicks'),
        [State(ids.TARGET_USER_DROPDOWN, 'value'), State(ids.PROJECT_DROPDOWN, 'value')],
        prevent_initial_call=True,
    )
    def preview_assignment(n_clicks, target, projects):
        try:
            plan = workflow.preview(actor(), projects, target)
            return render_reader_preview(plan), plan['token'], plan['allowedToSubmit'], []
        except Exception as exc:
            return render_alert(app_error('Vérification', exc)), None, False, []

    @app.callback(
        [Output(ids.RESULT, 'children', allow_duplicate=True), Output(ids.PREVIEW_TOKEN, 'data', allow_duplicate=True),
         Output(ids.PREVIEW_ALLOWED, 'data', allow_duplicate=True), Output(ids.ACK_SCOPE, 'value', allow_duplicate=True)],
        Input(ids.ADD_BUTTON, 'n_clicks'),
        [State(ids.PREVIEW_TOKEN, 'data'), State(ids.ACK_SCOPE, 'value'),
         State(ids.TARGET_USER_DROPDOWN, 'value'), State(ids.PROJECT_DROPDOWN, 'value')],
        prevent_initial_call=True,
    )
    def submit_assignment(n_clicks, token, ack, target, projects):
        try:
            result = workflow.submit(actor(), token, 'ack' in (ack or []), projects, target)
            return html.Div([render_alert(result), render_empty_summary()]), None, False, []
        except Exception as exc:
            return render_alert(app_error('Attribution', exc)), None, False, []
