"""Server-owned signed preview tokens, independent of Dash/DSS."""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from ..config import PREVIEW_TTL_SECONDS

def get_secret() -> bytes:
    seed = os.environ.get("DKU_WEBAPP_ACCESS_MANAGER_SECRET")
    if not seed:
        seed = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
        os.environ["DKU_WEBAPP_ACCESS_MANAGER_SECRET"] = seed
    return seed.encode("utf-8")


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


class PreviewSigner:
    def __init__(self, secret=None, ttl=PREVIEW_TTL_SECONDS):
        self.secret = secret if secret is not None else get_secret()
        self.ttl = ttl

    def sign(self, payload: Dict[str, Any]) -> str:
        blob = canonical_json(payload).encode("utf-8")
        sig = hmac.new(self.secret, blob, hashlib.sha256).hexdigest()
        token_payload = base64.urlsafe_b64encode(blob).decode("ascii")
        return f"{token_payload}.{sig}"

    def verify(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        if not token or "." not in token:
            return False, None, "Aperçu manquant. Lancez d’abord la vérification des accès."
        token_payload, sig = token.rsplit(".", 1)
        try:
            blob = base64.urlsafe_b64decode(token_payload.encode("ascii"))
        except Exception:
            return False, None, "Aperçu invalide."
        expected = hmac.new(self.secret, blob, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False, None, "La signature de l’aperçu ne correspond plus."
        try:
            payload = json.loads(blob.decode("utf-8"))
        except Exception:
            return False, None, "Contenu d’aperçu invalide."
        if int(payload.get("expires_at", 0)) < int(time.time()):
            return False, payload, "L’aperçu a expiré. Relancez la vérification des accès."
        return True, payload, ""
