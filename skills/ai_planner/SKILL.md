---
name: ai_planner
description: AI-assisted project planning — single ticket per project, phases spec→plan→execution managed by plugin, canvas files maintained by agent.
disable-model-invocation: false
---

Follow these steps in order.

**HARD RULE: Every conversation related to a project — spec, plan, or execution tasks — must happen inside the AI Planner ticket. Never create separate tickets for these phases.**

---

## Overview

All planning for a project happens in a single **AI Planner ticket**. The plugin manages phase transitions (spec → plan → execution) by passing `project_context` on each message. The agent writes canvas files (`canvas-documents/spec.md`, `canvas-documents/plan.md`, `canvas-documents/execution_tasks.json`). The plugin saves confirmed content back to the project via `Projects_patch`.

**Phases:**
1. **Spec** — agent writes `canvas-documents/spec.md`
2. **Plan** — agent reads spec, writes `canvas-documents/plan.md`
3. **Execution** — agent reads plan, writes `canvas-documents/execution_tasks.json` and generates stages

**Platform context rules (always include `project_id`):**
- Spec phase: `ticket_type: "spec_creation"`, `project_id`
- Plan phase: `ticket_type: "plan_creation"`, `project_id`, `spec_content`
- Execution phase: `ticket_type: "plan_execution"`, `project_id`, `spec_content`, `plan_content`

---

## Step 0 — Verify project is active

Read `.duplocloud/state.toon`.

- If `project_id` or `workspace_id` is absent: stop and tell the user:
  > "No active project. Please run `/duplo:activate_project` first."

Capture `project_id`, `workspace_id`, `project_name`.

Read env values:
```bash
bash -c 'source .env 2>/dev/null; printf "TOKEN=%s\nURL=%s" "$DUPLO_TOKEN" "$DUPLO_HELPDESK_URL"'
```

---

## Step 1 — Find or create the AI Planner ticket

Call `duplo-helpdesk::Ticket_list` with `workspaceId = workspace_id`.

Look for an existing `open` or `inProgress` ticket whose `project.id == project_id`.

- **Found** → set `active_ticket_name`, call `duplo-helpdesk::Ticket_put_status` to mark `inProgress`, save state.
- **Not found** → ask the user for an agent, then call `duplo-helpdesk::Ticket_create`:
  ```json
  {
    "title": "<project_name> AI Planner",
    "aiAgentId": "<selected agent id>",
    "workspaceId": "<workspace_id>",
    "origin": "api",
    "project": { "id": "<project_id>" }
  }
  ```
  Set `active_ticket_name` and save state.

---

## Step 2 — Detect current phase and artifact state

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

Extract:
- `spec.content` → `spec_content`
- `spec.metaData.approvalState` → `spec_state` (`"Approved"` / `"Draft"` / `"Not started"`)
- `plan.content` → `plan_content`
- `plan.metaData.approvalState` → `plan_state`
- `execution.stages` → `execution_stages`
- `execution.version` → `execution_version`

Determine current phase:
| State | Phase |
|---|---|
| `spec_content` blank | **spec** |
| `spec_content` present, `plan_content` blank | **plan** |
| `plan_content` present, `execution_stages` empty | **execution** |
| `execution_stages` present | **stages ready** → skip to Step 6 |

**Artifact state awareness:**
- If entering spec phase and `spec_content` is present (draft): tell the user:
  > "You have a spec draft (status: **\<spec_state\>**). Would you like to edit it, confirm it, or start fresh? (edit / confirm / restart)"
  - **edit** → proceed to Step 3 in edit mode (send current `spec_content` as context)
  - **confirm** → go directly to confirm action in Step 3
  - **restart** → proceed to Step 3 with blank context
- If entering plan phase and `plan_content` is present (draft): tell the user:
  > "You have a plan draft (status: **\<plan_state\>**). Would you like to edit it, confirm it, or start fresh? (edit / confirm / restart)"
  - Same logic, proceed to Step 4 accordingly.
- Users can explicitly request to change a confirmed artifact at any time. If the user says "edit spec", "change plan", "redo execution", etc., jump to the appropriate step regardless of approval state.

---

## Step 3 — Spec phase

If not already shown: tell the user:
> "Let's define the spec. Describe what you'd like to achieve:"

Send the user's input via `duplo-helpdesk::Ticket_send_message_streaming`:
```json
{
  "workspaceId": "<workspace_id>",
  "ticketName": "<active_ticket_name>",
  "content": "<user input>",
  "message_mode": 0,
  "data": {},
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "spec_creation",
      "project_id": "<project_id>"
    }
  }
}
```

Apply agent availability hard rule. From the SSE response:
- Concatenate all `text_delta` values → assemble and display the agent's full text verbatim.
- Look for a `present_file` event where `path` ends with `spec.md` → capture its `content` as `spec_draft`.

Ask:
> "Would you like to refine the spec or confirm it? (refine / confirm)"

- **refine** → send follow-up with same `project_context`, display response, re-capture `spec_draft`. Repeat.
- **confirm** → save:
  1. Use `spec_draft` (from `present_file`) if captured; otherwise use the assembled `text_delta` text.
  2. Call `duplo-helpdesk::Projects_patch` with body `{ "spec": { "content": "<spec_draft>" } }`
  3. Tell the user: "Spec saved."
  4. Proceed to Step 4.

---

## Step 4 — Plan phase

Fetch updated project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Capture `spec_content`, `plan_content`, `plan_state`.

