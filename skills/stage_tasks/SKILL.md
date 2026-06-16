---
name: stage_tasks
description: Manage execution stages and tasks — list, add, edit, delete, and create tickets for tasks.
disable-model-invocation: false
---

## Color Coding — HARD RULE

**Always prefix active workspace, project, or ticket names with a 🟢 emoji.**

---

Follow these steps in order.

---

## Step 0 — Resolve workspace and project (conditional)

Read `.duplocloud/state.toon` and `.env`.

Capture `workspace_id`, `project_id`, `project_name` if present.

**Case A: Project is already active** (`project_id` present in state)
- Skip to **Step 0b** (Load project data). This is the path when called from `activate_project` flow.

**Case B: No active project** (`project_id` absent)
- Follow **Step 0a** (Select project), then proceed to **Step 0b**.

---

## Step 0a — List and select project

Call `duplo-helpdesk::Workspaces_get_available` to get available workspaces.

If no workspaces, tell the user:
> "No workspaces available. Please create one in the DuploCloud portal first."
Then stop.

If only one workspace, auto-select and capture its `id` as `workspace_id`. Tell the user:
> "Auto-selecting 🟢 **\<workspace name\>** — it's the only workspace available."

If multiple workspaces, show a numbered list and ask: "Which workspace?"
Capture the selected workspace's `id` as `workspace_id`.

Call `duplo-helpdesk::Projects_list` with `workspaceId = workspace_id`.

If no projects, tell the user:
> "No projects found in this workspace. Please create one in the DuploCloud portal first."
Then stop.

Filter projects to those with execution stages:
- Call `duplo-helpdesk::Projects_get` with `id = <each project>`.
- Keep only projects where `execution.stages` is non-empty and has at least one stage with tasks.

If no projects with execution stages, tell the user:
> "No projects with execution stages found. Please run `/duplo:ai_planner` on a project to generate stages and tasks first."
Then stop.

Show a numbered list of projects with execution stages (name and task count):
```
Projects with execution stages:
1. <name> — <N> total tasks
2. ...
```

Ask: "Which project would you like to work on?"

Capture the selected project's `id` as `project_id` and `name` as `project_name`.

---

## Step 0b — Load project data

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

Extract and store:
- `execution.stages` → `stages`
- `execution.version` → `execution_version`

Call `duplo-helpdesk::Ticket_list` with `workspaceId = workspace_id`.

From the returned tickets, build `task_ticket_map` keyed by `metadata.taskId` using only tickets where all of the following are true:
- `originContext.type` is `Project`
- `originContext.id` equals `project_id`
- `originContext.metadata.projectType` equals `plan_execution`
- `originContext.metadata.taskId` is present

For each mapped ticket, capture:
- `ticket_name`
- `ticket_title`
- `ticket_status`

If `stages` is empty or absent, tell the user:
> "No execution stages found for 🟢 **\<project_name\>**. Please generate execution stages first using `/duplo:ai_planner`."
Then stop.

Save state silently:
```
workspace_id: <workspace_id>
project_id: <project_id>
project_name: <project_name>
```

Proceed to **Step 1**.

---

## Step 1 — List execution stages

Display:
```
Project: 🟢 <project_name>

Execution Stages:
1. <stage.title> — <stage.description> (<N> tasks)
2. ...
```

Ask: "Which stage would you like to work on? (number, or 'done')"

- **done** → stop.
- **number** → capture the selected entry as `active_stage` (with `name`, `title`, `description`, and full `tasks` array where each task has `name`, `title`, `description`, `version`). Proceed to Step 2.

---

## Step 2 — Stage action menu

Display the stage description in a hard frame:
```
╔═══════════════════════════════════════════════════════╗
║ Stage: 🟢 <active_stage.title>                        ║
╠═══════════════════════════════════════════════════════╣
║ <active_stage.description>                            ║
╚═══════════════════════════════════════════════════════╝
```

Ask:
> "What would you like to do with this stage?
> 1. Edit stage name / description
> 2. Add a new task
> 3. Manage a task
> 4. Back to stage list
> 5. Done"

- **1** → go to Step 3.
- **2** → go to Step 4.
- **3** → go to Step 5.
- **4** → go to Step 1.
- **5** → stop.

---

## Step 3 — Edit stage

Tell the user the current values:
> "Current name: **\<active_stage.title\>**  
> Current description: \<active_stage.description\>"

Ask: "New name? (press Enter to keep current)"
Ask: "New description? (press Enter to keep current)"

Apply only the values the user provided. Keep unchanged fields as-is.

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Update `execution_version` and re-capture `active_stage` tasks.

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<updated title>",
      "description": "<updated description>",
      "tasksToAddOrUpdate": [
        { "name": "<task.name>", "title": "<task.title>", "description": "<task.description>", "version": "<task.version>" }
      ]
    }
  ]
}
```

Tell the user: "Stage updated." Go back to Step 2.

---

## Step 4 — Add a new task to stage

Ask: "Task title:"
Ask: "Task description:"

Generate a UUID:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```
Capture as `new_task_id`.

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Update `execution_version` and re-capture current tasks for `active_stage`.

