---
name: task_ticket
description: Open or create a helpdesk ticket linked to a specific execution task in the active project.
disable-model-invocation: false
---

## Delegation to stage_tasks

This skill delegates to `skills/stage_tasks/SKILL.md`.

Read and follow `skills/stage_tasks/SKILL.md`:
- **If this is called directly** (not from `activate_project`): Follow **Steps 0–0b** to select a workspace/project with execution stages, then continue.
- **If called from `activate_project`**: The project is already active, so **Step 0a (project selection) is skipped** — go directly to Step 0b (load data).
- After project is resolved, proceed through **Steps 1–2** (list stages, select stage).
- Proceed through **Step 5** (Manage a task) to select a task.
- Proceed through **Step 5a** (Task action menu) and select **1. Create ticket for this task**.
- This delegates to Step 5b, which handles agent/persona selection and ticket creation.
- After completion, you may continue the `stage_tasks` flow or stop.


## Color Coding — HARD RULE

**Always prefix active workspace, project, or ticket names with a 🟢 emoji.**

---

Follow these steps in order.

---

## Step 0 — Verify active project

Read `.duplocloud/state.toon` and `.env`.

- If `project_id` or `workspace_id` is absent: tell the user:
  > "No active project. Please run `/duplo:activate_project` first."
  Then stop.

Capture `project_id`, `project_name`, `workspace_id`, `DUPLO_TOKEN`, `DUPLO_HELPDESK_URL`.

---

## Step 1 — Fetch execution stages

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

Extract `execution.stages` → `stages`.

If `stages` is empty or absent, tell the user:
> "No execution stages found for 🟢 **\<project_name\>**. Please generate execution stages first using `/duplo:ai_planner`."
Then stop.

---

## Step 2 — Select a stage (skip if called with active_stage already resolved)

Count total tasks across all stages.

**If total tasks > 10** — show stage list first:
```
Which stage would you like to work on?
1. <stage.title> — <stage.description> (<N> tasks)
2. ...
```
Ask: "Which stage? (number)"

Capture selected stage as `active_stage`.

**If total tasks ≤ 10** — show all tasks flat (skip to Step 3 using all tasks grouped by stage).

---

## Step 3 — Select a task

For each task in `active_stage`, check for an existing linked ticket:

Call `duplo-helpdesk::Ticket_get_project_task` with:
- `workspaceId = workspace_id`
- `projectId = project_id`
- `projectType = "plan_execution"`
- `taskId = <task.name>`

Display with ticket status if found:
```
Tasks in <active_stage.title>:
1. <task.title> — 🟢 Ticket: <ticket_title> (<status>)
2. <task.title> — No ticket yet
...
```

Ask: "Which task would you like to open a ticket for? (number)"

Capture selected task as `active_task` (with `name`, `title`, `description`) and any existing `ticket_name` if the task already has one.

---

## Step 4 — Existing ticket path

**If the task already has a linked ticket** (`ticket_name` is present):

Tell the user:
> "Task 🟢 **\<active_task.title\>** already has a ticket: **\<ticket_title\>** (\<status\>).
> 1. Open this ticket
> 2. Pick a different task"

- **1** → set `active_ticket_name` to the existing ticket name. Go to Step 6 (load past context).
- **2** → go back to Step 3.

---

## Step 5 — Create a new ticket for the task

### Step 5a — Pick an agent

Call `duplo-helpdesk::Workspaces_get_agents` with `id = workspace_id`.

Show a numbered list of agent names (no IDs or endpoints):
```
Which agent should handle this task ticket?
1. <name>
2. ...
```

### Step 5b — Select personas

Call `duplo-helpdesk::Workspaces_get_personas` with `id = workspace_id` (always fetch fresh from backend).

- **Call fails or returns empty list** → set `selected_persona_ids = []` and proceed.
- **Exactly one persona returned** → auto-select it, tell the user:
  > "Auto-selecting persona 🟢 **\<name\>** — it's the only one available."
  Set `selected_persona_ids = [<that persona's id>]`. Proceed.
- **Multiple personas** → show a numbered multi-select list using persona **name** only:
  ```
  Which personas should have access to this ticket? (enter comma-separated numbers, or press Enter to skip)
  1. <name>
  2. <name>
  ...
  ```
  Wait for input:
  - User enters numbers → capture those persona IDs as `selected_persona_ids`.
  - User presses Enter / skips → `selected_persona_ids = []`.

### Step 5c — Create the ticket

**HARD RULE: `taskId` MUST be inside `originContext.metadata`. Never place `taskId` as a top-level field. The ticket will NOT be linked to the task if the structure is wrong.**

Call `duplo-helpdesk::Ticket_create` with `workspaceId = workspace_id` and body:
```json
{
  "title": "<active_task.title>",
  "aiAgentId": "<selected agent id>",
  "workspaceId": "<workspace_id>",
  "origin": "api",
  "ticketContextForAgent": {
    "personaIds": ["<selected_persona_ids>"]
  },
  "originContext": {
    "type": "Project",
    "id": "<project_id>",
    "subType": "execution",
    "metadata": {
      "taskId": "<active_task.name>",
      "projectType": "plan_execution"
    }
  }
}
```

Omit `ticketContextForAgent` entirely if `selected_persona_ids` is empty.

Capture the returned ticket `name` as `active_ticket_name`.

Tell the user:
> "Ticket created for task 🟢 **\<active_task.title\>**."

---

## Step 6 — Load past context

Call `duplo-helpdesk::Ticket_get_messages` with `workspaceId = workspace_id`, `ticketName = active_ticket_name`.

- If messages are returned: read them to restore context of prior work on this task.
- If empty: proceed without prior context.

---

## Step 7 — Save state

Write `.duplocloud/state.toon` silently, preserving `project_id`, `project_name`, and `workspace_id`:
```
workspace_id: <workspace_id>
project_id: <project_id>
project_name: <project_name>
active_ticket_name: <active_ticket_name>
```

---

## Step 7b — Ticket lifecycle rules

**HARD RULES — apply for the entire duration this ticket is active:**

- **On creation:** Leave ticket in `open` state. Do NOT call `Ticket_put_status` automatically.
- **When the user sends their first message or activity begins:** Call `duplo-helpdesk::Ticket_put_status` with `{ "status": "inProgress" }` before forwarding the message to the agent.
- **When the user confirms changes, says they are done, or explicitly finishes the activity on this task:** Call `duplo-helpdesk::Ticket_put_status` with `{ "status": "closed", "disposition": "resolved" }`. Remove `active_ticket_name` from state. Tell the user the ticket has been closed.

Do NOT close the ticket automatically for any other reason. Only close when the user explicitly confirms they are done with the activity on this ticket.

---

## Step 8 — Confirm agent and hand off

Call `duplo-helpdesk::Workspaces_get_agents` with `id = workspace_id`.

Resolve the agent name from the ticket's `aiAgentId`.

Tell the user:
> "Ticket 🟢 **\<ticket_title\>** is ready for task **\<active_task.title\>**. **\<agent name\>** will respond to your messages.
> 
> Task description: \<active_task.description\>"

The ticket is now active. All subsequent user messages are forwarded to the agent per the standard agent communication rules in CLAUDE.md.
