# DuploCloud Plugin

## Allowed Tools

- Bash(*)

## Ticket Lifecycle

When the user explicitly asks to close the ticket (e.g. "close the ticket", "mark as done", "resolve the ticket"):

1. Ask the user for confirmation:
   > "Shall I mark this ticket as resolved and close it? (y/n)"
2. If the user confirms — always run with both flags (the API requires disposition when closing):
   ```bash
   python3 ~/.duplocloud/bin/duplo_ticket.py --set-ticket-status --status closed --disposition resolved
   ```
3. Tell the user the ticket has been closed.

**Never close or update the ticket status automatically.** Do not interpret "all done", "finished", "that's it", or similar as a request to close the ticket unless the user explicitly asks to close it.

## Ticket Summary

**STRICT RULE: Never call `--save-summary` unless the user explicitly types a request to save the summary in this message.** Completing a task, passing tests, finishing implementation, or any other work milestone does NOT trigger a summary save. The only trigger is explicit user text such as "save summary", "update summary", or "summarise the work".

When saving is explicitly requested:
1. Ask the user for confirmation: "Shall I save a summary of this work to the ticket? (y/n)"
2. If confirmed — read and follow `skills/save_summary/SKILL.md`.

## End of Turn Summary

After every response where meaningful work was done (code written, tests run, files changed, commands executed, decisions made), append a brief **Work Done** section at the end of your reply:

```
---
**Work Done**
- <bullet: what was done>
- <bullet: what was done>
```

Keep it factual and concise — one line per meaningful action. Omit this section for pure question/answer exchanges where no work was performed.

## Execution Enforcement

**Never write, edit, or run code for a project task without an active execution ticket.**

Before starting any implementation work (writing files, running commands, executing tasks):

1. Run `python3 ~/.duplocloud/bin/duplo_ticket.py --check-project` and verify `active_ticket_name` is set in state.
2. If `active_ticket_name` is missing: do NOT start coding. Tell the user:
   > "No active execution ticket found. Please run `/duplo:activate_ticket` to pick a task before I begin."
   Then stop and wait.

This applies even if the user says "start the execution", "just do it", or similar. An active ticket must exist first.

## State Errors

If `--check-project` or any duplo command returns exit code 3 (no active project/ticket):
- Do NOT attempt to re-activate the project or ticket automatically.
- Tell the user: "Session state is missing. Please run `/duplo:activate_ticket` to restore context before continuing."
- Stop and wait for the user.
