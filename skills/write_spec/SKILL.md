---
name: write_spec
description: Collaboratively define requirements and scope for a DuploCloud project, then save the spec to the platform.
disable-model-invocation: false
---

Read and follow the brainstorming approach described in `skills/write_spec/spec-writing.md` throughout this process.

Follow these steps in order:

**Step 0 — Verify project is active:**

Read `.duplocloud/state.json`.

- If `project_id` is absent or file missing: stop and tell the user:
  > "No active project found. Please run `/duplo:activate_project` first."

Capture `project_id`.

**Step 1 — Fetch current spec content:**

Call `duplo-helpdesk::Projects_get` with `id = project_id`.

Extract the `spec.content` field from the response.

- If `spec.content` is **empty or null**: proceed to Step 2a.
- If `spec.content` has **content**: proceed to Step 2b.

**Step 2a — Empty spec: gather requirements:**

Ask the user one open-ended high-level question:
> "What would you like to achieve as part of this project?"

Ask clarifying questions **one at a time** (see spec-writing.md) to understand goals, requirements, scope boundaries, and success criteria. Avoid technical implementation questions — only ask about technical systems if needed to define scope boundaries.

Then proceed to Step 3.

**Step 2b — Non-empty spec: review and iterate:**

Show the existing spec content to the user. Ask:
> "I found an existing spec draft. Would you like to continue refining it, or start fresh?"

Ask clarifying questions one at a time to understand what needs to change. Then proceed to Step 3.

**Step 3 — Draft the spec:**

Write a well-structured spec covering: goals, requirements, scope (in/out), success criteria, stakeholders, and any technical boundaries needed to scope the work. Do NOT include architecture decisions, implementation approaches, or technology choices — those belong in the plan.

Show the draft to the user, then ask:
> "Does this draft look good, or would you like changes?"

- If the user requests **changes**: make the edits and re-ask.
- If the user says **good**: proceed to Step 4.

**Step 4 — Confirm and save to platform:**

Ask the user:
> "The spec looks good! How would you like to proceed?"
> 1. **Save** — push content to the platform (stays in Draft)
> 2. **Cancel** — don't push

- If **Save**:

  Call `duplo-helpdesk::Projects_patch` with `id = project_id` and body:
  ```json
  {
    "spec": {
      "content": "<spec content>"
    }
  }
  ```

  - On success: tell the user "Spec saved to the DuploCloud platform."
  - On error: show the error to the user.

- If **Cancel**: stop — the draft is visible in this conversation but not saved.
