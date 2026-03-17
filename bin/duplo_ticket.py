"""DuploCloud ticket activation script.

Usage:
  python3 duplo_ticket.py --check-project
  python3 duplo_ticket.py --list-workspaces
  python3 duplo_ticket.py --list-agents --workspace-id <id>
  python3 duplo_ticket.py --list-execution-tickets
  python3 duplo_ticket.py --list-execution-tasks
  python3 duplo_ticket.py --get-task-by-index --task-index N [--stage-index S]
  python3 duplo_ticket.py --check-task-ticket --task-id <task_name>
  python3 duplo_ticket.py --create-execution-task-ticket --task-id <task_name> --agent-id <id>
  python3 duplo_ticket.py --create-ticket --type spec_creation|plan_execution \
                           --agent-id <id> --workspace-id <id>
  python3 duplo_ticket.py --activate-ticket --type spec_creation|plan_execution
  python3 duplo_ticket.py --get-ticket-context
  python3 duplo_ticket.py --get-ticket-status
  python3 duplo_ticket.py --set-ticket-status --status <status> [--disposition <disposition>]
  python3 duplo_ticket.py --save-summary --summary-file <path>
  python3 duplo_ticket.py --get-spec
  python3 duplo_ticket.py --save-spec --spec-file <path>
  python3 duplo_ticket.py --get-plan
  python3 duplo_ticket.py --save-plan --plan-file <path>

Exit codes:
  0 = success
  1 = general error (or no existing ticket for --activate-ticket / --check-task-ticket)
  3 = auth missing or invalid / no active project
"""

import argparse
import json
import pathlib
import sys

from duplo_common import (
    require_auth, load_state, update_state,
    _get, _post, _put,
    _unwrap_data, _parse_list,
    _item_id, _item_name,
)

TICKET_TITLES = {
    "spec_creation":  "{project_name}-Spec-Creation-Ticket",
    "plan_execution": "{project_name}-Plan-Execution-Ticket",
}

PROJECT_TYPE_INT = {
    "spec_creation":  0,
    "plan_execution": 2,
}

TICKET_DESCRIPTIONS = {
    "spec_creation": (
        "The specification for the project `{project_name}` is currently in draft state "
        "and needs to be created. Please review the project details and create the necessary "
        "specifications to move forward with the project execution."
    ),
    "plan_execution": (
        "An execution task for the project `{project_name}` needs to be worked on. "
        "Please review the approved plan and carry out the implementation steps assigned "
        "to this execution ticket."
    ),
}


# ---------------------------------------------------------------------------
# Ticket-specific helpers
# ---------------------------------------------------------------------------

def _extract_execution_stages(data: dict) -> list:
    """Extract stages list from project execution data."""
    execution = data.get("execution") or {}
    return execution.get("stages") or []


def _fetch_ticket(base_url: str, token: str, workspace_id: str, ticket_ref: str) -> dict | None:
    """Fetch a single ticket by id or name. Returns the ticket dict or None."""
    status, body = _get(base_url, token, f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_ref}")
    if status != 200 or not body:
        return None
    try:
        parsed = json.loads(body)
        data = _unwrap_data(parsed)
        if isinstance(data, dict) and data:
            return data
        if isinstance(parsed, dict) and parsed:
            return parsed
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Subcommand: --check-project
# ---------------------------------------------------------------------------

