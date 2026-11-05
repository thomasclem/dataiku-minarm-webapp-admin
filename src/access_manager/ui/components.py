"""Pure presentation components with no application data access."""
from dash import html
from typing import Any, Dict, List, Optional, Tuple
from .labels import permission_labels

def render_alert(result: Optional[Dict[str, Any]]) -> html.Div:
    if not result:
        return html.Div()
    cls = "alert alert-success" if result.get("ok", True) else "alert alert-error"
    return html.Div([
        html.Strong("État : "), html.Span(result.get("message", "")),
        html.Div(result.get("detail", ""), style={"marginTop": "0.35rem"}) if result.get("detail") else html.Div(),
    ], className=cls)


def render_permission_badges(names) -> html.Div:
    labels = permission_labels(names)
    if not labels:
        labels = ["No additional permissions"]
    return html.Div([html.Span(label, className="badge") for label in labels], className="badge-list")


def render_empty_summary():
    # Keep the verification area absent until there is a result to review.
    return None



def render_preview(preview: Dict[str, Any]) -> html.Div:
    group = preview["group"]
    affected = preview.get("affectedProjects", [])
    blocked = preview.get("blockedReasons") or ["Aucun point bloquant détecté pour l’utilisateur connecté et la politique actuels."]
    allowed = preview.get("allowedToSubmit")
    state_text = "Attribution possible après confirmation" if allowed else "Attribution non autorisée"
    state_class = "state-allowed" if allowed else "state-blocked"
    return html.Div([
        html.H2("Récapitulatif de l’habilitation", className="card-heading"),
        html.Div(state_text, className=state_class),
        html.Div([
            html.Div([html.Div("Projet", className="summary-label"), html.Div(preview["project"], className="summary-value")], className="summary-row"),
            html.Div([html.Div("Utilisateur bénéficiaire", className="summary-label"), html.Div(preview["target"], className="summary-value")], className="summary-row"),
            html.Div([html.Div("Groupe concerné", className="summary-label"), html.Div(group["name"], className="summary-value")], className="summary-row"),
        ], className="summary-grid"),
        html.Div([html.Strong("Droits accordés sur le projet"), render_permission_badges(group.get("grants", {}).keys())]),
        html.Div([html.Strong("Droits à l’échelle de l’instance"), render_permission_badges(group.get("globalCapabilities"))], style={"marginTop": "0.9rem"}),
        html.Div([
            html.Strong("Projets concernés : "),
            html.Span(f"{len(affected)} au total, dont {group.get('otherAffectedProjectCount', 0)} autre(s) projet(s)."),
            html.Ul([html.Li(f"{p['projectKey']}, {', '.join(permission_labels(p.get('grants', {}).keys()))}") for p in affected] or [html.Li("Aucun projet concerné détecté.")], className="project-list"),
        ], style={"marginTop": "1rem"}),
        html.Div([
            html.Strong("Points de vigilance"),
            html.Ul([html.Li(reason) for reason in blocked], className="project-list"),
        ], className="scope-warning"),
        html.P("L’ajout à un groupe peut accorder des droits sur d’autres projets et ressources de l’instance.", className="card-copy", style={"marginTop": "1rem"}),
    ])


