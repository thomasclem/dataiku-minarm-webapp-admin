"""Run the UI against local demonstration data. No DSS credentials are needed."""
import argparse

from dash import Dash

from access_manager.main import render_dash_webapp
from devtools.demo_repository import DemoRepository


def create_demo_app():
    app = Dash(__name__)
    render_dash_webapp(app, repository=DemoRepository())
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print("Local demo: all users, groups and membership changes are in memory.")
    create_demo_app().run(host="127.0.0.1", port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
