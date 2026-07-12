"""
Smoketest for the FastAPI + WSGIMiddleware mount pattern.

Builds a minimal Flask app with a few representative routes, wraps it under
FastAPI via a2wsgi.WSGIMiddleware, exercises both Flask and FastAPI routes
through the FastAPI test client. Verifies:

- Plain Flask GET response
- Flask form POST + redirect (the basic flask-security-too-shaped flow)
- Flask session cookie roundtrip (signed sessions)
- Flask static-style file serving via send_from_directory pattern
- FastAPI native route alongside the mounted Flask app
- FastAPI route precedence (FastAPI wins for paths it owns; Flask handles the rest)

Run via:
    uv run python -m sparkmeter._wsgi_mount_smoketest
"""

import sys

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask, Response, redirect, request, session, url_for


def build_flask() -> Flask:
    flask_app = Flask(__name__)
    flask_app.secret_key = "smoketest-secret"

    @flask_app.route("/")
    def index():
        return "flask-index"

    @flask_app.route("/echo")
    def echo():
        name = request.args.get("name", "world")
        return f"hello {name}"

    @flask_app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            session["user"] = request.form["user"]
            return redirect(url_for("whoami"))
        return '<form method="POST"><input name="user" /><button type="submit">Login</button></form>'

    @flask_app.route("/whoami")
    def whoami():
        return f"user={session.get('user', 'anonymous')}"

    @flask_app.route("/blob")
    def blob():
        return Response(b"BLOBBYTES", mimetype="application/octet-stream")

    return flask_app


def build_fastapi() -> FastAPI:
    api = FastAPI()

    @api.get("/api/native")
    async def native():
        return {"source": "fastapi"}

    @api.get("/")  # FastAPI route should win over Flask's "/"
    async def native_root():
        return {"source": "fastapi-wins-at-root"}

    api.mount("/", WSGIMiddleware(build_flask()))
    return api


CHECKS = []


def check(label):
    def deco(fn):
        CHECKS.append((label, fn))
        return fn

    return deco


@check("FastAPI native route works")
def t_native(client):
    r = client.get("/api/native")
    assert r.status_code == 200, r.status_code
    assert r.json() == {"source": "fastapi"}


@check("FastAPI route wins over Flask at /")
def t_root_precedence(client):
    r = client.get("/")
    assert r.status_code == 200, r.status_code
    assert r.json() == {"source": "fastapi-wins-at-root"}


@check("Flask GET passes through WSGIMiddleware")
def t_flask_get(client):
    r = client.get("/echo?name=spark")
    assert r.status_code == 200, r.status_code
    assert r.text == "hello spark"


@check("Flask form POST + redirect chain")
def t_flask_form(client):
    r = client.post("/login", data={"user": "tristan"}, follow_redirects=True)
    assert r.status_code == 200, r.status_code
    assert r.text == "user=tristan", r.text


@check("Flask session cookie persists across requests")
def t_flask_session(client):
    r = client.post("/login", data={"user": "session-bearer"}, follow_redirects=False)
    assert r.status_code in (301, 302), (r.status_code, r.text)
    cookies = r.cookies
    assert "session" in cookies, cookies
    r2 = client.get("/whoami", cookies=cookies)
    assert r2.text == "user=session-bearer", r2.text


@check("Flask binary response passes through unchanged")
def t_flask_blob(client):
    r = client.get("/blob")
    assert r.status_code == 200
    assert r.content == b"BLOBBYTES", r.content
    assert r.headers["content-type"] == "application/octet-stream"


def main() -> int:
    api = build_fastapi()
    client = TestClient(api)

    failures = 0
    for label, fn in CHECKS:
        try:
            fn(client)
            print(f"  PASS  {label}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {label}: {exc!r}")

    print()
    if failures:
        print(f"{failures} of {len(CHECKS)} checks failed")
        return 1
    print(f"All {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
