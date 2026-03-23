---
name: activate_project
description: Activate a DuploCloud project context.
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Check current state:**

Read `.duplocloud/state.json` if it exists.

- If `project_id` is present: ask the user:
  > "Active project: **\<project_name\>**. Continue with this project? (y/n)"
  - **y** → show a brief summary of the active project and stop.
  - **n** → continue to Step 2.
- If absent or file missing: continue to Step 2.

**Step 2 — List projects:**

Call `mcp__duplo-helpdesk__Projects_list` with no filter.

If the call fails with an auth or connection error, stop and tell the user:
> "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` is exported and the server is running."

Show the user a numbered list of active projects. Write each item clearly:
```
1. <name> — <description or "no description">
2. <name> — ...
```

If the list is empty: tell the user "No projects found. Please create a project in the DuploCloud portal first." and stop.

**Step 3 — User selects project:**

Ask:
> "Which project would you like to activate? (enter the number)"

Wait for the user's selection (number N). Resolve to the Nth project from the list returned in Step 2.

Capture from the selected project object:
- `id` → `project_id`
- `name` → `project_name`
- `workspaceId` → `workspace_id`

If `workspaceId` is absent from the response, ask the user:
> "Could not find a workspace ID for this project. Please enter the workspace/tenant ID:"

**Step 4 — Save state:**

Write `.duplocloud/state.json` with:
```json
{
  "workspace_id": "<workspace_id>",
  "project_id": "<project_id>",
  "project_name": "<project_name>"
}
```

Create the `.duplocloud/` directory first if it does not exist.

**Step 5 — Confirm:**

Tell the user:
> "Project **\<project_name\>** activated. Run `/duplo:activate_ticket` to open or create a ticket."
