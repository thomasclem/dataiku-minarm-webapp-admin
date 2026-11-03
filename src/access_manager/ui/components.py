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
        labels = ["Aucun droit supplémentaire détecté"]
    return html.Div([html.Span(label, className="badge") for label in labels], className="badge-list")


def render_empty_summary() -> html.Div:
    return html.Div([
        html.H2("Récapitulatif de l’habilitation", className="card-heading"),
        html.Div([
            html.Div([
                html.Strong("Aucune attribution préparée"),
                html.Div("Renseignez les paramètres, puis sélectionnez « Vérifier les droits » pour consulter le récapitulatif."),
            ])
        ], className="empty-state"),
    ])


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


def render_reader_plan(plan):
    rows = [html.Tr([
        html.Td(a['project']), html.Td(a['group']),
        html.Td(', '.join(permission_labels(a['grants']))),
        html.Td('Déjà membre' if a['alreadyMember'] else 'À ajouter'),
    ]) for a in plan['assignments']]
    return html.Div([
        html.Div([
            html.Table([
                html.Thead(html.Tr([html.Th(v, scope='col') for v in ['Projet', 'Groupe proposé', 'Droits', 'Appartenance']])),
                html.Tbody(rows),
            ], className='access-plan-table'),
        ], className='table-scroll') if rows else html.P('Aucun groupe admissible.'),
        html.Ul([html.Li(reason) for reason in plan['blockedReasons']], className='project-list') if plan['blockedReasons'] else None,
    ])


def render_reader_preview(plan):
    affected = sorted({a['projectKey'] for group in plan['groups'] for a in group['affectedProjects']})
    outside = sorted(set(affected) - set(plan['projects']))
    return html.Div([
        html.H2('Récapitulatif de l’habilitation', className='card-heading'),
        html.Div('Attribution possible après confirmation' if plan['allowedToSubmit'] else 'Attribution bloquée',
                 className='state-allowed' if plan['allowedToSubmit'] else 'state-blocked'),
        html.Div([
            html.Div('Utilisateur bénéficiaire · Reader', className='summary-label'),
            html.Div(plan['target'], className='summary-value'),
        ], className='summary-row'),
        render_reader_plan(plan),
        html.Div([
            html.Strong('Portée des groupes proposés'),
            html.P('Autres projets concernés : ' + (', '.join(outside) if outside else 'aucun détecté.')),
            html.P('Les groupes peuvent aussi être utilisés sur d’autres ressources de l’instance. Ce contrôle porte sur les droits globaux et les listes d’accès des projets ; il ne constitue pas un inventaire de toutes les autorisations de ressources.'),
        ], className='scope-warning'),
        html.P('Proposition automatique par projet : consultation des tableaux de bord avant lecture du contenu, puis portée et nombre de droits minimaux. Les groupes identiques sont ajoutés une seule fois.', className='step-help'),
    ])