Tell the user:
> "Now let's build the plan. Describe your approach or say 'generate from spec':"

Send the user's input via `duplo-helpdesk::Ticket_send_message_streaming`:
```json
{
  "workspaceId": "<workspace_id>",
  "ticketName": "<active_ticket_name>",
  "content": "<user input>",
  "message_mode": 0,
  "data": {},
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "plan_creation",
      "project_id": "<project_id>",
      "spec_content": "<spec_content>"
    }
  }
}
```

Apply agent availability hard rule. From the SSE response:
- Concatenate all `text_delta` values → assemble and display the agent's full text verbatim.
- Look for a `present_file` event where `path` ends with `plan.md` → capture its `content` as `plan_draft`.

Ask:
> "Would you like to refine the plan or confirm it? (refine / confirm)"

- **refine** → send follow-up with same `project_context`, display response, re-capture `plan_draft`. Repeat.
- **confirm** → save:
  1. Use `plan_draft` (from `present_file`) if captured; otherwise use the assembled `text_delta` text.
  2. Call `duplo-helpdesk::Projects_patch` with body `{ "plan": { "content": "<plan_draft>" } }`
  3. Tell the user: "Plan saved."
  4. Proceed to Step 5.

---

## Step 5 — Execution phase

Fetch updated project: call `duplo-helpdesk::Projects_get` with `id = project_id`. Capture `spec_content` and `plan_content`.

Tell the user:
> "Generating execution stages from the plan..."

Send via `duplo-helpdesk::Ticket_send_message_streaming`:
```json
{
  "workspaceId": "<workspace_id>",
  "ticketName": "<active_ticket_name>",
  "content": "Based on the confirmed plan, generate execution stages and tasks for this project.",
  "message_mode": 0,
  "data": {},
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "plan_execution",
      "project_id": "<project_id>",
      "spec_content": "<spec_content>",
      "plan_content": "<plan_content>"
    }
  }
}
```

Apply agent availability hard rule. From the SSE response:
- Concatenate all `text_delta` values → assemble and display the agent's full text verbatim.
- Look for a `present_file` event where `path` ends with `execution_tasks.json` → capture its `content` as `execution_draft`.

If no `present_file` was captured:
> "The agent did not return execution tasks. Would you like to try again? (y/n)"
- **y** → re-send the same message. Repeat this step.
- **n** → stop.

Ask the user:
> "Would you like to refine the execution tasks or confirm them? (refine / confirm)"

- **refine** → send follow-up with same `project_context`, display response, re-capture `execution_draft`. Repeat.
- **confirm** → save the execution stages:
  1. Re-fetch project: call `duplo-helpdesk::Projects_get` to get `execution.version`.
  2. Parse `execution_draft` JSON — it has a `stages` array. Each stage has `id`, `name`, `description`, `tasks[]` where each task has `id`, `title`, `description`.
  3. Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id`:
     ```json
     {
       "version": "<execution.version>",
       "stageToAddOrUpdate": [
         {
           "name": "<stage.id>",
           "title": "<stage.name>",
           "description": "<stage.description>",
           "tasksToAddOrUpdate": [
             { "name": "<task.id>", "title": "<task.title>", "description": "<task.description>" }
           ]
         }
       ]
     }
     ```
  4. Tell the user: "Execution stages saved."
  5. Proceed to Step 6.

---

## Step 6 — List stages

Re-fetch if needed: call `duplo-helpdesk::Projects_get` with `id = project_id`.

Display:
```
Project: <project_name>
Progress: <project.progress>%

Execution Stages:
1. <stage.title> — <N> tasks
2. ...
```

Ask:
> "Which stage would you like to work on? (number, or 'done')"

- **done** → stop.
- **number** → capture `active_stage`. Proceed to Step 7.

---

## Step 7 — List tasks in stage

For each task in `active_stage.tasks`, check for an existing ticket:
Call `duplo-helpdesk::Ticket_get_project_task` with `workspaceId`, `projectId = project_id`, `projectType = "plan_execution"`, `taskId = <task.name>`.

Display:
```
Tasks in <stage.title>:
1. <task.title> — <ticket title or "No ticket">
2. ...
N+1. Add a new task
```

- **existing task** → capture as `active_task`. Proceed to Step 8.
- **Add a new task** → proceed to Step 8b.

---

## Step 8 — Task action

Ask:
> "For **\<active_task.title\>**:
> 1. Open a ticket for this task
> 2. Go back to stage list"

- **1** → follow `skills/activate_ticket/SKILL.md` from Step 4d using `task_id = active_task.name`, `task_title = active_task.title`, `project_ticket_type = "plan_execution"`. Ticket is linked to the task, mirroring applies.
- **2** → go back to Step 6.

---

## Step 8b — Add new task to stage

Ask for title and description.

Generate a UUID:
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

Re-fetch project to get `execution.version` and all existing tasks in `active_stage` with their `name`, `title`, `description`, `version`.

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id`:
```json
{
  "version": "<execution.version>",
  "stageToAddOrUpdate": [
    {
      "name": "<active_stage.name>",
      "title": "<active_stage.title>",
      "tasksToAddOrUpdate": [
        { "name": "<task.name>", "title": "<task.title>", "description": "<task.description>", "version": "<task.version>" },
        { "name": "<new-uuid>", "title": "<user title>", "description": "<user description>" }
      ]
    }
  ]
}
```

Tell the user: "Task added." Re-fetch and go back to Step 7.
