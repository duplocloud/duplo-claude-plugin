---
name: activate_ticket
description: Open or resume a helpdesk ticket. Tickets are independent of projects.
disable-model-invocation: false
---

Follow these steps in order:

---

## Step 1 — Resolve workspace

Read `.duplocloud/state.json` (file may not exist). Note `workspace_id`, `active_ticket_name`, `project_id`, `project_name` if present.

Call `mcp__duplo-helpdesk__Workspaces_get_available` to get the list of available workspaces.

- If the call returns an empty list, tell the user:
  > "It looks like you don't have any workspaces set up yet. Please create one in the DuploCloud portal first."
  Then stop.

- If only **one** workspace is returned: auto-select it silently. Capture its `id` as `workspace_id`.

- If **multiple** workspaces and `workspace_id` is present in state:
  - Check whether that `workspace_id` exists in the returned list.
  - If **found**: ask the user:
    > "You're currently connected to **\<workspace name\>**. Would you like to continue with this workspace? (y/n)"
    - **y** → use this workspace. Proceed to Step 1b.
    - **n** → show the workspace list (Step 1a).
  - If **not found**: tell the user the previously saved workspace is no longer available, then show the workspace list (Step 1a).

- If `workspace_id` is absent from state: show the workspace list (Step 1a).

### Step 1a — Choose a workspace

Show a numbered list using only the workspace **name** (no raw IDs):
```
Here are your available workspaces:
1. <name>
2. ...
```
Ask: "Which workspace would you like to use?"

Capture the selected workspace's `id` as `workspace_id` (store internally, do not show to the user).

If the newly selected workspace **differs** from what was in state: **clear `active_ticket_name`** (the old ticket belongs to the old workspace).

### Step 1b — Sync tickets to state

After workspace is resolved (whether auto-selected or chosen via Step 1a):

Call `mcp__duplo-helpdesk__Ticket_list` with `workspaceId = workspace_id`.

Store the results in `.duplocloud/state.json` under a `tickets` field:
```json
"tickets": [
  { "name": "<ticketName>", "title": "<title>", "status": "<status>", "aiAgentId": "<aiAgentId or null>" }
]
```

Write the updated state silently. Step 3 will use this cached list.

---

## Step 2 — Resume or open a ticket?

If `active_ticket_name` is present in state (and workspace has not changed), look up the ticket title from the cached `tickets` list. Ask the user:
> "You were last working on **\<title\>**. Would you like to pick up where you left off? (y/n)"
- **y** → go to Step 6 (load past context).
- **n** → continue to Step 3.

If absent: continue to Step 3.

---

## Step 3 — Choose an existing ticket or create a new one

Use the cached `tickets` array from state. Filter to `open` or `inProgress` status only.

Display using the ticket **title** as the primary label. Map status values to friendly labels: `open` → "Open", `inProgress` → "In Progress". Do not show raw ticket name IDs.

```
Here are your open tickets:
1. <title> — <friendly status>
2. ...
N+1. Start a new ticket
```

If there are no open tickets, skip the list and go directly to Step 4.

Ask: "Which would you like to work on?"

- Existing ticket selected → capture its `name` as `active_ticket_name`, go to Step 5.
- "Start a new ticket" → continue to Step 4.

---

## Step 4 — Create a new ticket

### Step 4a — Check for execution tasks (only if project is active)

If `project_id` is present in state:

Call `mcp__duplo-helpdesk__Projects_get` with `id = project_id`.

From the response extract:
- `has_execution_tasks` = true if any stage in `execution.stages` has tasks

If `has_execution_tasks` is true, ask the user:
> "Your project **\<project_name\>** has tasks ready to execute. What would you like to do?
> 1. Work on a project task
> 2. Open a standalone ticket"

- User picks **1** → go to Step 4b.
- User picks **2** → go to Step 4c.

If `has_execution_tasks` is false, or `project_id` is absent: go to Step 4c.

---

### Step 4b — Pick a project task

Using the stages data from the project response, count total tasks across all stages.

**If total tasks > 10** — first ask user to select a stage (show name and task count, no IDs):
```
Which area would you like to work on?
1. <stage_name> — <stage_description> (<N> tasks)
2. ...
```
Then show tasks within the chosen stage:
```
Which task would you like to work on?
1. <task_title> — <friendly ticket status or "No ticket yet">
2. ...
```

**If total tasks ≤ 10** — show all tasks flat:
```
Which task would you like to work on?
1. <task_title> (<stage_name>) — <friendly ticket status or "No ticket yet">
2. ...
```

