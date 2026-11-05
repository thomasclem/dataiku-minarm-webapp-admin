"""Credential-free, immutable history rows for one access attribution operation."""
import json
from datetime import datetime, timezone
from uuid import uuid4

HISTORY_SCHEMA = [
    {'name': 'record_id', 'type': 'string'},
    {'name': 'event_id', 'type': 'string'},
    {'name': 'ts_utc', 'type': 'date'},
    {'name': 'actor_login', 'type': 'string'},
    {'name': 'beneficiary_login', 'type': 'string'},
    {'name': 'project_key', 'type': 'string'},
    {'name': 'group_name', 'type': 'string'},
    {'name': 'outcome', 'type': 'string'},
    {'name': 'user_profile', 'type': 'string'},
    {'name': 'project_permissions_json', 'type': 'string'},
    {'name': 'affected_projects_json', 'type': 'string'},
    {'name': 'source', 'type': 'string'},
]


def history_rows(actor_login, plan, event_id, phase):
    """One row per project/group; no token, browser header, password or user settings."""
    if phase not in {'REQUESTED', 'COMPLETED', 'UNVERIFIED'}:
        raise ValueError('Phase d’historique inconnue.')
    stamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    affected = {group['name']: sorted(item['projectKey'] for item in group['affectedProjects']) for group in plan['groups']}
    rows = []
    for assignment in plan['assignments']:
        outcome = phase
        if phase == 'COMPLETED':
            outcome = 'ALREADY_MEMBER' if assignment['alreadyMember'] else 'GRANTED'
        rows.append({
            'record_id': str(uuid4()), 'event_id': event_id, 'ts_utc': stamp,
            'actor_login': actor_login, 'beneficiary_login': plan['target'],
            'project_key': assignment['project'], 'group_name': assignment['group'],
            'outcome': outcome, 'user_profile': 'READER',
            'project_permissions_json': json.dumps(assignment['grants'], sort_keys=True),
            'affected_projects_json': json.dumps(affected[assignment['group']]),
            'source': 'reader_onboarding',
        })
    return rows
