---
name: save_summary
description: Generate and save a summary of the current active ticket's work to the platform.
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Check active ticket:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --check-project
```

- If exit code is **3**: tell the user "No active project found. Please run `/duplo:activate_project` first." and stop.

Check that `active_ticket_name` exists in state — the summary is scoped to the **current active ticket only**. Do not summarise work from previous tickets or earlier sessions.

**Step 2 — Generate the summary:**

Write a markdown summary covering only the work done for the current active ticket in this session. Use only the sections below. Omit any section that has nothing relevant. Be concise — each bullet is a standalone, concrete fact. No filler.

```
## Summary
2-3 sentences: what this ticket was about and what was accomplished.

## Completed
Bullet list of things successfully done.

## What Went Wrong
Bullet list of issues, errors, blockers, or failures encountered. Include root cause where clear.

## Approach Changes
For each significant pivot away from the original plan:
- **Original approach**: what was tried first
- **New approach**: what was done instead
- **Reason**: why the change was needed
- **Impact on future tasks**: what downstream work is affected and how

## Discoveries
(Include for discovery or exploration tickets.)
Concrete findings — actual resource names, configurations, or technical facts uncovered.

## Key Decisions
Bullet list of important technical or architectural decisions made.

## Future Task Impacts
Specific impacts on upcoming tickets the project lead must account for. Name the affected area or task where possible.

## Open Items
Unresolved issues, pending questions, or follow-up actions still needed.
```

**Step 3 — Save to platform:**

Pipe the summary directly to the API via stdin (do NOT use the Write tool or create a local file):

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --save-summary << 'SUMMARY_EOF'
<summary content from Step 2>
SUMMARY_EOF
```

- If exit code is **0**: tell the user "Summary saved to the ticket."
- If exit code is **1**: show the error and stop.
