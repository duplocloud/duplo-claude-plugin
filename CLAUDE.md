# DuploCloud Plugin

## Allowed Tools

- Bash(*)

## MCP Server

All DuploCloud backend calls go through the **`duplo-helpdesk` MCP server** configured in `.mcp.json`.
The server auto-generates tools from the helpdesk Swagger spec — tools are named `mcp__duplo-helpdesk__<OperationId>`.

Environment variables required before launching Claude:
```bash
source .env   # sets DUPLO_TOKEN and DUPLO_HELPDESK_URL
```

If any MCP tool call fails with an auth or connection error:
- Tell the user: "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` is exported in your shell and is valid for the configured server."
- Stop and wait.

## Local State

Session state is stored in `.duplocloud/state.json` in the current working directory.
Skills read and write this file directly using Claude's file tools. No Python required.

**Schema:**
```json
{
  "workspace_id": "string",
  "project_id": "string",
  "project_name": "string",
  "active_ticket_name": "string"
}
```

If state is missing (`project_id` or `workspace_id` absent):
- Do NOT attempt to re-activate automatically.
- Tell the user: "Session state is missing. Please run `/duplo:activate_project` to restore context before continuing."
- Stop and wait.

## Ticket Lifecycle

When the user explicitly asks to close the ticket (e.g. "close the ticket", "mark as done", "resolve the ticket"):

1. Ask the user for confirmation:
   > "Shall I mark this ticket as resolved and close it? (y/n)"
2. If confirmed — call the `duplo-helpdesk` MCP tool to update the ticket status
   with `status = "closed"` and `disposition = "resolved"` on the active ticket.
3. Tell the user the ticket has been closed.

**Never close or update the ticket status automatically.** Do not interpret "all done", "finished", "that's it", or similar as a request to close the ticket unless the user explicitly asks to close it.

## Ticket Summary

**STRICT RULE: Never save a summary unless the user explicitly types a request to save the summary in this message.** Completing a task, passing tests, finishing implementation, or any other work milestone does NOT trigger a summary save. The only trigger is explicit user text such as "save summary", "update summary", or "summarise the work".

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
