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

- `DUPLO_TOKEN` — Bearer token for API auth
- `DUPLO_HELPDESK_URL` — Helpdesk server base URL (also used as `platform_context.duplo_base_url` when sending messages to the agent)

## Agent Communication

When a ticket is active, **the assigned agent is the sole responder to the user's messages**. Claude Code handles ticket lifecycle only (activate, create, close, spec, plan). Do not add your own response to user messages — forward them to the agent and display the agent's reply.

When the user sends a message with an active ticket:

1. Read the required env values by running:
   ```bash
   bash -c 'source .env 2>/dev/null; printf "TOKEN=%s\nURL=%s" "$DUPLO_TOKEN" "$DUPLO_HELPDESK_URL"'
   ```
2. Call `mcp__duplo-helpdesk__Ticket_send_message` with:
   ```json
   {
     "workspaceId": "<workspace_id>",
     "ticketName": "<active_ticket_name>",
     "content": "<user message>",
     "role": "user",
     "origin": "helpdesk",
     "message_mode": 0,
     "data": {},
     "platform_context": {
       "duplo_base_url": "<value of DUPLO_HELPDESK_URL>",
       "duplo_token": "<value of DUPLO_TOKEN>"
     }
   }
   ```
3. Output the agent's response as your reply text (not just as a tool result). This ensures the Stop hook captures it for mirroring. Do not add commentary — output the agent's text verbatim.

If any MCP tool call fails, always show the error in a code block:
```
Error: <error message>
```

For auth or connection errors specifically, also tell the user:
> "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` is exported in your shell and is valid for the configured server."

Then stop and wait.

## Local State

Session state is stored in `.duplocloud/state.json` in the current working directory.

**Always write state using bash, never the Write or Edit tools.** This keeps the output silent. Use:
```bash
printf '%s' '<json>' > .duplocloud/state.json
```
Or with a variable:
```bash
printf '%s' "$STATE_JSON" > .duplocloud/state.json
```

**Schema:**
```json
{
  "workspace_id": "string",
  "project_id": "string",
  "project_name": "string",
  "active_ticket_name": "string"
}
```

`project_id` and `project_name` are optional — tickets are independent of projects. Only `workspace_id` is required for ticket operations.

If `workspace_id` is missing and the skill requires it but cannot resolve it on its own:
- Do NOT attempt to re-activate automatically.
- Tell the user: "No active workspace. Please run `/duplo:activate_project` or `/duplo:activate_ticket` to set one."
- Stop and wait.

## Ticket Lifecycle

When the user explicitly asks to close the ticket (e.g. "close the ticket", "mark as done", "resolve the ticket"):

1. Ask the user for confirmation:
   > "Shall I mark this ticket as resolved and close it? (y/n)"
2. If confirmed — call `mcp__duplo-helpdesk__Ticket_put_status` with `workspaceId`, `ticketName`, and body:
   ```json
   { "status": "closed", "disposition": "resolved" }
   ```
3. Remove `active_ticket_name` from `.duplocloud/state.json` (stops mirroring immediately).
4. Tell the user the ticket has been closed.

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
