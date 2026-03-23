---
name: write_plan
description: Collaboratively write a DuploCloud project implementation plan with the user, then save it to the platform.
disable-model-invocation: false
---

Read and follow the brainstorming approach described in `skills/write_plan/writing-plans.md` throughout this process.

Follow these steps in order:

**Step 0 — Verify project is active:**

Read `.duplocloud/state.json`.

- If `project_id` is absent or file missing: stop and tell the user:
  > "No active project found. Please run `/duplo:activate_project` first."

Capture `project_id`.

**Step 1 — Fetch the spec for context:**

Call `mcp__duplo-helpdesk__Projects_get` with `id = project_id`.

Extract `spec.content` and `plan` from the response. The spec provides requirements and scope that the plan must implement.

**Step 2 — Fetch current plan content:**

Use the `plan` field extracted in Step 1.

- If `plan` is **empty or null**: proceed to Step 2a.
- If `plan` has **content**: proceed to Step 2b.

**Step 2a — Empty plan: gather requirements:**

Ask the user one open-ended high-level question:
> "The spec is loaded. What aspects of the implementation would you like to focus on, or shall I draft a complete plan from the spec?"

Ask clarifying questions **one at a time** (see writing-plans.md) until you have enough to draft a plan.

Then proceed to Step 3.

**Step 2b — Non-empty plan: review and iterate:**

Show the existing plan content to the user. Ask:
> "I found an existing plan draft. Would you like to continue refining it, or start fresh?"

Ask clarifying questions one at a time to understand what needs to change. Then proceed to Step 3.

**Step 3 — Draft the plan:**

Write a well-structured implementation plan based on the spec and the user's answers, following the format in writing-plans.md.

Show the draft to the user, then ask:
> "Does this draft look good, or would you like changes?"

- If the user requests **changes**: make the edits and re-ask.
- If the user says **good**: proceed to Step 4.

**Step 4 — Confirm and save to platform:**

Ask the user:
> "The plan looks good! How would you like to proceed?"
> 1. **Save** — push content to the platform
> 2. **Cancel** — don't push

- If **Save**:

  Call `mcp__duplo-helpdesk__Projects_patch` with `id = project_id` and body:
  ```json
  {
    "plan": "<plan content as markdown string>"
  }
  ```

  Note: `plan` is a plain string field, not a nested object like `spec`.

  - On success: tell the user "Plan saved to the DuploCloud platform."
  - On error: show the error to the user.

- If **Cancel**: stop — the draft is visible in this conversation but not saved.
