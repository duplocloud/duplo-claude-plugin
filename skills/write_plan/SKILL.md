---
name: write_plan
description: Collaboratively write a DuploCloud project implementation plan with the user, then save it to the platform.
disable-model-invocation: false
---

Read and follow the brainstorming approach described in `skills/write_plan/writing-plans.md` throughout this process.

Follow these steps in order:

**Step 0 — Verify spec ticket is active:**

Run:
```bash
python3 -c "import json,sys; d=json.load(open('.duplocloud/state.json')); sys.exit(0 if d.get('spec_ticket_id') else 1)" 2>/dev/null
```

- Exit 0: continue to Step 1.
- Any other result (exit 1 or file missing): stop and tell the user:
  > "No active spec ticket found. Please run `/duplo:activate_ticket` first."

**Step 1 — Fetch the approved spec for context:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-spec
```

Read the spec content — it provides the requirements and scope that the plan must implement.

**Step 2 — Fetch current plan content:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-plan
```

- If the output is **empty**: proceed to Step 2a.
- If the output has **content**: proceed to Step 2b.

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

Write a well-structured implementation plan based on the spec and the user's answers, following the format in writing-plans.md. Save it locally:

```bash
# Write the plan content to .duplocloud/plan.md
```

Show the draft to the user, then ask:
> "Does this draft look good, or would you like changes?"

- If the user requests **changes**: make the edits, save to `.duplocloud/plan.md` again, and re-ask.
- If the user says **good**: proceed to Step 4.

**Step 4 — Confirm and save to platform:**

Ask the user:
> "The plan looks good! How would you like to proceed?"
> 1. **Save** — push content to the platform (stays in Draft)
> 2. **Save and Approve** — push content and mark the plan as Approved
> 3. **Cancel** — keep the local draft only, don't push

- If **Save**:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --save-plan --plan-file .duplocloud/plan.md
```

  - Exit 0: tell the user "Plan saved to the DuploCloud platform (Draft)."
  - Exit 1: show the error to the user.

- If **Save and Approve**:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --save-plan --plan-file .duplocloud/plan.md --approve
```

  - Exit 0: tell the user "Plan saved and approved on the DuploCloud platform."
  - Exit 1: show the error to the user.

- If **Cancel**: stop — the local draft remains at `.duplocloud/plan.md`.
