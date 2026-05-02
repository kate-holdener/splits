"""
Gmail OAuth sign-in flow for the Splits desktop app.

Uses the Authorization Code + PKCE flow with a local HTTP callback server.
Tokens are stored in the user data directory.

Required environment variables:
    GMAIL_CLIENT_ID: Google OAuth client ID
    GMAIL_CLIENT_SECRET: Google OAuth client secret
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

TOKENS_FILENAME = "gmail_tokens.json"
CALLBACK_PORT = 9741

_auth_state: dict = {
    "server": None,
    "code": None,
    "error": None,
    "state": None,
    "code_verifier": None,
}


def _tokens_path() -> Path:
    from persistence.user_data_dir import get_user_data_dir
    return get_user_data_dir() / TOKENS_FILENAME


def _get_client_credentials() -> tuple[str, str]:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    missing = [n for n, v in [("GMAIL_CLIENT_ID", client_id), ("GMAIL_CLIENT_SECRET", client_secret)] if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return client_id, client_secret


def get_auth_status() -> dict:
    """Return {signed_in, email} based on stored tokens."""
    path = _tokens_path()
    if not path.exists():
        return {"signed_in": False, "email": None}
    try:
        data = json.loads(path.read_text())
        return {"signed_in": True, "email": data.get("email")}
    except Exception:
        return {"signed_in": False, "email": None}


def start_sign_in() -> dict:
    """
    Begin the OAuth flow: open the browser to Google's consent screen and
    start a local HTTP server to receive the authorization code callback.
    Returns {ok, msg} — errors surface if credentials are missing.
    """
    try:
        client_id, _ = _get_client_credentials()
    except ValueError as e:
        return {"ok": False, "msg": str(e)}

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_hex(16)

    _auth_state["code"] = None
    _auth_state["error"] = None
    _auth_state["state"] = state
    _auth_state["code_verifier"] = code_verifier

    try:
        _start_callback_server()
    except OSError as e:
        return {"ok": False, "msg": f"Could not start local callback server: {e}"}

    params = {
        "client_id": client_id,
        "redirect_uri": f"http://localhost:{CALLBACK_PORT}/callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.send openid email",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    webbrowser.open(auth_url)
    return {"ok": True}


def poll_sign_in() -> dict:
    """
    Check whether the authorization code has arrived.
    Returns:
        {ok: True, done: False}  — still waiting
        {ok: True, done: True, email: str}  — success, tokens saved
        {ok: False, msg: str}   — error
    """
    if _auth_state["error"]:
        _stop_callback_server()
        return {"ok": False, "msg": f"Google sign-in failed: {_auth_state['error']}"}

    if not _auth_state["code"]:
        return {"ok": True, "done": False}

    try:
        client_id, client_secret = _get_client_credentials()
    except ValueError as e:
        return {"ok": False, "msg": str(e)}

    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": _auth_state["code"],
                "code_verifier": _auth_state["code_verifier"],
                "grant_type": "authorization_code",
                "redirect_uri": f"http://localhost:{CALLBACK_PORT}/callback",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as e:
        return {"ok": False, "msg": f"Token exchange failed: {e}"}

    token_data = resp.json()

    email = None
    id_token = token_data.get("id_token")
    if id_token:
        try:
            parts = id_token.split(".")
            if len(parts) >= 2:
                padding = "=" * (-len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding).decode())
                email = payload.get("email")
        except Exception:
            pass

    tokens = {
        "refresh_token": token_data.get("refresh_token"),
        "email": email,
    }
    _tokens_path().write_text(json.dumps(tokens, indent=2))

    _auth_state["code"] = None
    _stop_callback_server()

    return {"ok": True, "done": True, "email": email}


def cancel_sign_in() -> dict:
    """Abort an in-progress sign-in flow."""
    _auth_state["code"] = None
    _auth_state["error"] = None
    _stop_callback_server()
    return {"ok": True}


def sign_out() -> dict:
    """Remove stored tokens."""
    path = _tokens_path()
    if path.exists():
        path.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Local HTTP callback server
# ---------------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if "code" in params:
                _auth_state["code"] = params["code"][0]
                body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Signed in! You can close this tab and return to Splits.</h2></body></html>"
            else:
                _auth_state["error"] = (params.get("error") or ["unknown"])[0]
                body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Sign-in failed. You can close this tab.</h2></body></html>"
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def _start_callback_server() -> None:
    if _auth_state.get("server"):
        return
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _auth_state["server"] = server


def _stop_callback_server() -> None:
    server = _auth_state.get("server")
    if server:
        threading.Thread(target=server.shutdown, daemon=True).start()
        _auth_state["server"] = None
