"""Dash request adapters; domain decisions are delegated to AccessService."""
from dash import html, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from flask import request
from . import ids
from ...config import SAFE_ERROR_TYPES
from ...services.audit import structured_audit
from ...ui.labels import group_option_label
from ...ui.components import render_alert, render_empty_summary, render_preview
from ...ui.messages import app_error, ok_message

def register_callbacks(app, service):
    @app.callback(
        [Output(ids.OPERATOR, "children"), Output(ids.PROJECT_DROPDOWN, "options"), Output(ids.TARGET_USER_DROPDOWN, "options"), Output(ids.RESULT, "children", allow_duplicate=True)],
        Input(ids.LOAD_BUTTON, "n_clicks"),
        prevent_initial_call=True,
    )
    def load_projects_and_users(n_clicks):
        try:
            actor = service.authenticate(dict(request.headers))
            group_defs = service.list_group_defs()
            projects = service.project_dropdown_options_for_actor(actor, group_defs)
            users = service.list_enabled_users()
            operator = html.Div([html.Span("Utilisateur connecté : "), html.Strong(actor["login"])])
            status = render_alert(ok_message(f"{len(projects)} projet(s) administrable(s) et {len(users)} utilisateur(s) actif(s) chargés."))
            return operator, projects, users, html.Div([status, render_empty_summary()])
        except Exception as exc:
            return None, [], [], html.Div([render_alert(app_error("Chargement", exc)), render_empty_summary()])


    @app.callback(
        [Output(ids.PREVIEW_TOKEN, "data", allow_duplicate=True), Output(ids.PREVIEW_ALLOWED, "data", allow_duplicate=True), Output(ids.ACK_SCOPE, "value", allow_duplicate=True)],
        [Input(ids.PROJECT_DROPDOWN, "value"), Input(ids.TARGET_USER_DROPDOWN, "value"), Input(ids.GROUP_DROPDOWN, "value")],
        prevent_initial_call=True,
    )
    def clear_preview_on_selection_change(project_key, target_user, group_name_):
        return None, False, []


    @app.callback(
        Output(ids.ADD_BUTTON, "disabled"),
        [Input(ids.PREVIEW_ALLOWED, "data"), Input(ids.ACK_SCOPE, "value")],
    )
    def set_add_enabled(preview_allowed, ack_values):
        return not (bool(preview_allowed) and "ack" in (ack_values or []))


    @app.callback(
        [Output(ids.GROUP_DROPDOWN, "options"), Output(ids.GROUP_DROPDOWN, "value"), Output(ids.RESULT, "children", allow_duplicate=True)],
        Input(ids.PROJECT_DROPDOWN, "value"),
        prevent_initial_call=True,
    )
    def load_groups_for_project(project_key):
        if not project_key:
            raise PreventUpdate
        try:
            actor = service.authenticate(dict(request.headers))
            ranked = service.ranked_groups(actor, project_key)
            options = []
            for _, g, affected in sorted(ranked, key=lambda item: item[0]):
                label = group_option_label(g, affected)
                options.append({"label": label, "value": g["name"], "disabled": bool(g["isAdmin"])})
            status = render_alert(ok_message(f"{len(options)} groupe(s) de la liste d’accès chargés. L’ordre est une estimation prudente du moindre privilège, pas une garantie exhaustive."))
            return options, None, html.Div([status, render_empty_summary()])
        except Exception as exc:
            return [], None, html.Div([render_alert(app_error("Chargement des groupes", exc)), render_empty_summary()])


    @app.callback(
        [Output(ids.RESULT, "children", allow_duplicate=True), Output(ids.PREVIEW_TOKEN, "data", allow_duplicate=True), Output(ids.PREVIEW_ALLOWED, "data", allow_duplicate=True)],
        Input(ids.PREVIEW_BUTTON, "n_clicks"),
        [State(ids.PROJECT_DROPDOWN, "value"), State(ids.TARGET_USER_DROPDOWN, "value"), State(ids.GROUP_DROPDOWN, "value")],
        prevent_initial_call=True,
    )
    def preview_assignment(n_clicks, project_key, target_user, group_name_):
        if not project_key or not target_user or not group_name_:
            alert = render_alert({"ok": False, "message": "Vérification impossible : contrôle de sécurité non validé.", "detail": "Choisissez un projet, un utilisateur et un groupe."})
            return html.Div([alert, render_empty_summary()]), None, False
        actor_login = "<unknown>"
        try:
            actor = service.authenticate(dict(request.headers))
            actor_login = actor["login"]
            preview = service.compute_preview(actor, project_key, target_user, group_name_)
            structured_audit(actor_login, target_user, project_key, group_name_, "PREVIEW_OK" if preview["allowedToSubmit"] else "PREVIEW_BLOCKED")
            alert = render_alert(ok_message("Vérification terminée. Relisez le résumé avant de confirmer."))
            return html.Div([alert, render_preview(preview)]), preview["token"], preview["allowedToSubmit"]
        except Exception as exc:
            detail = str(exc) if isinstance(exc, SAFE_ERROR_TYPES) else exc.__class__.__name__
            structured_audit(actor_login, target_user, project_key, group_name_, "PREVIEW_FAILED", detail)
            return html.Div([render_alert(app_error("Vérification", exc)), render_empty_summary()]), None, False


    @app.callback(
        [Output(ids.RESULT, "children", allow_duplicate=True), Output(ids.PREVIEW_TOKEN, "data", allow_duplicate=True), Output(ids.PREVIEW_ALLOWED, "data", allow_duplicate=True), Output(ids.ACK_SCOPE, "value", allow_duplicate=True)],
        Input(ids.ADD_BUTTON, "n_clicks"),
        [State(ids.PREVIEW_TOKEN, "data"), State(ids.ACK_SCOPE, "value"), State(ids.PROJECT_DROPDOWN, "value"), State(ids.TARGET_USER_DROPDOWN, "value"), State(ids.GROUP_DROPDOWN, "value")],
        prevent_initial_call=True,
    )
    def submit_assignment(n_clicks, preview_token, ack_values, project_key, target_user, group_name_):
        actor_login = "<unknown>"
        try:
            actor = service.authenticate(dict(request.headers))
            actor_login = actor["login"]
            result = service.add_group_to_user(actor, preview_token, "ack" in (ack_values or []), project_key, target_user, group_name_)
            return html.Div([render_alert(result), render_empty_summary()]), None, False, []
        except Exception as exc:
            detail = str(exc) if isinstance(exc, SAFE_ERROR_TYPES) else exc.__class__.__name__
            structured_audit(actor_login, target_user or "<from-current-selection>", project_key or "<from-current-selection>", group_name_ or "<from-current-selection>", "SUBMIT_FAILED", detail)
            return render_alert(app_error("Ajout", exc)), no_update, no_update, no_update