def cmd_check_project():
    auth = require_auth()
    state = load_state()

    project_id = state.get("project_id")
    workspace_id = state.get("workspace_id")
    if not project_id or not workspace_id:
        print("No active project found. Please activate a project first.", file=sys.stderr)
        sys.exit(3)

    project_name = state.get("project_name", project_id)
    base_url = auth["base_url"]
    token = auth["token"]

    status, body = _get(base_url, token, f"/v1/aiservicedesk/user/data/projects/{project_id}")
    if status != 200:
        print(f"Failed to fetch project details (HTTP {status}).", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    data = _unwrap_data(parsed)
    if not isinstance(data, dict):
        print("Unexpected project details response format.", file=sys.stderr)
        sys.exit(1)

    spec = data.get("spec") or {}
    plan = data.get("plan") or {}
    spec_meta = spec.get("metaData") or spec.get("metadata") or {}
    plan_meta = plan.get("metaData") or plan.get("metadata") or {}

    spec_approved = (spec_meta.get("approvalState") or spec_meta.get("ApprovalState")) == "Approved"
    plan_approved = (plan_meta.get("approvalState") or plan_meta.get("ApprovalState")) == "Approved"

    if not spec_approved:
        action = "spec"
    elif not plan_approved:
        action = "plan"
    else:
        action = "none"

    spec_content = spec.get("content") or spec.get("Content") or ""
    plan_content = plan.get("content") or plan.get("Content") or ""
    spec_empty = not bool(spec_content.strip())
    plan_empty = not bool(plan_content.strip())

    stages = _extract_execution_stages(data)
    has_execution_tasks = any(stage.get("tasks") for stage in stages)

    scope_ids = data.get("scopeIds") or []
    update_state({"scope_ids": scope_ids})

    result = {
        "action": action,
        "project_id": project_id,
        "project_name": project_name,
        "spec_empty": spec_empty,
        "plan_empty": plan_empty,
        "has_execution_tasks": has_execution_tasks,
    }
    print(json.dumps(result))


# ---------------------------------------------------------------------------
# Subcommand: --list-workspaces
# ---------------------------------------------------------------------------

def cmd_list_workspaces():
    state = load_state()
    workspace_id = state.get("workspace_id")
    if not workspace_id:
        print("No workspace set. Run `/duplo:activate_project` first.", file=sys.stderr)
        sys.exit(3)
    print(workspace_id)


# ---------------------------------------------------------------------------
# Subcommand: --list-agents
# ---------------------------------------------------------------------------

def cmd_list_agents(workspace_id: str | None = None):
    auth = require_auth()
    if not workspace_id:
        state = load_state()
        workspace_id = state.get("workspace_id")
    if not workspace_id:
        print("No workspace ID found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)
    base_url = auth["base_url"]
    token = auth["token"]

    status, body = _get(
        base_url, token,
        f"/v1/aiservicedesk/user/data/workspaces/{workspace_id}/agents"
    )
    if status != 200:
        print(f"Failed to list agents (HTTP {status}).", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    agents = _parse_list(parsed)
    if not agents:
        print("No agents found for this workspace.", file=sys.stderr)
        sys.exit(1)

    print("Available agents:")
    for i, agent in enumerate(agents, start=1):
        aid = _item_id(agent)
        aname = _item_name(agent)
        print(f"  {i}. {aname} (id: {aid})")


# ---------------------------------------------------------------------------
# Subcommand: --list-execution-tickets
# ---------------------------------------------------------------------------

def cmd_list_execution_tickets():
    auth = require_auth()
    state = load_state()

    project_id = state.get("project_id")
    workspace_id = state.get("workspace_id")
    if not project_id or not workspace_id:
        print("No active project found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)

    base_url = auth["base_url"]
    token = auth["token"]
    project_type = PROJECT_TYPE_INT["plan_execution"]

    status, body = _get(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}"
        f"?projectId={project_id}&projectType={project_type}",
    )
    if status != 200 or not body:
        print(f"Failed to list execution tickets (HTTP {status}).", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    tickets = _parse_list(parsed)
    if not tickets:
        print("No execution tickets found for this project.", file=sys.stderr)
        sys.exit(1)

    print("Available execution tickets:")
    for i, ticket in enumerate(tickets, start=1):
        tid = _item_id(ticket)
        tname = str(ticket.get("title") or ticket.get("name") or tid)
        print(f"  {i}. {tname} (id: {tid})")


# ---------------------------------------------------------------------------
# Helpers: fetch execution tickets map
# ---------------------------------------------------------------------------

def _fetch_execution_tickets_map(auth: dict, project_id: str, workspace_id: str) -> dict:
    """Fetch all execution tickets for the project and return a map of taskId -> ticket."""
    base_url = auth["base_url"]
    token = auth["token"]
    status, body = _get(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}"
        f"?projectId={project_id}&projectType={PROJECT_TYPE_INT['plan_execution']}",
    )
    if status != 200 or not body:
        return {}
    try:
        parsed = json.loads(body)
        tickets = _parse_list(parsed)
        if not tickets:
            d = _unwrap_data(parsed)
            if isinstance(d, list):
                tickets = d
        result = {}
        for t in tickets:
            proj = t.get("project") or {}
            tid = proj.get("taskId") or proj.get("TaskId") or ""
            if tid:
                result[tid] = t
        return result
    except Exception:
        return {}


def _ticket_current_status(ticket: dict) -> str:
    """Return the current status from history.statuses[-1].
    Defaults to 'open' when history is absent (newly created ticket).
    """
    history = ticket.get("history") or {}
    statuses = history.get("statuses") or []
    if statuses:
        last = statuses[-1]
        return str(last.get("status") or last.get("Status") or "open")
    return str(ticket.get("status") or ticket.get("Status") or "open")


def _ticket_summary(ticket: dict) -> dict:
    """Extract id, name and status from a ticket dict."""
    return {
        "ticket_id":     _item_id(ticket),
        "ticket_name":   str(ticket.get("name") or ""),
        "ticket_status": _ticket_current_status(ticket),
    }


# ---------------------------------------------------------------------------
# Subcommand: --list-execution-tasks
# ---------------------------------------------------------------------------

def cmd_list_execution_tasks():
    auth = require_auth()
    state = load_state()
    project_id, workspace_id = _require_project(state)
    data = _get_project_data(auth, project_id)

    stages = _extract_execution_stages(data)
    total = sum(len(stage.get("tasks") or []) for stage in stages)

    tickets_map = _fetch_execution_tickets_map(auth, project_id, workspace_id)

    output_stages = []
    for stage in stages:
        tasks = stage.get("tasks") or []
        task_list = []
        for t in tasks:
            task_name = t.get("name") or ""
            task_out = {
                "name":        task_name,
                "title":       t.get("title") or "",
                "description": t.get("description") or "",
            }
            ticket = tickets_map.get(task_name)
            if ticket:
                task_out.update(_ticket_summary(ticket))
            task_list.append(task_out)
        output_stages.append({
            "name":        stage.get("name") or stage.get("title") or "",
            "description": stage.get("description") or "",
            "tasks":       task_list,
        })

    print(json.dumps({"total": total, "stages": output_stages}))


# ---------------------------------------------------------------------------
# Subcommand: --get-task-by-index
# ---------------------------------------------------------------------------

def cmd_get_task_by_index(task_index: int, stage_index: int | None = None):
    """Resolve a 1-based task selection to its name/title/description and existing ticket info.

    If stage_index is given, task_index is relative to that stage.
    Otherwise task_index counts across all stages (flat numbering).
    Prints JSON: {"name": "<uuid>", "title": "...", "description": "...",
                  "ticket_id": "...", "ticket_name": "...", "ticket_status": "..."}
    ticket_* fields are present only when a ticket already exists for the task.
    """
    auth = require_auth()
    state = load_state()
    project_id, _ = _require_project(state)
    data = _get_project_data(auth, project_id)
    stages = _extract_execution_stages(data)

    if stage_index is not None:
        if stage_index < 1 or stage_index > len(stages):
            print(f"Invalid stage index {stage_index}. Must be 1–{len(stages)}.", file=sys.stderr)
            sys.exit(1)
        tasks = stages[stage_index - 1].get("tasks") or []
        if task_index < 1 or task_index > len(tasks):
            print(f"Invalid task index {task_index}. Must be 1–{len(tasks)}.", file=sys.stderr)
            sys.exit(1)
        t = tasks[task_index - 1]
    else:
        flat: list = []
        for stage in stages:
            flat.extend(stage.get("tasks") or [])
        if task_index < 1 or task_index > len(flat):
            print(f"Invalid task index {task_index}. Must be 1–{len(flat)}.", file=sys.stderr)
            sys.exit(1)
        t = flat[task_index - 1]

    print(json.dumps({
        "name":        t.get("name") or "",
        "title":       t.get("title") or "",
        "description": t.get("description") or "",
    }))


# ---------------------------------------------------------------------------
# Subcommand: --check-task-ticket
# ---------------------------------------------------------------------------

def cmd_check_task_ticket(task_id: str):
    auth = require_auth()
    state = load_state()
    project_id, workspace_id = _require_project(state)

    # Fetch all execution tickets and match strictly by project.taskId
    tickets_map = _fetch_execution_tickets_map(auth, project_id, workspace_id)
    ticket = tickets_map.get(task_id)

    if not ticket:
        print(f"No ticket found for task '{task_id}'.", file=sys.stderr)
        sys.exit(1)

    ticket_id    = _item_id(ticket)
    ticket_title = str(ticket.get("title") or ticket_id)
    ticket_name  = str(ticket.get("name") or "")

    update_state({
        "execution_ticket_id":         ticket_id,
        "execution_ticket_project_id": project_id,
        "active_ticket_id":            ticket_id,
        "active_ticket_title":         ticket_title,
        "active_ticket_name":          ticket_name,
    })

    print(f"Ticket found: {ticket_title} (id: {ticket_id})")


# ---------------------------------------------------------------------------
# Subcommand: --create-execution-task-ticket
# ---------------------------------------------------------------------------

def cmd_create_execution_task_ticket(task_id: str, agent_id: str):
    auth = require_auth()
    state = load_state()
    project_id, workspace_id = _require_project(state)

    # Look up task title and description from project data
    data = _get_project_data(auth, project_id)
    stages = _extract_execution_stages(data)
    task_title = task_id
    task_description = ""
    for stage in stages:
        for t in (stage.get("tasks") or []):
            if t.get("name") == task_id:
                task_title = t.get("title") or task_id
                task_description = t.get("description") or ""
                break

    base_url = auth["base_url"]
    token = auth["token"]
    scope_ids = state.get("scope_ids") or []

    payload = {
        "title": task_title,
        "aiAgentId": agent_id,
        "workspaceId": workspace_id,
        "ticketContextForAgent": {"scopeIds": scope_ids},
        "project": {
            "id": project_id,
            "type": "plan_execution",
            "taskId": task_id,
        },
        "description": task_description,
    }

    status, body = _post(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}",
        payload,
    )
    if status not in (200, 201):
        err = body.decode("utf-8", errors="replace") if body else ""
        print(f"Failed to create ticket (HTTP {status}): {err}", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    resp_data = _unwrap_data(parsed)
    if isinstance(resp_data, dict):
        ticket_id = _item_id(resp_data)
        ticket_title_out = str(resp_data.get("title") or task_title)
        ticket_name = str(resp_data.get("name") or "")
    elif isinstance(parsed, dict):
        inner = parsed.get("ticket") or {}
        ticket_id = _item_id(parsed) or _item_id(inner) or "unknown"
        ticket_title_out = str(inner.get("title") or parsed.get("title") or task_title)
        ticket_name = str(inner.get("name") or parsed.get("name") or "")
    else:
        ticket_id = "unknown"
        ticket_title_out = task_title
        ticket_name = ""

    ticket_ref = ticket_name or ticket_id
    if ticket_ref and ticket_ref != "unknown":
        details = _fetch_ticket(base_url, token, workspace_id, ticket_ref)
        if details:
            ticket_id = _item_id(details) or ticket_id
            ticket_title_out = str(details.get("title") or ticket_title_out)
            ticket_name = str(details.get("name") or ticket_name)

    update_state({
        "execution_ticket_id": ticket_id,
        "execution_ticket_project_id": project_id,
        "active_ticket_id": ticket_id,
        "active_ticket_title": ticket_title_out,
        "active_ticket_name": ticket_name,
    })

    if not ticket_id or ticket_id == "unknown":
        ticket_id = ticket_name
    print(f"Ticket created: {ticket_title_out} (id: {ticket_id})")


# ---------------------------------------------------------------------------
# Subcommand: --create-ticket
# ---------------------------------------------------------------------------

def cmd_create_ticket(ticket_type: str, agent_id: str, workspace_id: str | None = None):
    auth = require_auth()
    state = load_state()

    project_id = state.get("project_id")
    project_name = state.get("project_name", project_id)
    if not project_id:
        print("No active project found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)

    if not workspace_id:
        workspace_id = state.get("workspace_id")
    if not workspace_id:
        print("No workspace ID found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)

    base_url = auth["base_url"]
    token = auth["token"]
    scope_ids = state.get("scope_ids") or []
    title = TICKET_TITLES[ticket_type].format(project_name=project_name)

    payload = {
        "title": title,
        "aiAgentId": agent_id,
        "project": {
            "id": project_id,
            "type": PROJECT_TYPE_INT[ticket_type],
        },
        "ticketContextForAgent": {
            "scopeIds": scope_ids,
        },
        "tenantId": workspace_id,
        "platform_context": {
            "duplo_base_url": base_url,
            "duplo_token": token,
            "project": {
                "id": project_id,
                "type": PROJECT_TYPE_INT[ticket_type],
            },
        },
    }

    status, body = _post(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}",
        payload,
    )
    if status not in (200, 201):
        err = body.decode("utf-8", errors="replace") if body else ""
        print(f"Failed to create ticket (HTTP {status}): {err}", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    data = _unwrap_data(parsed)
    if isinstance(data, dict):
        ticket_id    = _item_id(data)
        ticket_title = str(data.get("title") or title)
        ticket_name  = str(data.get("name") or "")
    elif isinstance(parsed, dict):
        inner        = parsed.get("ticket") or {}
        ticket_id    = (_item_id(parsed) or _item_id(inner) or "unknown")
        ticket_title = str(inner.get("title") or parsed.get("title") or title)
        ticket_name  = str(inner.get("name") or parsed.get("name") or "")
    else:
        ticket_id    = "unknown"
        ticket_title = title
        ticket_name  = ""

    ticket_ref = ticket_name or ticket_id
    if ticket_ref and ticket_ref != "unknown":
        details = _fetch_ticket(base_url, token, workspace_id, ticket_ref)
        if details:
            ticket_id    = _item_id(details) or ticket_id
            ticket_title = str(details.get("title") or ticket_title)
            ticket_name  = str(details.get("name") or ticket_name)

    state_key   = "spec_ticket_id"         if ticket_type == "spec_creation" else "execution_ticket_id"
    project_key = "spec_ticket_project_id" if ticket_type == "spec_creation" else "execution_ticket_project_id"
    update_state({
        state_key:             ticket_id,
        project_key:           project_id,
        "active_ticket_id":    ticket_id,
        "active_ticket_title": ticket_title,
        "active_ticket_name":  ticket_name,
    })

    if not ticket_id or ticket_id == "unknown":
        ticket_id = ticket_name

    print(f"Ticket created: {ticket_title} (id: {ticket_id})")


# ---------------------------------------------------------------------------
# Subcommand: --activate-ticket
# ---------------------------------------------------------------------------

def cmd_activate_ticket(ticket_type: str):
    auth = require_auth()
    state = load_state()

    project_id  = state.get("project_id")
    workspace_id = state.get("workspace_id")
    if not project_id or not workspace_id:
        print("No active project. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)

    state_key   = "spec_ticket_id"         if ticket_type == "spec_creation" else "execution_ticket_id"
    project_key = "spec_ticket_project_id" if ticket_type == "spec_creation" else "execution_ticket_project_id"

    base_url = auth["base_url"]
    token    = auth["token"]
    project_type = PROJECT_TYPE_INT[ticket_type]

    status, body = _get(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}"
        f"?projectId={project_id}&projectType={project_type}",
    )

    if status == 200 and body:
        parsed  = json.loads(body)
        tickets = _parse_list(parsed)
        if tickets:
            ticket       = tickets[0]
            ticket_id    = _item_id(ticket)
            ticket_title = str(ticket.get("title") or ticket_id)
            ticket_name  = str(ticket.get("name") or "")

            # List endpoint may omit 'name'; fetch full ticket to get it
            if not ticket_name and ticket_id:
                details = _fetch_ticket(base_url, token, workspace_id, ticket_id)
                if details:
                    ticket_id    = _item_id(details) or ticket_id
                    ticket_title = str(details.get("title") or ticket_title)
                    ticket_name  = str(details.get("name") or "")

            update_state({
                state_key:             ticket_id,
                project_key:           project_id,
                "active_ticket_id":    ticket_id,
                "active_ticket_title": ticket_title,
                "active_ticket_name":  ticket_name,
            })
            print(f"Ticket activated: {ticket_title} (id: {ticket_id})")
            return

    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: --get-ticket-context
# ---------------------------------------------------------------------------

def cmd_get_ticket_context():
    """Fetch past messages for the active ticket and print them as readable context."""
    auth = require_auth()
    state = load_state()
    workspace_id, ticket_name, ticket_title = _require_active_ticket(state)

    base_url = auth["base_url"]
    token    = auth["token"]

    status, body = _get(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_name}/getmessages",
    )
    if status == 404 or not body:
        print(f"No past messages found for ticket '{ticket_title}'.")
        return
    if status != 200:
        print(f"Could not fetch context (HTTP {status}) — starting fresh.", file=sys.stderr)
        return

    try:
        parsed = json.loads(body)
    except Exception:
        print("Could not parse messages response — starting fresh.", file=sys.stderr)
        return

    messages = parsed if isinstance(parsed, list) else (
        parsed.get("data") or parsed.get("Data") or
        parsed.get("messages") or parsed.get("Messages") or []
    )
    if not messages:
        print(f"No past messages found for ticket '{ticket_title}'.")
        return

    print(f"=== Past context for ticket: {ticket_title} ===\n")
    for msg in messages:
        role    = msg.get("role") or "unknown"
        content = msg.get("content") or ""
        ts      = msg.get("timeStamp") or ""
        ts_str  = f"[{ts}] " if ts else ""
        print(f"{ts_str}{role}:\n{content}\n")
    print("=== End of past context ===")


# ---------------------------------------------------------------------------
# Subcommand: --get-ticket-status / --set-ticket-status
# ---------------------------------------------------------------------------

def _require_active_ticket(state: dict) -> tuple[str, str, str]:
    """Return (workspace_id, ticket_name, ticket_title) or exit 3."""
    workspace_id = state.get("workspace_id")
    ticket_name  = state.get("active_ticket_name")
    ticket_title = state.get("active_ticket_title", ticket_name or "")
    if not workspace_id or not ticket_name:
        print("No active ticket. Run /duplo:activate_ticket first.", file=sys.stderr)
        sys.exit(3)
    return workspace_id, ticket_name, ticket_title


def cmd_get_ticket_status():
    auth = require_auth()
    state = load_state()
    workspace_id, ticket_name, _ = _require_active_ticket(state)

    base_url = auth["base_url"]
    token    = auth["token"]
    status, body = _get(base_url, token,
                        f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_name}")
    if status != 200 or not body:
        print(f"Failed to fetch ticket (HTTP {status}).", file=sys.stderr)
        sys.exit(1)

    parsed = json.loads(body)
    data   = _unwrap_data(parsed)
    ticket = data if isinstance(data, dict) else (parsed if isinstance(parsed, dict) else {})
    print(_ticket_current_status(ticket))


def cmd_set_ticket_status(status: str, disposition: str | None = None):
    if status == "closed" and not disposition:
        print("Error: --disposition is required when --status is 'closed'. Use --disposition resolved or --disposition unResolved.", file=sys.stderr)
        sys.exit(1)

    auth = require_auth()
    state = load_state()
    workspace_id, ticket_name, ticket_title = _require_active_ticket(state)

    base_url = auth["base_url"]
    token    = auth["token"]
    payload: dict = {"status": status}
    if disposition:
        payload["disposition"] = disposition

    http_status, body = _put(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_name}/status",
        payload,
    )
    if http_status not in (200, 201, 204):
        err = body.decode("utf-8", errors="replace") if body else ""
        print(f"Failed to update ticket status (HTTP {http_status}): {err}", file=sys.stderr)
        sys.exit(1)

    msg = f"Ticket '{ticket_title}' status set to '{status}'"
    if disposition:
        msg += f" (disposition: {disposition})"
    print(msg)


# ---------------------------------------------------------------------------
# Subcommand: --save-summary
# ---------------------------------------------------------------------------

def cmd_save_summary(summary_file: str | None = None):
    auth = require_auth()
    state = load_state()
    workspace_id, ticket_name, ticket_title = _require_active_ticket(state)

    if summary_file:
        content_path = pathlib.Path(summary_file)
        if not content_path.exists():
            print(f"File not found: {summary_file}", file=sys.stderr)
            sys.exit(1)
        summary = content_path.read_text(encoding="utf-8").strip()
    else:
        summary = sys.stdin.read().strip()

    if not summary:
        print("Summary content is empty.", file=sys.stderr)
        sys.exit(1)

    base_url = auth["base_url"]
    token    = auth["token"]

    http_status, body = _post(
        base_url, token,
        f"/v1/aiservicedesk/tickets/{workspace_id}/{ticket_name}/saveSummary",
        {"summary": summary},
    )
    if http_status not in (200, 201, 204):
        err = body.decode("utf-8", errors="replace") if body else ""
        print(f"Failed to save summary (HTTP {http_status}): {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Summary saved for ticket '{ticket_title}'.")


# ---------------------------------------------------------------------------
# Subcommand: --get-spec / --get-plan
# ---------------------------------------------------------------------------

def _get_project_data(auth: dict, project_id: str) -> dict:
    base_url = auth["base_url"]
    token = auth["token"]
    status, body = _get(base_url, token, f"/v1/aiservicedesk/user/data/projects/{project_id}")
    if status != 200:
        print(f"Failed to fetch project details (HTTP {status}).", file=sys.stderr)
        sys.exit(1)
    parsed = json.loads(body)
    data = _unwrap_data(parsed)
    if not isinstance(data, dict):
        sys.exit(0)
    return data


def _require_project(state: dict) -> tuple[str, str]:
    project_id = state.get("project_id")
    workspace_id = state.get("workspace_id")
    if not project_id or not workspace_id:
        print("No active project found. Run /duplo:activate_project first.", file=sys.stderr)
        sys.exit(3)
    return project_id, workspace_id


def cmd_get_spec():
    auth = require_auth()
    state = load_state()
    project_id, _ = _require_project(state)
    data = _get_project_data(auth, project_id)
    spec = data.get("spec") or {}
    content = spec.get("content") or spec.get("Content") or ""
    print(content, end="")


def cmd_get_plan():
    auth = require_auth()
    state = load_state()
    project_id, _ = _require_project(state)
    data = _get_project_data(auth, project_id)
    plan = data.get("plan") or {}
    content = plan.get("content") or plan.get("Content") or ""
    print(content, end="")


# ---------------------------------------------------------------------------
# Subcommand: --save-spec / --save-plan
# ---------------------------------------------------------------------------

def _save_artifact(artifact_key: str, file_path: str, approve: bool):
    auth = require_auth()
    state = load_state()
    project_id, _ = _require_project(state)

    content_path = pathlib.Path(file_path)
    if not content_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = content_path.read_text(encoding="utf-8")
    base_url = auth["base_url"]
    token = auth["token"]

    project_obj = _get_project_data(auth, project_id)

    if artifact_key not in project_obj or not isinstance(project_obj[artifact_key], dict):
        project_obj[artifact_key] = {}
    project_obj[artifact_key]["content"] = content

    if approve:
        if not isinstance(project_obj[artifact_key].get("metaData"), dict):
            project_obj[artifact_key]["metaData"] = {}
        project_obj[artifact_key]["metaData"]["approvalState"] = "Approved"

    put_status, put_body = _put(
        base_url, token,
        f"/v1/aiservicedesk/user/data/projects/{project_id}",
        project_obj,
    )
    if put_status not in (200, 201, 204):
        err = put_body.decode("utf-8", errors="replace") if put_body else ""
        print(f"Failed to save {artifact_key} (HTTP {put_status}): {err}", file=sys.stderr)
        sys.exit(1)

    label = artifact_key.capitalize()
    if approve:
        print(f"{label} saved and approved on platform.")
    else:
        print(f"{label} saved to platform.")


def cmd_save_spec(spec_file: str, approve: bool = False):
    _save_artifact("spec", spec_file, approve)


def cmd_save_plan(plan_file: str, approve: bool = False):
    _save_artifact("plan", plan_file, approve)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DuploCloud ticket activation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-project", action="store_true",
                       help="Check project state and determine required action")
    group.add_argument("--list-workspaces", action="store_true",
                       help="Print current workspace ID from state")
    group.add_argument("--list-agents", action="store_true",
                       help="List agents for a workspace")
    group.add_argument("--list-execution-tickets", action="store_true",
                       help="List execution tickets for the active project")
    group.add_argument("--list-execution-tasks", action="store_true",
                       help="List execution tasks from the active project as JSON")
    group.add_argument("--get-task-by-index", action="store_true",
                       help="Resolve a 1-based task number to its name/title (outputs JSON)")
    group.add_argument("--check-task-ticket", action="store_true",
                       help="Check if a ticket exists for a specific task (exit 0=found, 1=not found)")
    group.add_argument("--create-execution-task-ticket", action="store_true",
                       help="Create a ticket for a specific execution task")
    group.add_argument("--create-ticket", action="store_true",
                       help="Create a spec or execution ticket")
    group.add_argument("--activate-ticket", action="store_true",
                       help="Activate an existing ticket from state")
    group.add_argument("--get-ticket-context", action="store_true",
                       help="Fetch past messages for the active ticket to restore context")
    group.add_argument("--get-ticket-status", action="store_true",
                       help="Print the current status of the active ticket")
    group.add_argument("--set-ticket-status", action="store_true",
                       help="Update the status of the active ticket")
    group.add_argument("--save-summary", action="store_true",
                       help="Save a summary markdown file to the active ticket")
    group.add_argument("--get-spec", action="store_true",
                       help="Fetch the current spec content from the platform")
    group.add_argument("--save-spec", action="store_true",
                       help="Save spec content from a local file to the platform")
    group.add_argument("--get-plan", action="store_true",
                       help="Fetch the current plan content from the platform")
    group.add_argument("--save-plan", action="store_true",
                       help="Save plan content from a local file to the platform")

    parser.add_argument("--workspace-id", help="Workspace ID (required with --list-agents and --create-ticket)")
    parser.add_argument("--agent-id", help="Agent ID (required with --create-ticket and --create-execution-task-ticket)")
    parser.add_argument("--task-id", help="Task name/UUID (required with --check-task-ticket and --create-execution-task-ticket)")
    parser.add_argument("--task-index", type=int, help="1-based task number (required with --get-task-by-index)")
    parser.add_argument("--stage-index", type=int, help="1-based stage number (optional with --get-task-by-index)")
    parser.add_argument("--type", dest="ticket_type",
                        choices=["spec_creation", "plan_execution"],
                        help="Ticket type (required with --create-ticket and --activate-ticket)")
    parser.add_argument("--summary-file", help="Path to summary markdown file (required with --save-summary)")
    parser.add_argument("--spec-file", help="Path to spec markdown file (required with --save-spec)")
    parser.add_argument("--plan-file", help="Path to plan markdown file (required with --save-plan)")
    parser.add_argument("--status", help="Ticket status: open|inProgress|waitingForUserInput|waitingForUserAgent|closed  (Note: --status closed requires --disposition)")
    parser.add_argument("--disposition", help="Required when --status closed: resolved|unResolved")
    parser.add_argument("--approve", action="store_true",
                        help='Mark the spec/plan as approved when saving (approvalState="Approved")')

    args = parser.parse_args()

    if args.check_project:
        cmd_check_project()
    elif args.list_workspaces:
        cmd_list_workspaces()
    elif args.list_agents:
        cmd_list_agents(args.workspace_id)
    elif args.list_execution_tickets:
        cmd_list_execution_tickets()
    elif args.list_execution_tasks:
        cmd_list_execution_tasks()
    elif args.get_task_by_index:
        if not args.task_index:
            parser.error("--get-task-by-index requires --task-index")
        cmd_get_task_by_index(args.task_index, args.stage_index)
    elif args.check_task_ticket:
        if not args.task_id:
            parser.error("--check-task-ticket requires --task-id")
        cmd_check_task_ticket(args.task_id)
    elif args.create_execution_task_ticket:
        if not args.task_id:
            parser.error("--create-execution-task-ticket requires --task-id")
        if not args.agent_id:
            parser.error("--create-execution-task-ticket requires --agent-id")
        cmd_create_execution_task_ticket(args.task_id, args.agent_id)
    elif args.create_ticket:
        if not args.ticket_type:
            parser.error("--create-ticket requires --type")
        if not args.agent_id:
            parser.error("--create-ticket requires --agent-id")
        cmd_create_ticket(args.ticket_type, args.agent_id, args.workspace_id)
    elif args.activate_ticket:
        if not args.ticket_type:
            parser.error("--activate-ticket requires --type")
        cmd_activate_ticket(args.ticket_type)
    elif args.save_summary:
        cmd_save_summary(args.summary_file)
    elif args.get_ticket_context:
        cmd_get_ticket_context()
    elif args.get_ticket_status:
        cmd_get_ticket_status()
    elif args.set_ticket_status:
        if not args.status:
            parser.error("--set-ticket-status requires --status")
        cmd_set_ticket_status(args.status, args.disposition)
    elif args.get_spec:
        cmd_get_spec()
    elif args.save_spec:
        if not args.spec_file:
            parser.error("--save-spec requires --spec-file")
        cmd_save_spec(args.spec_file, args.approve)
    elif args.get_plan:
        cmd_get_plan()
    elif args.save_plan:
        if not args.plan_file:
            parser.error("--save-plan requires --plan-file")
        cmd_save_plan(args.plan_file, args.approve)


if __name__ == "__main__":
    main()
