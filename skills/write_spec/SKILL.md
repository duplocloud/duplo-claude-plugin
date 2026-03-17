---
name: write_spec
description: Collaboratively define requirements and scope for a DuploCloud project, then save the spec to the platform.
disable-model-invocation: false
---

Read and follow the brainstorming approach described in `skills/write_spec/spec-writing.md` throughout this process.

Follow these steps in order:

**Step 0 — Verify spec ticket is active:**

Run:
```bash
python3 -c "import json,sys; d=json.load(open('.duplocloud/state.json')); sys.exit(0 if d.get('spec_ticket_id') else 1)" 2>/dev/null
```

- Exit 0: continue to Step 1.
- Any other result (exit 1 or file missing): stop and tell the user:
  > "No active spec ticket found. Please run `/duplo:activate_ticket` first to create or resume a spec ticket."

**Step 1 — Fetch current spec content:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-spec
```

- If the output is **empty**: proceed to Step 2a.
- If the output has **content**: proceed to Step 2b.

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

Write a well-structured spec covering: goals, requirements, scope (in/out), success criteria, stakeholders, and any technical boundaries needed to scope the work. Do NOT include architecture decisions, implementation approaches, or technology choices — those belong in the plan. Save it locally:

```bash
# Write the spec content to .duplocloud/spec.md
```

Show the draft to the user, then ask:
> "Does this draft look good, or would you like changes?"

- If the user requests **changes**: make the edits, save to `.duplocloud/spec.md` again, and re-ask.
- If the user says **good**: proceed to Step 4.

**Step 4 — Confirm and save to platform:**

Ask the user:
> "The spec looks good! How would you like to proceed?"
> 1. **Save** — push content to the platform (stays in Draft)
> 2. **Save and Approve** — push content and mark the spec as Approved
> 3. **Cancel** — keep the local draft only, don't push

- If **Save**:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --save-spec --spec-file .duplocloud/spec.md
```

  - Exit 0: tell the user "Spec saved to the DuploCloud platform (Draft)."
  - Exit 1: show the error to the user.

- If **Save and Approve**:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --save-spec --spec-file .duplocloud/spec.md --approve
```

  - Exit 0: tell the user "Spec saved and approved on the DuploCloud platform."
  - Exit 1: show the error to the user.

- If **Cancel**: stop — the local draft remains at `.duplocloud/spec.md`.
