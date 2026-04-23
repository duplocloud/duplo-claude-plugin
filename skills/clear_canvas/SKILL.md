---
name: clear_canvas
description: Clear spec, plan, and/or execution tasks for the active project based on the user's natural language request. Clearing cascades downstream — clearing spec also clears plan and execution; clearing plan also clears execution. Loops back into the AI Planner at the correct phase after clearing. Requires an active project.
disable-model-invocation: false
---

**IMPORTANT: Only execute this skill when the user explicitly asks to clear or reset the spec, plan, or canvas files. Never invoke it automatically. This skill is project-scoped — a `project_id` must be present in state.**

Follow these steps in order:

---

## Step 0 — Verify project is active

Read `.duplocloud/state.toon`.

- If `project_id` is absent or file missing: stop and tell the user:
  > "No active project found. Please run `/duplo:activate_project` first."

Capture `project_id` and `project_name`.

---

## Step 1 — Determine what to clear from the user's request

Interpret the user's message and apply the **cascade rule**: clearing any artifact also clears everything downstream in the `spec → plan → execution` chain.

| User mentions | clear_set |
|---------------|-----------|
| spec (any mention) | spec + plan + execution |
| plan (without spec) | plan + execution |
| execution / tasks (without spec or plan) | execution only |
| "all", "everything", "canvas", "reset" | spec + plan + execution |

Examples:
- "clear spec" → `{spec, plan, execution}`
- "clear spec and plan" → `{spec, plan, execution}` (spec cascades anyway)
- "remove the plan" → `{plan, execution}`
- "delete execution tasks" → `{execution}`
- "reset everything" → `{spec, plan, execution}`

Do **not** ask the user to pick from a list — the cascade rule fully resolves `clear_set` from their words.

---

## Step 2 — Confirm

Build a bullet list from `clear_set` and show:

> "This will permanently clear the following for project **\<project_name\>** on the platform:
> - \<Spec — if in clear_set\>
> - \<Plan — if in clear_set\>
> - \<Execution tasks — if in clear_set\>
>
> This cannot be undone. Continue? (y/n)"

- **n** or anything other than yes → stop. Tell the user: "Cancelled — nothing was changed."
- **y** → proceed to Step 3.

---

## Step 3 — Clear the artifacts

**3a — If `clear_set` contains `spec` or `plan`:**

Call `duplo-helpdesk::Projects_patch` with `id = project_id` and body (include only what is in `clear_set`):
```json
{
  "spec": { "content": "" },
  "plan": ""
}
```

- On error: show the error and stop.

**3b — If `clear_set` contains `execution`:**

Call `duplo-helpdesk::Projects_update_plan_execution` with `id = project_id` and body:
```json
{
  "canvas_files": []
}
```

- On error: show the error.

---

## Step 4 — Confirm and determine re-entry phase

Tell the user what was cleared:
> "Cleared: \<comma-separated list\> for **\<project_name\>**."

Re-entry phase — earliest in chain that was cleared:

| clear_set contains | Re-entry phase |
|--------------------|---------------|
| `spec` | **spec** |
| `plan` (no spec) | **plan** |
| `execution` only | **execution** |

---

## Step 5 — Loop back to AI Planner

Tell the user:
> "Starting AI Planner from the **\<re-entry phase\>** phase now."

Then read and follow `skills/ai_planner/SKILL.md` from **Step 2 onwards** (project is already verified — skip Step 0).

In AI Planner Step 2 (phase detection), **skip re-detection** — instead use the `re-entry phase` from above and jump directly to:

| Re-entry phase | AI Planner step |
|----------------|-----------------|
| **spec** | Step 3 (spec phase) |
| **plan** | Step 4 (plan phase) |
| **execution** | Step 5 (execution phase) |
