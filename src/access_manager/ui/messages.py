"""Safe French status messages for presentation."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from ..config import SAFE_ERROR_TYPES
LOGGER = logging.getLogger(__name__)

def app_error(operation: str, exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, SAFE_ERROR_TYPES):
        return {"ok": False, "message": f"{operation} impossible : contrôle de sécurité non validé.", "detail": str(exc)}
    LOGGER.exception("Unexpected %s failure (%s)", operation, exc.__class__.__name__)
    return {
        "ok": False,
        "message": f"{operation} impossible : contrôle de sécurité non validé.",
        "detail": f"Erreur interne inattendue ({exc.__class__.__name__}) ; consultez les journaux serveur.",
    }


def ok_message(message: str, **kwargs: Any) -> Dict[str, Any]:
    out = {"ok": True, "message": message}
    out.update(kwargs)
    return out
