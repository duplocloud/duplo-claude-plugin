"""Shared helpers for DuploCloud CLI tools.

Imported by duplo_activate.py, duplo_ticket.py, and duplo_mirror.py.
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

if sys.version_info < (3, 10):
    sys.exit("Error: Python 3.10+ is required.")

AUTH_FILE = pathlib.Path.home() / ".duplocloud" / ".auth"
_ACTIVE_SESSION_FILE = pathlib.Path.home() / ".duplocloud" / ".active_session"


def _state_file() -> pathlib.Path:
    """Return the per-session state file.

    The UserPromptSubmit hook writes the session ID to ~/.duplocloud/.active_session
    before any CLI call in a turn, so this always resolves to the correct session.
    """
    try:
        session_id = _ACTIVE_SESSION_FILE.read_text().strip()
        if session_id:
            return pathlib.Path.home() / ".duplocloud" / "sessions" / session_id / "state.json"
    except OSError:
        pass
    return pathlib.Path.home() / ".duplocloud" / "state.json"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def load_auth() -> dict | None:
    if not AUTH_FILE.exists():
        return None
    try:
        with open(AUTH_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def require_auth() -> dict:
    auth = load_auth()
    if not auth or not auth.get("base_url") or not auth.get("token"):
        print("No valid credentials found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)
    return auth


def write_auth(base_url: str, token: str):
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump({"base_url": base_url, "token": token}, f, indent=2)
    AUTH_FILE.chmod(0o600)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_state() -> dict:
    sf = _state_file()
    if not sf.exists():
        return {}
    try:
        with open(sf) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict):
    """Replace the entire state file with the given dict."""
    sf = _state_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    with open(sf, "w") as f:
        json.dump(state, f, indent=2)


def update_state(updates: dict):
    """Merge updates into the existing state file."""
    state = load_state()
    state.update(updates)
    save_state(state)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(base_url: str, token: str, path: str):
    """GET <base_url><path> with Bearer auth. Returns (status_code, body_bytes)."""
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _post(base_url: str, token: str, path: str, payload: dict):
    """POST JSON to <base_url><path> with Bearer auth. Returns (status_code, body_bytes)."""
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _put(base_url: str, token: str, path: str, payload: dict):
    """PUT JSON to <base_url><path> with Bearer auth. Returns (status_code, body_bytes)."""
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

def _unwrap_data(parsed):
    """Extract the 'data' value from an API envelope response."""
    if isinstance(parsed, dict):
        return parsed.get("data") or parsed.get("Data")
    return parsed


def _parse_list(parsed) -> list:
    """Extract a list from an API response (handles envelope and direct list)."""
    if isinstance(parsed, list):
        return parsed
    data = _unwrap_data(parsed)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "Items"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


# ---------------------------------------------------------------------------
# Item normalisation helpers
# ---------------------------------------------------------------------------

def _item_id(item) -> str:
    return str(item.get("id") or item.get("Id") or item.get("_id") or "")


def _item_name(item) -> str:
    return str(item.get("name") or item.get("Name") or item.get("title") or _item_id(item))