Build `tasksToAddOrUpdate`: all existing tasks (with `name`, `title`, `description`, `version`) plus the new entry:
```json
{ "name": "<new_task_id>", "title": "<user title>", "description": "<user description>" }
```

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "description": "<active_stage.description>",
      "tasksToAddOrUpdate": [ ...existing tasks..., { "name": "<new_task_id>", "title": "<title>", "description": "<description>" } ]
    }
  ]
}
```

Tell the user: "Task **\<title\>** added." Go back to Step 2.

---

## Step 5 — Manage a task

For each task in `active_stage.tasks`, look up an existing linked ticket in `task_ticket_map` using `task.name`.

Display:
```
Tasks in <active_stage.title>:
1. <task.title> — 🟢 Ticket: <ticket_title> (<status>)
2. <task.title> — No ticket
...
```

Ask: "Which task? (number, or 'back')"

- **back** → go to Step 2.
- **number** → capture selected task as `active_task` (with `name`, `title`, `description`, `version`) and `task_ticket_name` / `task_ticket_status` if a ticket was found. Proceed to Step 5a.

Whenever the project is re-fetched later in this flow, also refresh `task_ticket_map` from `Ticket_list` before showing task menus again.

---

## Step 5a — Task action menu

Ask:
> "What would you like to do with task 🟢 **\<active_task.title\>**?
> 1. Create ticket for this task
> 2. Move to a different stage
> 3. Edit name / description
> 4. Delete task
> 5. Back to task list"

- **1** → go to Step 5b.
- **2** → go to Step 5c.
- **3** → go to Step 5d.
- **4** → go to Step 5e.
- **5** → go to Step 5.

---

## Step 5b — Create ticket for task

**Block rule:** If the task already has a ticket with status `open`, `inProgress`, or `closed`, tell the user:
> "This task already has a ticket **\<ticket_title\>** (\<status\>). A new ticket cannot be created."
Go back to Step 5a.

If no ticket exists, or the existing ticket has status `resolved` or `cancelled`: proceed.

Delegate to `skills/task_ticket/SKILL.md`:
- Pass `workspace_id`, `project_id`, `active_task` (with `name`, `title`, `description`), and `active_stage`.
- Instruct: skip Steps 0–4, start directly at **Step 5** (persona selection in the original skill numbering — the ticket creation sub-flow).

After `task_ticket` returns (ticket created), go back to Step 5.

---

## Step 5c — Move task to a different stage

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Update `stages` and `execution_version`.

List the other stages (exclude `active_stage`):
```
Move to which stage? (or 'back' to cancel)
1. <stage.title>
2. ...
N. Back
```

Wait for selection:
- **back** or **N** → go back to Step 5a without making any changes.
- **number** → capture as `target_stage` (with `name`, `title`, `description`, `tasks`).

**Remove from current stage:** Build `tasksToAddOrUpdate` for `active_stage` containing all tasks **except** `active_task`.

**Add to target stage:** Build `tasksToAddOrUpdate` for `target_stage` containing all its current tasks plus `active_task` (without `version` field for the moved task).

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "description": "<active_stage.description>",
      "tasksToAddOrUpdate": [ ...all tasks except active_task... ]
    },
    {
      "name": "<target_stage.name>",
      "title": "<target_stage.title>",
      "description": "<target_stage.description>",
      "tasksToAddOrUpdate": [ ...target stage tasks..., { "name": "<active_task.name>", "title": "<active_task.title>", "description": "<active_task.description>" } ]
    }
  ]
}
```

Tell the user: "Task **\<active_task.title\>** moved to stage **\<target_stage.title\>**." Go back to Step 5.

---

## Step 5d — Edit task name / description

Tell the user the current values:
> "Current name: **\<active_task.title\>**  
> Current description: \<active_task.description\>"

Ask: "New name? (press Enter to keep current)"
Ask: "New description? (press Enter to keep current)"

Apply only provided values.

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Update `execution_version` and re-capture all tasks for `active_stage`.

Build `tasksToAddOrUpdate`: all tasks for `active_stage`, replacing `active_task` with the updated values.

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "description": "<active_stage.description>",
      "tasksToAddOrUpdate": [ ...all tasks with active_task updated... ]
    }
  ]
}
```

Tell the user: "Task updated." Update `active_task` with the new values. Go back to Step 5a.

---

## Step 5e — Delete task

Ask for confirmation:
> "Are you sure you want to delete task **\<active_task.title\>**? This cannot be undone. (y/n)"

- **n** → go back to Step 5a.
- **y** → proceed.

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Update `execution_version` and re-capture tasks for `active_stage`.

Build `tasksToAddOrUpdate`: all tasks for `active_stage` **except** `active_task`.

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "description": "<active_stage.description>",
      "tasksToAddOrUpdate": [ ...all tasks except active_task... ]
    }
  ]
}
```

Tell the user: "Task **\<active_task.title\>** deleted." Go back to Step 5.
