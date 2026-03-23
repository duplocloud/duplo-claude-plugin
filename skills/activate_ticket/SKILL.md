---
name: activate_ticket
description: Open or create a helpdesk ticket for the active project.
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Check project state:**

Read `.duplocloud/state.json`.

- If `project_id` or `workspace_id` is missing: tell the user:
  > "No active project found. Please run `/duplo:activate_project` first."
  Then stop.

Capture `workspace_id`, `project_id`, `project_name`, and `active_ticket_name` (may be absent).

**Step 2 — Resume or open new ticket?**

If `active_ticket_name` is present in state: ask the user:
> "Active ticket: **\<active_ticket_name\>**. Resume this ticket? (y/n)"
- **y** → skip to Step 5.
- **n** → clear `active_ticket_name` from consideration, continue to Step 3.

If absent: continue to Step 3.

**Step 3 — List existing tickets:**

Call `mcp__duplo-helpdesk__Ticket_list` with `tenantId = workspace_id`.

Filter the returned tickets to those belonging to the active project (where `projectId == project_id` or where the ticket's content/metadata references this project). If no filtering field is available, show all workspace tickets.

Show the user a numbered list of open/inProgress tickets plus a "Create new ticket" option:
```
Existing tickets:
1. <ticketName> — <title> (<status>)
2. ...
N+1. Create a new ticket
```

If there are no existing tickets, skip showing the list and go directly to Step 4 (create).

Ask:
> "Which ticket would you like to work on? (enter the number)"

- If the user picks an existing ticket: capture its `name` as `active_ticket_name`, then go to Step 5.
- If the user picks "Create new ticket": continue to Step 4.

**Step 4 — Create a new ticket:**

4a. Ask the user: "What is the title for this ticket?"

4b. List available agents:

Call `mcp__duplo-helpdesk__ServiceDeskAgents_get_allowed_agents` with `tenantId = workspace_id`.

Show the numbered agent list:
```
Available agents:
1. <name> (<id>)
2. ...
```

Ask: "Which agent should handle this ticket? (enter the number)"

4c. Create the ticket:

Call `mcp__duplo-helpdesk__Ticket_create` with `tenantId = workspace_id` and body:
```json
{
  "title": "<user-provided title>",
  "aiAgentId": "<selected agent id>",
  "tenantId": "<workspace_id>"
}
```

Capture the returned ticket's `name` as `active_ticket_name`.

4d. Set status to inProgress:

Call `mcp__duplo-helpdesk__Ticket_put_status` with `tenantId = workspace_id`, `ticketName = active_ticket_name`, and body:
```json
{ "status": "inProgress" }
```

**Step 5 — Save state and confirm:**

Write `.duplocloud/state.json` with the updated `active_ticket_name` (preserve existing `workspace_id`, `project_id`, `project_name`):
```json
{
  "workspace_id": "<workspace_id>",
  "project_id": "<project_id>",
  "project_name": "<project_name>",
  "active_ticket_name": "<active_ticket_name>"
}
```

Tell the user:
> "Ticket **\<active_ticket_name\>** is now active. You're ready to work!"
