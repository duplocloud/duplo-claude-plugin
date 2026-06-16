---
name: add_task
description: Add a new execution task to a stage in the active project.
disable-model-invocation: false
---

## Delegation to stage_tasks

This skill delegates to `skills/stage_tasks/SKILL.md`.

Read and follow `skills/stage_tasks/SKILL.md`:
- **If this is called directly** (not from `activate_project`): Follow **Steps 0–0b** to select a workspace/project with execution stages, then continue.
- **If called from `activate_project`**: The project is already active, so **Step 0a (project selection) is skipped** — go directly to Step 0b (load data).
- After project is resolved, proceed through **Steps 1–2** (list stages, select stage).
- Jump to **Step 4** (Add a new task to stage) to add your task.
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

Extract:
- `execution.stages` → `stages`
- `execution.version` → `execution_version`

If `stages` is empty or absent, tell the user:
> "No execution stages found for 🟢 **\<project_name\>**. Please generate execution stages first using `/duplo:ai_planner`."
Then stop.

---

## Step 2 — Select a stage

Display:
```
Project: 🟢 <project_name>

Execution Stages:
1. <stage.title> — <stage.description> (<N> tasks)
2. ...
```

Ask: "Which stage would you like to add a task to? (number)"

Capture the selected stage as `active_stage` (with `name`, `title`, `description`, and full `tasks` array including each task's `name`, `title`, `description`, `version`).

---

## Step 3 — Collect task details

Ask: "What is the title of the new task?"

Wait for response. Capture as `new_task_title`.

Ask: "Describe what this task should do:"

Wait for response. Capture as `new_task_description`.

---

## Step 4 — Generate task UUID

Generate a UUID for the new task:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

Capture output as `new_task_id`.

---

## Step 5 — Re-fetch for latest version

Re-fetch the project to get the most up-to-date `execution.version` and the current task list for `active_stage`:

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

Update `execution_version` and re-capture the existing tasks for `active_stage` (match by `active_stage.name`).

Build the full `tasksToAddOrUpdate` array by including **all existing tasks** (with their `name`, `title`, `description`, `version`) plus the new task entry at the end:
```json
{ "name": "<new_task_id>", "title": "<new_task_title>", "description": "<new_task_description>" }
```

---

## Step 6 — Save the task

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "version": "<execution_version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "description": "<active_stage.description>",
      "tasksToAddOrUpdate": [
        { "name": "<task.name>", "title": "<task.title>", "description": "<task.description>", "version": "<task.version>" },
        ...existing tasks...,
        { "name": "<new_task_id>", "title": "<new_task_title>", "description": "<new_task_description>" }
      ]
    }
  ]
}
```

Tell the user: "Task **\<new_task_title\>** added to stage **\<active_stage.title\>**."

---

## Step 7 — Show updated task list

Re-fetch the project: call `duplo-helpdesk::Projects_get` with `id = project_id`.

Find `active_stage` by name in the updated stages. Display:
```
Tasks in <active_stage.title>:
1. <task.title> — <task.description>
2. ...
```

Ask:
> "Would you like to add another task to this stage, pick a different stage, or open a ticket for one of these tasks?
> 1. Add another task to this stage
> 2. Pick a different stage
> 3. Open a ticket for a task (runs /duplo:task_ticket)
> 4. Done"

- **1** → go back to Step 3.
- **2** → go back to Step 2.
- **3** → read and follow `skills/task_ticket/SKILL.md` with `project_id`, `workspace_id`, and `active_stage` already resolved (skip to its Step 2 to pick a task).
- **4** → stop.
