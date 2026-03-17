#!/usr/bin/env python3
"""DuploCloud MCP stdio<->HTTP proxy.

Re-reads ~/.duplocloud/.auth on every request so that token refreshes
(via /duplo:activate) take effect immediately without restarting Claude.

Protocol:
  stdin  — newline-delimited JSON-RPC 2.0 requests from Claude Code
  stdout — newline-delimited JSON-RPC 2.0 responses back to Claude Code
  HTTP   — Streamable MCP HTTP transport (JSON or SSE responses)
"""

import json
import sys
import pathlib
import urllib.request
import urllib.error

AUTH_FILE = pathlib.Path.home() / ".duplocloud" / ".auth"

# Reused across requests within one Claude session (stateful MCP session)
_session_id = None


def read_auth():
    with open(AUTH_FILE) as f:
        return json.load(f)


def write_msg(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def error_response(req_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def proxy(message):
    global _session_id
    req_id = message.get("id")

    try:
        auth = read_auth()
    except FileNotFoundError:
        write_msg(error_response(
            req_id, -32001,
            "~/.duplocloud/.auth not found — run /duplo:activate first."
        ))
        return
    except Exception as e:
        write_msg(error_response(req_id, -32001, f"Failed to read auth: {e}"))
        return

    url = auth["base_url"].rstrip("/") + "/mcp"
    token = auth["token"]

    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("Authorization", f"Bearer {token}")
    if _session_id:
        req.add_header("Mcp-Session-Id", _session_id)

    try:
        with urllib.request.urlopen(req) as resp:
            new_sid = resp.headers.get("Mcp-Session-Id")
            if new_sid:
                _session_id = new_sid

            content_type = resp.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                # Parse SSE stream — each "data: <json>" line is one response
                for raw in resp:
                    line = raw.decode("utf-8").rstrip("\r\n")
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if payload and payload != "[DONE]":
                            try:
                                write_msg(json.loads(payload))
                            except json.JSONDecodeError:
                                pass
            else:
                body = resp.read().decode("utf-8").strip()
                if body:
                    try:
                        write_msg(json.loads(body))
                    except json.JSONDecodeError:
                        pass

    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        write_msg(error_response(
            req_id, -32000,
            f"HTTP {e.code} {e.reason}. {detail}".strip()
        ))
    except urllib.error.URLError as e:
        write_msg(error_response(req_id, -32000, f"Connection error: {e.reason}"))
    except Exception as e:
        write_msg(error_response(req_id, -32001, f"Proxy error: {e}"))


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        proxy(message)


if __name__ == "__main__":
    main()