def render_detected_groups(groups):
    """Readable group cards; rights remain visible as individual labels."""
    cards = []
    for group in groups:
        state = 'Proposé' if group.get('recommended') else ('Admissible' if group['eligible'] else 'Non attribuable')
        cards.append(html.Article([
            html.Div([
                html.Div([
                    html.Div(group['project'], className='group-project'),
                    html.H3(group['name'], className='group-name'),
                ]),
                html.Span(state, className='status-label status-allowed' if group['eligible'] else 'status-label status-blocked'),
            ], className='group-card-header'),
            html.Div([
                html.Div('Droits sur le projet', className='rights-caption'),
                render_permission_badges(group['grants']),
            ], className='rights-section'),
            html.Div([
                html.Div('Droits globaux', className='rights-caption'),
                render_permission_badges(group['globalCapabilities']),
            ], className='rights-section') if group['globalCapabilities'] else None,
            html.Div([
                html.Div('Droits inactifs sur cette instance', className='rights-caption'),
                render_permission_badges(group['inactiveGlobalCapabilities']),
                html.P('User Isolation Framework désactivé : ce droit conservé dans la configuration n’est pas pris en compte pour l’attribution.', className='step-help'),
            ], className='rights-section') if group.get('inactiveGlobalCapabilities') else None,
            html.Div([
                html.Strong('Informations à valider', className='reasons-caption'),
                html.Ul([html.Li(warning) for warning in group['warnings']], className='project-list'),
            ], className='group-reasons') if group.get('warnings') else None,
            html.Details([
                html.Summary('Droits sur les autres projets concernés'),
                html.Div([
                    html.Div([html.Strong(item['projectKey']), render_permission_badges(item['grants'])], className='rights-section')
                    for item in group.get('affectedProjects', []) if item['projectKey'] != group['project']
                ], className='group-scope-details'),
            ], className='group-scope') if any(item['projectKey'] != group['project'] for item in group.get('affectedProjects', [])) else None,
            html.Div([
                html.Strong('Motifs de non-attribution', className='reasons-caption'),
                html.Ul([html.Li(reason) for reason in group['reasons']], className='project-list'),
            ], className='group-reasons') if group['reasons'] else None,
            html.P('L’utilisateur appartient déjà à ce groupe.', className='membership-note') if group.get('alreadyMember') else None,
        ], className='group-card'))
    return html.Div(cards, className='group-card-list')


def render_reader_plan(plan):
    groups = plan.get('detectedGroups') or [
        dict(name=a['group'], project=a['project'], grants=a['grants'],
             globalCapabilities=[], eligible=True, recommended=True, reasons=[], alreadyMember=a['alreadyMember'])
        for a in plan['assignments']
    ]
    notice = None
    if plan['blockedReasons']:
        notice = html.Div([
            html.Strong('Aucune attribution possible pour la sélection actuelle.'),
            html.P('Consultez les motifs indiqués pour chaque groupe ci-dessous.'),
            html.Ul([html.Li(reason) for reason in plan['blockedReasons']], className='project-list') if not groups else None,
        ], className='plan-notice')
    return html.Div([
        html.P('Les droits affichés sont ceux des groupes. Leur utilisation dépend également du profil Reader. Consultez leur portée, puis validez explicitement l’attribution.', className='step-help'),
        notice,
        render_detected_groups(groups) if groups else html.P('Aucun groupe détecté dans les projets sélectionnés.', className='step-help'),
    ], className='reader-plan')


def render_reader_preview(plan):
    """Inline verification only; the rights and group cards stay in step 03."""
    affected = sorted({a['projectKey'] for group in plan['groups'] for a in group['affectedProjects']})
    outside = sorted(set(affected) - set(plan['projects']))
    allowed = plan['allowedToSubmit']
    return html.Section([
        html.H3('Vérification des droits', className='verification-heading'),
        html.P('Attribution possible après confirmation' if allowed else 'Attribution bloquée',
               className='state-allowed' if allowed else 'state-blocked'),
        html.P([
            html.Strong(plan['target']),
            f" · Reader · {len(plan['projects'])} projet(s) sélectionné(s)",
            html.Br(),
            'Groupes à attribuer : ' + (', '.join(group['name'] for group in plan['groups']) or 'aucun'),
        ], className='verification-context'),
        html.P('Les motifs de blocage figurent dans les groupes ci-dessus.', className='step-help') if not allowed else html.Div([
            html.P('Autres projets concernés : ' + (', '.join(outside) if outside else 'aucun détecté.')),
            html.P('Les groupes peuvent aussi donner accès à d’autres ressources de l’instance. Confirmez cette portée avant d’attribuer les accès.', className='step-help'),
        ], className='verification-scope'),
    ], className='verification-panel')
