"""DuploCloud non-interactive project activation script.

Usage:
  python3 duplo_activate.py --check-state                      Print current workspace and project from state as JSON
  python3 duplo_activate.py --list                             List available projects (exit 3 if no valid auth)
  python3 duplo_activate.py --select N                         Activate project N (1-based index)
  python3 duplo_activate.py --edit-auth                        Create auth file if missing and open it in $EDITOR
  python3 duplo_activate.py --login --url URL --token TOK      Validate and save credentials
  python3 duplo_activate.py --list-workspaces                   List available workspaces
  python3 duplo_activate.py --set-workspace N                   Set workspace N (1-based index) in state

Exit codes:
  0 = success
  1 = general error
  3 = auth missing or invalid
"""

import argparse
import json
import os
import subprocess
import sys

from duplo_common import (
    require_auth, write_auth,
    load_state, save_state,
    _get,
)


# ---------------------------------------------------------------------------
# API calls specific to activation
# ---------------------------------------------------------------------------

def validate_token(base_url: str, token: str) -> int:
    """Validate token via GET /admin/GetUserRoleInfo. Returns HTTP status code."""
    status, _ = _get(base_url, token, "/admin/GetUserRoleInfo")
    return status


def list_workspaces(base_url: str, token: str) -> list:
    status, body = _get(base_url, token, "/v1/aiservicedesk/admin/data/workspaces")
    if status == 401:
        print("Token is expired or invalid (401).", file=sys.stderr)
        sys.exit(3)
    if status != 200:
        print(f"Failed to list workspaces (HTTP {status}).", file=sys.stderr)
        sys.exit(1)
    parsed = json.loads(body)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        data = parsed.get("data") or parsed.get("Data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "Items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
    return []


def list_projects(base_url: str, token: str, workspace_id: str) -> list:
    path = f"/v1/aiservicedesk/user/data/projects?filters[workspaceId]={workspace_id}"
    status, body = _get(base_url, token, path)
    if status != 200:
        print(f"Failed to list projects (HTTP {status}).", file=sys.stderr)
        sys.exit(1)
    parsed = json.loads(body)
    if isinstance(parsed, dict):
        data = parsed.get("data") or parsed.get("Data")
        if isinstance(data, dict):
            for key in ("items", "Items", "projects", "Projects"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        for key in ("data", "Data", "items", "Items", "projects", "Projects"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return []
    return parsed


# ---------------------------------------------------------------------------
# Workspace/project normalisation
# ---------------------------------------------------------------------------

def _ws_id(ws) -> str:
    return str(ws.get("id") or ws.get("Id") or ws.get("_id") or "")


def _ws_name(ws) -> str:
    return str(ws.get("name") or ws.get("Name") or ws.get("title") or _ws_id(ws))


def _proj_id(proj) -> str:
    if isinstance(proj, str):
        return proj
    return str(proj.get("Id") or proj.get("id") or proj.get("project_id") or "")


def _proj_name(proj) -> str:
    if isinstance(proj, str):
        return proj
    pid = _proj_id(proj)
    return str(proj.get("Name") or proj.get("name") or proj.get("project_name") or pid)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_check_state():
    state = load_state()
    output = {
        "workspace": state.get("workspace"),
        "project": state.get("project"),
    }
    print(json.dumps(output, indent=2))


def cmd_login(url: str, token: str):
    status = validate_token(url, token)
    if status == 200:
        write_auth(url, token)
        print(f"Credentials saved for {url}.")
    elif status == 401:
        print("Invalid token (401). Please check your credentials.", file=sys.stderr)
        sys.exit(3)
    else:
        print(f"Unexpected response (HTTP {status}) validating credentials.", file=sys.stderr)
        sys.exit(1)



def cmd_edit_auth():
    """Create the auth file with empty fields if missing, then open it in VSCode.
    If VSCode is unavailable, print a shell command the user can run in their terminal."""
    from duplo_common import AUTH_FILE
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AUTH_FILE.exists():
        with open(AUTH_FILE, "w") as f:
            json.dump({"base_url": "", "token": ""}, f, indent=2)
            f.write("\n")
        AUTH_FILE.chmod(0o600)

    # Try VSCode first
    try:
        subprocess.run(["code", "--wait", str(AUTH_FILE)], check=True)
        return
    except FileNotFoundError:
        pass

    # VSCode not available — print a bash script for the user to run in their terminal
    print(
        f"\nVSCode ('code') is not available. Run this script in your terminal to set your credentials:\n\n"
        f"mkdir -p ~/.duplocloud\n"
        f"read -p 'DuploCloud base URL: ' DUPLO_URL\n"
        f"read -s -p 'API token (hidden): ' DUPLO_TOKEN && echo\n"
        f"cat > ~/.duplocloud/.auth <<EOF\n"
        f'{{\n'
        f'  "base_url": "$DUPLO_URL",\n'
        f'  "token": "$DUPLO_TOKEN"\n'
        f'}}\n'
        f"EOF\n"
        f"chmod 600 ~/.duplocloud/.auth\n"
        f"echo 'Credentials saved.'\n\n"
        f"Then re-run /duplo:activate_project."
    )
    sys.exit(1)


def cmd_list():
    auth = require_auth()
    base_url = auth["base_url"]
    token = auth["token"]

    status = validate_token(base_url, token)
    if status == 401:
        print("Token is expired or invalid (401).", file=sys.stderr)
        sys.exit(3)
    elif status != 200:
        print(f"Unexpected response (HTTP {status}) validating token.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    workspace_id = state.get("workspace_id", "")
    if not workspace_id:
        print("No workspace set. Run /duplo:activate_project and select an workspace first.", file=sys.stderr)
        sys.exit(3)

    projects = list_projects(base_url, token, workspace_id)
    if not projects:
        print("No projects found for this workspace.", file=sys.stderr)
        sys.exit(1)

    current_id = state.get("project_id", "")
    print("Available projects:")
    for i, proj in enumerate(projects, start=1):
        pid = _proj_id(proj)
        pname = _proj_name(proj)
        marker = "  * (current)" if pid == current_id else ""
        print(f"  {i}. {pname}{marker}")


def cmd_select(n: int):
    auth = require_auth()
    base_url = auth["base_url"]
    token = auth["token"]

    state = load_state()
    workspace_id = state.get("workspace_id", "")
    if not workspace_id:
        print("No workspace set. Run /duplo:activate_project and select an workspace first.", file=sys.stderr)
        sys.exit(3)

    projects = list_projects(base_url, token, workspace_id)
    if not projects:
        print("No projects found for this workspace.", file=sys.stderr)
        sys.exit(1)

    if n < 1 or n > len(projects):
        print(f"Invalid selection {n}. Must be between 1 and {len(projects)}.", file=sys.stderr)
        sys.exit(1)

    chosen = projects[n - 1]
    project_id = _proj_id(chosen)
    project_name = _proj_name(chosen)

    state["project"] = chosen
    state["project_id"] = project_id
    state["project_name"] = project_name
    for key in ("active_ticket_id", "active_ticket_title", "active_ticket_name",
                "spec_ticket_id", "spec_ticket_project_id",
                "plan_ticket_id", "plan_ticket_project_id"):
        state.pop(key, None)
    save_state(state)

    print(f"Project context activated: {project_name}")


def cmd_list_workspaces():
    auth = require_auth()
    base_url = auth["base_url"]
    token = auth["token"]

    workspaces = list_workspaces(base_url, token)
    if not workspaces:
        print("No workspaces found.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    current_id = state.get("workspace_id", "")

    print("Available workspaces:")
    for i, ws in enumerate(workspaces, start=1):
        eid = _ws_id(ws)
        ename = _ws_name(ws)
        marker = "  * (current)" if eid == current_id else ""
        print(f"  {i}. {ename} (id: {eid}){marker}")

    if len(workspaces) == 1:
        print("(Only one workspace found — will be auto-selected.)")


def cmd_set_workspace(n: int):
    auth = require_auth()
    base_url = auth["base_url"]
    token = auth["token"]

    workspaces = list_workspaces(base_url, token)
    if not workspaces:
        print("No workspaces found.", file=sys.stderr)
        sys.exit(1)

    if n < 1 or n > len(workspaces):
        print(f"Invalid selection {n}. Must be between 1 and {len(workspaces)}.", file=sys.stderr)
        sys.exit(1)

    chosen = workspaces[n - 1]
    workspace_id = _ws_id(chosen)
    workspace_name = _ws_name(chosen)

    state = load_state()
    state["workspace"] = chosen
    state["workspace_id"] = workspace_id
    state["workspace_name"] = workspace_name
    # Clear old project — it may not belong to the new workspace
    state.pop("project", None)
    state.pop("project_id", None)
    state.pop("project_name", None)
    for key in ("active_ticket_id", "active_ticket_title", "active_ticket_name",
                "spec_ticket_id", "spec_ticket_project_id",
                "plan_ticket_id", "plan_ticket_project_id"):
        state.pop(key, None)
    save_state(state)

    print(f"Workspace set: {workspace_name} (id: {workspace_id})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DuploCloud project activation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-state", action="store_true", help="Print current workspace and project from state as JSON")
    group.add_argument("--list", action="store_true", help="List available projects")
    group.add_argument("--select", type=int, metavar="N", help="Activate project N (1-based)")
    group.add_argument("--edit-auth", action="store_true", help="Create auth file if missing and open it in $EDITOR")
    group.add_argument("--login", action="store_true", help="Validate and save credentials")
    group.add_argument("--list-workspaces", action="store_true", help="List available workspaces")
    group.add_argument("--set-workspace", type=int, metavar="N", help="Set workspace N (1-based) in state")
    parser.add_argument("--url", help="DuploCloud base URL (required with --login)")
    parser.add_argument("--token", help="API token (required with --login)")

    args = parser.parse_args()

    if args.check_state:
        cmd_check_state()
    elif args.edit_auth:
        cmd_edit_auth()
    elif args.login:
        if not args.url or not args.token:
            parser.error("--login requires --url and --token")
        cmd_login(args.url, args.token)
    elif args.list:
        cmd_list()
    elif args.list_workspaces:
        cmd_list_workspaces()
    elif args.set_workspace is not None:
        cmd_set_workspace(args.set_workspace)
    else:
        cmd_select(args.select)


if __name__ == "__main__":
    main()
