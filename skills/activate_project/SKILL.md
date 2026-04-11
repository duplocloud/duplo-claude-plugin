---
name: activate-project
description: Activate a DuploCloud project context.
disable-model-invocation: false
---

## Color Coding — HARD RULE

**Always prefix active workspace, project, or ticket names with a 🟢 emoji.** This applies everywhere an active/selected name is displayed — auto-select messages, confirmation prompts, health tables, and list items.

Example:
> Auto-selecting 🟢 **aws-sample-workspace** — it's the only workspace available.

In lists, only the currently active item gets the 🟢 prefix.

---

Follow these steps in order:

---

## Step 1 — Resolve workspace

Read `.duplocloud/state.json` (file may not exist). Note `workspace_id`, `project_id`, `project_name` if present.

Call `duplo-helpdesk::Workspaces_get_available` to get the list of available workspaces.

If the call fails with an auth or connection error, stop and tell the user:
> "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` is exported and the server is running."

- If the call returns an empty list, tell the user:
  > "It looks like you don't have any workspaces set up yet. Please create one in the DuploCloud portal first."
  Then stop.

- If only **one** workspace is returned: auto-select it and tell the user:
  > "Auto-selecting 🟢 **\<workspace name\>** — it's the only workspace available."
  Capture its `id` as `workspace_id`.

- If **multiple** workspaces and `workspace_id` is present in state:
  - Check whether that `workspace_id` exists in the returned list.
  - If **found**: ask the user:
    > "You're currently connected to 🟢 **\<workspace name\>**. Would you like to continue with this workspace? (y/n)"
    - **y** → use this workspace. Proceed to Step 2.
    - **n** → show the workspace list (Step 1a).
  - If **not found**: tell the user the previously saved workspace is no longer available, then show the workspace list (Step 1a).

- If `workspace_id` is absent from state: show the workspace list (Step 1a).

### Step 1a — Choose a workspace

Show a numbered list using only the workspace **name** (no raw IDs). If a workspace matches the `workspace_id` currently in state, prefix it with 🟢:
```
Here are your available workspaces:
1. 🟢 <name>   ← currently active
2. <name>
...
```
Ask: "Which workspace would you like to use?"

Capture the selected workspace's `id` as `workspace_id` (store internally, do not show to the user).

If the newly selected workspace **differs** from what was in state: **clear `project_id` and `project_name`** (the old project belongs to the old workspace).

---

## Step 2 — Resolve project

Call `duplo-helpdesk::Projects_list` with `workspaceId = workspace_id`.

If the list is empty: tell the user "No projects found in this workspace. Please create a project in the DuploCloud portal first." and stop.

**Case A — only one remote project:**
- If it matches `project_id` in local state → tell the user:
  > "Auto-selecting 🟢 **\<name\>** — it matches your saved session."
  Proceed to Step 4.
- Otherwise → tell the user:
  > "Auto-selecting 🟢 **\<name\>** — it's the only project available."
  Set `project_id` and `project_name`. Proceed to Step 4.

**Case B — multiple remote projects, `project_id` present in state AND found in remote list:**
> "Active project: 🟢 **\<project_name\>**. Would you like to continue with this project or select a different one?
> 1. Continue with **\<project_name\>**
> 2. Select from list"
- **1** → keep current project. Proceed to Step 4.
- **2** → continue to Step 3.

**Case C — multiple remote projects, `project_id` absent OR not found in remote list:**
Continue to Step 3.

---

## Step 3 — List and select project

Show the user a numbered list. If a project matches the `project_id` currently in state, prefix it with 🟢:
```
Available projects:
1. 🟢 <name> — <description>   ← currently active
2. <name> — <description or "no description">
...
```
Ask: "Which project would you like to activate?"

Wait for selection. Capture `id` → `project_id`, `name` → `project_name`.

---

## Step 4 — Save state

Write `.duplocloud/state.json` silently using bash, preserving any existing `active_ticket_name` and `tickets` fields if the workspace has not changed:
```json
{
  "workspace_id": "<workspace_id>",
  "project_id": "<project_id>",
  "project_name": "<project_name>"
}
```

Create the `.duplocloud/` directory first if it does not exist.

---

## Step 5 — Fetch project data

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

From the response extract:
- `spec.content` → `spec_content` (string, may be blank or absent)
- `spec.metaData.approvalState` → `spec_state`:
  - `"Approved"` → **Approved**
  - content present but not approved → **Draft**
  - content absent or blank → **Not started**
- `plan.content` → `plan_content` (string, may be blank or absent)
- `plan.metaData.approvalState` → `plan_state` (same logic as spec)
- `execution.stages` → `has_execution_tasks` = true if any stage has tasks

---

## Step 6 — Project health

Display the health table:

> **Project:** 🟢 **\<project_name\>**
>
> | Artifact | Status |
> |----------|--------|
> | Spec | \<spec_state\> |
> | Plan | \<plan_state\> |
> | Tasks | \<N tasks ready / None\> |

---

## Step 7 — Routing

Based on the health data, suggest the next action:

| Condition | Prompt |
|---|---|
| Spec **Not started** | "This project doesn't have a spec yet. Would you like to start the AI Planner? (y/n)" → if y, follow `skills/ai_planner/SKILL.md` |
| Spec **Draft** | "There's a spec draft in progress. Would you like to continue with the AI Planner to refine or confirm it? (y/n)" → if y, follow `skills/ai_planner/SKILL.md` |
| Spec **Approved**, plan **Not started** or **Draft** | "Spec is approved. Would you like to continue with the AI Planner to build the plan? (y/n)" → if y, follow `skills/ai_planner/SKILL.md` |
| Both **Approved**, `has_execution_tasks` = true | "Both spec and plan are approved and tasks are ready. Run `/duplo:ai_planner` to manage tasks or `/duplo:activate_ticket` to pick up a task." |
| Both **Approved**, no tasks | "Spec and plan are approved but no execution stages yet. Would you like to generate them now? (y/n)" → if y, follow `skills/ai_planner/SKILL.md` |

If the user declines any prompt: stop.
