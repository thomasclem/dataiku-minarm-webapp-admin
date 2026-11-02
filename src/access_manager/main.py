"""Composition root: assemble collaborators on the DSS-supplied Dash app."""
from .config import DELEGABLE_GROUPS_BY_PROJECT
from .repositories.dss import DSSRepository
from .services.access import AccessService
from .ui.shell import build_layout
from .ui.styles import apply_styles
from .features.access.callbacks import register_callbacks

def render_dash_webapp(app, *, repository=None, policy=None, signer=None):
    """Initialize the supplied app once, before it starts serving requests.

    DSS uses the default repository and admin-owned policy. Local development
    and tests can inject collaborators without creating a second Dash app.
    """
    repository = DSSRepository() if repository is None else repository
    policy = DELEGABLE_GROUPS_BY_PROJECT if policy is None else policy
    service = AccessService(repository, policy=policy, signer=signer)
    apply_styles(app)
    app.layout = build_layout
    register_callbacks(app, service)
    return service
