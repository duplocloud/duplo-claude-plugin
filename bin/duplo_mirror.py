"""Mirror conversation messages to the active DuploCloud ticket.

Called by the Claude Code Stop and UserPromptSubmit hooks — reads hook JSON
from stdin and posts the relevant message to the active ticket via
sendmessageStreaming (RecordOnly).

Always exits 0. Logs progress to stdout (redirected to mirror.log by the hook).
"""

import contextlib
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

from duplo_common import load_auth

LOCK_TIMEOUT = 5  # seconds


@contextlib.contextmanager
def _ticket_lock(ticket_name: str):
    """File-based lock scoped to ticket_name. Auto-releases after LOCK_TIMEOUT seconds."""
    lock_dir = pathlib.Path.home() / ".duplocloud"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"mirror_{ticket_name}.lock"

    acquired = False
    deadline = time.monotonic() + LOCK_TIMEOUT
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            # Steal stale lock
            try:
                age = time.time() - lock_file.stat().st_mtime
                if age >= LOCK_TIMEOUT:
                    lock_file.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(0.1)

    if not acquired:
        _log(f"could not acquire lock for ticket={ticket_name} after {LOCK_TIMEOUT}s — skipping")
        return

    try:
        yield
    finally:
        lock_file.unlink(missing_ok=True)


def _log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] duplo_mirror: {msg}", flush=True)


_ACTIVE_SESSION_FILE = pathlib.Path.home() / ".duplocloud" / ".active_session"


def _set_active_session(session_id: str):
    """Write session_id so CLI tools resolve the correct per-session state file."""
    try:
        _ACTIVE_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ACTIVE_SESSION_FILE.write_text(session_id)
    except Exception as e:
        _log(f"failed to write active session: {e}")


def _state_file() -> pathlib.Path:
    """Return the per-session state file path (mirrors duplo_common._state_file)."""
    try:
        session_id = _ACTIVE_SESSION_FILE.read_text().strip()
        if session_id:
            return pathlib.Path.home() / ".duplocloud" / "sessions" / session_id / "state.json"
    except OSError:
        pass
    return pathlib.Path.home() / ".duplocloud" / "state.json"


def _load_state() -> dict:
    state_file = _state_file()
    if not state_file.exists():
        _log(f"state file not found: {state_file}")
        return {}
    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception as e:
        _log(f"failed to load state: {e}")
        return {}


def _save_turn_start():
    state_file = _state_file()
    try:
        state = {}
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
        state["mirror_turn_start"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        _log(f"failed to save turn start: {e}")


def _post_silent(base_url: str, token: str, path: str, payload: dict):
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    _log(f"POST {path} body: {json.dumps(payload)}")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            _log(f"POST {path} -> HTTP {resp.status} response: {body}")
    except urllib.error.HTTPError as e:
        _log(f"POST {path} -> HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
    except Exception as e:
        _log(f"POST {path} -> error: {e}")


def _extract_assistant_messages(path: str, since: str | None = None) -> str:
    """Return all assistant text blocks from the turn concatenated together."""
    parts = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if since:
                    ts = entry.get("timestamp", "")
                    if ts and ts < since:
                        continue
                msg = entry if "role" in entry else entry.get("message", {})
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    parts.append(content.strip())
                elif isinstance(content, list):
                    texts = [b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text"]
                    text = "\n".join(texts).strip()
                    if text:
                        parts.append(text)
    except Exception as e:
        _log(f"failed to read transcript {path}: {e}")
    return "\n\n".join(parts)


def _content_hash(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _send_message(content: str, role: str = "assistant"):
    auth = load_auth()
    if not auth:
        _log("auth file not found or invalid — skipping")
        return
    state = _load_state()
    workspace_id = state.get("workspace_id")
    ticket_id   = state.get("active_ticket_name")
    if not workspace_id:
        _log("no workspace_id in state — skipping")
        return
    if not ticket_id:
        _log("no active_ticket_name in state — cannot mirror (name required for API)")
        return

    chash = _content_hash(content)
    _log(f"sending to ticket={ticket_id} workspace={workspace_id} ({len(content)} chars, hash={chash})")
    payload = {
        "content": content,
        "message_mode": 1,
        "data": {},
        "tenant_id": workspace_id,
        "role": role,
    }

    state_file = _state_file()

    with _ticket_lock(ticket_id):
        # Re-read state inside the lock — another process may have just sent this content
        fresh_state = _load_state()
        if fresh_state.get("last_mirror_hash") == chash:
            _log(f"duplicate detected (hash={chash}) — skipping")
            return

        _post_silent(
            auth["base_url"], auth["token"],
            f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_id}/sendMessage",
            payload,
        )

        # Record hash so concurrent callers skip this content
        try:
            fresh_state["last_mirror_hash"] = chash
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(fresh_state, f, indent=2)
        except Exception as e:
            _log(f"failed to save mirror hash: {e}")


def handle_user_prompt(hook_data: dict):
    session_id = hook_data.get("session_id", "").strip()
    if session_id:
        _set_active_session(session_id)
        _log(f"active session set to {session_id}")

    prompt = hook_data.get("prompt", "").strip()
    if not prompt:
        _log("empty prompt — skipping")
        return

    _save_turn_start()

    lines = "\n".join(f"> {line}" for line in prompt.splitlines())
    content = f"**User:**\n{lines}"
    _send_message(content, role="user")


def handle_stop(hook_data: dict):
    transcript_path = hook_data.get("transcript_path")
    if not transcript_path:
        _log(f"no transcript_path in hook data: {list(hook_data.keys())}")
        return

    session_id = hook_data.get("session_id", "").strip()
    if session_id:
        _set_active_session(session_id)
    _log(f"session: {session_id}  transcript: {transcript_path}")

    state = _load_state()
    since = state.get("mirror_turn_start")

    import time
    text = ""
    for attempt in range(10):
        text = _extract_assistant_messages(transcript_path, since=since)
        if text:
            break
        _log(f"no assistant message yet (attempt {attempt + 1}), retrying...")
        time.sleep(0.5)

    if not text:
        _log("no assistant message found in transcript")
        return
    content = f"**Claude Code:**\n\n{text}"
    _send_message(content, role="assistant")


def main():
    _log("hook fired")
    raw = sys.stdin.read().strip()
    if not raw:
        _log("empty stdin — exiting")
        return
    try:
        hook_data = json.loads(raw)
    except Exception as e:
        _log(f"failed to parse stdin JSON: {e}")
        return
    event = hook_data.get("hook_event_name", "Stop")

    if event == "UserPromptSubmit":
        handle_user_prompt(hook_data)
    else:
        handle_stop(hook_data)


if __name__ == "__main__":
    main()
