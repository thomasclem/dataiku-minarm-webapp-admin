"""Readable stylesheet embedded in the DSS-owned Dash template."""
APP_CSS = """
:root {
  --bg: #F6F7F9;
  --surface: #FFFFFF;
  --ink: #1E293B;
  --muted: #566274;
  --primary: #243B5A;
  --primary-dark: #1C2F49;
  --accent: #EEF2F6;
  --amber: #A66200;
  --amber-bg: #FFF7E8;
  --danger: #B42318;
  --danger-bg: #FEF3F2;
  --success: #067647;
  --success-bg: #ECFDF3;
  --border: #D4D9E2;
  --border-strong: #B8C0CC;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.5;
}
button, input, textarea { font: inherit; }
button {
  border: 0;
  border-radius: 4px;
  min-height: 44px;
  padding: 0 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color .12s ease, border-color .12s ease, color .12s ease;
}
button:focus-visible, .Select-control:focus-within, input:focus-visible { outline: 3px solid rgba(36,59,90,.28); outline-offset: 2px; }
button:hover:not(:disabled) { box-shadow: none; }
button:disabled { cursor: not-allowed; opacity: .52; box-shadow: none; }
.app-shell { max-width: 1180px; margin: 0 auto; padding: 1.75rem; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1.25rem; align-items: end; margin-bottom: 1.25rem; padding-top: 1rem; border-top: 3px solid var(--primary); }
.eyebrow { color: var(--primary); font-weight: 700; letter-spacing: .11em; text-transform: uppercase; font-size: .76rem; margin-bottom: .4rem; }
h1 { font-size: clamp(1.9rem, 3.4vw, 2.1rem); line-height: 1.2; letter-spacing: 0; font-weight: 680; margin: 0; }
.subtitle { color: var(--muted); font-size: 1rem; margin: .45rem 0 0; }
.hero-actions { display: flex; align-items: center; justify-content: flex-end; gap: .65rem; flex-wrap: wrap; }
.operator-pill { display: inline-flex; align-items: center; gap: .45rem; min-height: 40px; padding: .4rem .65rem; border: 1px solid var(--border); border-radius: 4px; background: #FFFFFF; color: var(--ink); box-shadow: none; font-size: .93rem; }
.operator-pill:empty { display: none; }
.operator-dot { display: none; }
.primary-button { background: var(--primary); color: white; border: 1px solid var(--primary); }
.primary-button:hover:not(:disabled) { background: var(--primary-dark); border-color: var(--primary-dark); }
.secondary-button { background: white; color: var(--primary); border: 1px solid var(--border-strong); }
.secondary-button:hover:not(:disabled) { background: #F8FAFC; border-color: var(--primary); }
.workspace { display: grid; grid-template-columns: minmax(0, 1.12fr) minmax(330px, .88fr); gap: 1.1rem; align-items: start; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; box-shadow: none; }
.selection-card { padding: 1.2rem; }
.summary-card { padding: 1.1rem; position: sticky; top: 1rem; }
.card-heading { margin: 0 0 .35rem; font-size: 1.2rem; line-height: 1.3; font-weight: 680; }
.card-copy { margin: 0 0 1rem; color: var(--muted); }
.step { border-top: 1px solid var(--border); padding: 1rem 0; }
.step:first-of-type { border-top: 0; }
.step-label { display: flex; align-items: baseline; gap: .65rem; margin-bottom: .45rem; font-weight: 650; }
.step-number { color: var(--primary); font-size: .78rem; letter-spacing: .08em; font-weight: 700; }
.step-help { margin: .35rem 0 0; color: var(--muted); font-size: .92rem; }
.Select-control { border-color: var(--border-strong) !important; border-radius: 4px !important; min-height: 44px !important; box-shadow: none !important; }
.Select-placeholder, .Select--single > .Select-control .Select-value { line-height: 44px !important; }
.Select-menu-outer { border-radius: 4px !important; border-color: var(--border-strong) !important; box-shadow: 0 6px 14px rgba(30,41,59,.10) !important; }
.Select-option { white-space: normal !important; line-height: 1.35 !important; padding: .65rem .8rem !important; }
/* Dash 4 uses Radix popovers rather than the legacy .Select-* menu. */
.dash-dropdown, .dash-dropdown-content {
  --Dash-Fill-Interactive-Strong: #243B5A;
  --Dash-Fill-Interactive-Weak: #EEF2F6;
  --Dash-Text-Strong: #1E293B;
  --Dash-Text-Weak: #566274;
  --Dash-Text-Disabled: #657389;
  --Dash-Stroke-Strong: #B8C0CC;
  --Dash-Fill-Inverse-Strong: #FFFFFF;
  color: var(--ink);
  border-radius: 4px;
}
.dash-dropdown-content {
  width: var(--radix-popover-trigger-width) !important;
  min-width: 0 !important;
  max-width: calc(100vw - 2rem) !important;
  overflow-x: hidden;
  box-shadow: 0 6px 14px rgba(30,41,59,.10);
}
.dash-dropdown-option { white-space: normal; overflow-wrap: anywhere; line-height: 1.4; }
.dash-dropdown-trigger { min-height: 44px; }
.dash-dropdown-grid-container { min-width: 0; }
.selection-card, .summary-card { min-width: 0; }
.form-actions { border-top: 1px solid var(--border); margin-top: .65rem; padding-top: .9rem; display: flex; gap: .65rem; flex-wrap: wrap; align-items: center; }
.ack-area { margin-top: .9rem; padding: .8rem .9rem; border-radius: 4px; background: #FFFFFF; border: 1px solid var(--border); color: var(--ink); }
.ack-area label { display: flex; gap: .55rem; align-items: flex-start; }
.alert { border-radius: 4px; padding: .8rem .9rem; margin-bottom: .9rem; border: 1px solid; }
.alert-success { background: var(--success-bg); border-color: rgba(6,118,71,.30); color: #064E3B; }
.alert-error { background: var(--danger-bg); border-color: rgba(180,35,24,.32); color: #7A271A; }
.empty-state { min-height: 250px; display: grid; place-items: center; text-align: center; padding: 1.3rem; color: var(--muted); background: #FFFFFF; border: 1px dashed var(--border-strong); border-radius: 6px; }
.empty-state strong { display: block; color: var(--ink); font-size: 1.05rem; margin-bottom: .35rem; }
.summary-grid { display: grid; gap: .65rem; margin: .9rem 0; }
.summary-row { padding: .7rem; border-radius: 4px; background: #F8FAFC; border: 1px solid var(--border); }
.summary-label { color: var(--muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; margin-bottom: .15rem; }
.summary-value { font-weight: 650; word-break: break-word; }
.badge-list { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .5rem; }
.badge { display: inline-flex; align-items: center; border-radius: 3px; padding: .25rem .45rem; background: var(--accent); color: var(--ink); border: 1px solid var(--border); font-size: .82rem; font-weight: 600; }
.state-allowed { color: var(--success); font-weight: 700; }
.state-blocked { color: var(--danger); font-weight: 700; }
.project-list { margin: .55rem 0 0; padding-left: 1.1rem; color: var(--ink); }
.scope-warning { margin-top: .9rem; padding: .8rem; border-radius: 4px; background: var(--amber-bg); border: 1px solid rgba(166,98,0,.34); color: #694100; }
details.admin-config { margin-top: .95rem; color: var(--muted); }
details.admin-config summary { cursor: pointer; font-weight: 650; color: var(--ink); }
@media (max-width: 900px) {
  .app-shell { padding: 1rem; }
  .hero { grid-template-columns: 1fr; align-items: start; }
  .hero-actions { justify-content: flex-start; }
  .workspace { grid-template-columns: 1fr; }
  .summary-card { position: static; }
}
"""


INDEX_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="fr">
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>{APP_CSS}</style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""


def apply_styles(app):
    app.title = "Gestion des habilitations"
    app.index_string = INDEX_TEMPLATE
