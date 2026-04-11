---
name: save_summary
description: Generate and save a summary of the current active ticket's work to the platform.
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Check active ticket:**

Read `.duplocloud/state.json`.

- If `workspace_id` or `active_ticket_name` is missing: tell the user:
  > "No active ticket found. Please run `/duplo:activate_ticket` first."
  Then stop.

Capture `workspace_id` and `active_ticket_name`. The summary is scoped to the **current active ticket only**. Do not summarise work from previous tickets or earlier sessions.

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

Call `duplo-helpdesk::Ticket_save_summary` with:
- `workspaceId = workspace_id`
- `ticketName = active_ticket_name`
- Body: `{ "summary": "<summary content from Step 2>" }`

- On success: tell the user "Summary saved to the ticket."
- On error (tool not found): the backend may need to be rebuilt and the MCP swagger refreshed. Tell the user the summary content so they can save it manually if needed.
