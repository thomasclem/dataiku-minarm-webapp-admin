"""Structured, credential-free audit records."""
import json
import logging
from datetime import datetime, timezone
LOGGER = logging.getLogger(__name__)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def structured_audit(actor: str, target: str, project: str, group: str, outcome: str, detail: str = "") -> None:
    record = {
        "ts_utc": utc_now(),
        "actor": actor or "<unknown>",
        "target": target or "<none>",
        "project": project or "<none>",
        "group": group or "<none>",
        "outcome": outcome,
        "detail": (detail or "")[:500],
    }
    LOGGER.info("WEBAPP_ACCESS_MANAGER_AUDIT %s", json.dumps(record, sort_keys=True))