Wait for task selection. Capture `task_id` (the task's `name` UUID, stored internally) and `task_title`.

**If the task already has a ticket** (`ticket_name` present in the task data):
- Set `active_ticket_name` to that ticket name.
- Go to Step 5.

**If no ticket yet**: continue to Step 4d (select agent), then Step 4e.

---

### Step 4c — Name the new ticket

Ask the user: "What should we call this ticket?"

---

### Step 4d — Pick an agent

Call `mcp__duplo-helpdesk__Workspaces_get_agents` with `id = workspace_id`.

Show a numbered list using agent **name** only (no IDs or endpoints):
```
Which agent should handle this ticket?
1. <name>
2. ...
```

---

### Step 4e — Create the ticket

**Standalone ticket** — call `mcp__duplo-helpdesk__Ticket_create` with `workspaceId = workspace_id` and body:
```json
{
  "title": "<user-provided title>",
  "aiAgentId": "<selected agent id>",
  "workspaceId": "<workspace_id>",
  "origin": "api"
}
```

**Spec or plan creation ticket** (when `project_ticket_type` is set) — call `mcp__duplo-helpdesk__Ticket_create` with `workspaceId = workspace_id` and body:
```json
{
  "title": "<project_name> — <spec_creation or plan_creation>",
  "aiAgentId": "<selected agent id>",
  "workspaceId": "<workspace_id>",
  "origin": "api",
  "project": {
    "id": "<project_id>",
    "type": "<project_ticket_type>"
  }
}
```

**Execution task ticket** — call `mcp__duplo-helpdesk__Ticket_create` with `workspaceId = workspace_id` and body:
```json
{
  "title": "<task_title>",
  "aiAgentId": "<selected agent id>",
  "workspaceId": "<workspace_id>",
  "origin": "api",
  "project": {
    "id": "<project_id>",
    "type": "plan_execution",
    "taskId": "<task_id>"
  }
}
```

Capture the returned ticket's `name` as `active_ticket_name` (stored internally).

---

## Step 5 — Mark ticket as in progress

Call `mcp__duplo-helpdesk__Ticket_put_status` with `workspaceId = workspace_id`, `ticketName = active_ticket_name`, and body:
```json
{ "status": "inProgress" }
```

This is safe to call unconditionally — the backend accepts it even if the ticket is already in progress.

---

## Step 6 — Load past context

Call `mcp__duplo-helpdesk__Ticket_get_messages` with `workspaceId = workspace_id`, `ticketName = active_ticket_name`.

- If messages are returned: read them carefully. They contain the full conversation history — prior user messages, assistant responses, decisions made, and work done. Use this to restore your understanding of where work left off before responding to the user.
- If no messages or empty: proceed without prior context.

---

## Step 7 — Save state

Write `.duplocloud/state.json` silently, preserving any existing `project_id` and `project_name` fields:
```json
{
  "workspace_id": "<workspace_id>",
  "project_id": "<project_id if present, else omit>",
  "project_name": "<project_name if present, else omit>",
  "active_ticket_name": "<active_ticket_name>",
  "tickets": [...]
}
```

---

## Step 7b — Confirm or change the agent

Call `mcp__duplo-helpdesk__Workspaces_get_agents` with `id = workspace_id`.

From the ticket data (captured in Step 3 or Step 4e), note the `aiAgentId`.

**Context:** Once a ticket is active, the assigned agent handles all your messages. Claude Code only manages ticket lifecycle (activation, creation, closing, spec and plan writing).

**If the ticket already has an agent assigned:**

Resolve the agent name from the agents list. Tell the user:
> "**\<agent name\>** is assigned to this ticket and will respond to your messages. Would you like to continue with this agent or switch?
> 1. Continue with **\<agent name\>**
> 2. Switch agent"

- If user picks **1**: keep current agent. Stop here.
- If user picks **2**: show the agent list (Step 7b-select).

**If no agent is assigned:**

Tell the user: "No agent is assigned to this ticket yet. Please pick one to handle your messages:"
Go to Step 7b-select.

### Step 7b-select — Pick an agent

Show agent names only (no IDs or endpoints):
```
1. <name>
2. ...
```
Ask: "Which agent should handle your messages?"

Call `mcp__duplo-helpdesk__Ticket_put_assignee` with `workspaceId = workspace_id`, `ticketName = active_ticket_name`, `agentId = <selected agent id>`.

Tell the user: "**\<agent name\>** is now assigned."

Then tell the user:
> "Ticket **\<title\>** is ready. **\<agent name\>** will respond to your messages."
