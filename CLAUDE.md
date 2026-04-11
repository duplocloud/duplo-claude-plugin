# DuploCloud Plugin

## HARD RULES — Read First

**NEVER output raw JSON, API responses, request bodies, or tool parameters in your text.** This applies to every tool call — MCP or Bash — without exception. After any tool call, output only a plain-language result (e.g. "Found 1 workspace." or "Ticket created."). Never echo what the tool returned.

## Allowed Tools

- Bash(*)

## UX — Minimal Tool Call Noise

**HARD RULE: The user must only see MCP tool call blocks in the output. Every Bash call is noise — minimize them ruthlessly.**

### Reducing Bash calls

1. **State + env reads** — When a skill starts and needs both state and env values, read them in a **single** Bash call that writes everything to a temp file. **The only stdout must be the temp file path — nothing else.**
   ```bash
   bash -c '
   TMPF=$(mktemp)
   cat .duplocloud/state.json >> "$TMPF" 2>/dev/null || echo "{}" >> "$TMPF"
   source .env 2>/dev/null
   printf "\nENV_TOKEN=%s\nENV_URL=%s\n" "$DUPLO_TOKEN" "$DUPLO_HELPDESK_URL" >> "$TMPF"
   echo "$TMPF"
   '
   ```
   The output will be just a path like `/tmp/tmp.abc123`. Then use the `Read` tool to silently read that file — the Read tool contents are not displayed to the user. **Never** issue separate Bash calls for state and env.
   
   Give this Bash call a description like `"Loading session"`.

2. **State write + log flush** — At the end of a flow, combine into a **single** Bash call that produces no visible output:
   ```bash
   bash -c '
   printf "%s" "<state_json>" > .duplocloud/state.json
   LOG_FILE=".duplocloud/duplo-plugin.log.json"
   ENTRIES="<log_entries_array>"
   if [ -f "$LOG_FILE" ]; then EXISTING=$(cat "$LOG_FILE"); else EXISTING="[]"; fi
   python3 -c "import json,sys; e=json.loads(sys.argv[1]); e.extend(json.loads(sys.argv[2])); print(json.dumps(e,indent=2))" "$EXISTING" "$ENTRIES" > "$LOG_FILE"
   '
   ```
   Give this Bash call a description like `"Saving session"`.

3. **Mid-flow state writes** — If you must write state mid-flow (e.g. after workspace selection before listing projects), batch it in the same parallel tool call as the next MCP call.

4. **No standalone Bash calls** — Every Bash call must either be the single init read at the start, the single flush at the end, or batched in parallel with an MCP call. If you find yourself about to issue a Bash call alone, stop and find something to batch it with.

### Status lines

Before each tool call batch, print a conversational status line:

```
Now let me fetch your available workspaces
Let me load the project details
Creating your ticket now
Sending your message to the agent
```

Use natural, first-person phrasing — not terse labels. One line per logical action, not per tool call.

### Displaying tool responses

**HARD RULE: Never output raw JSON, request bodies, response payloads, or tool parameters in your text response — for any tool, GET or write.**

After every tool call, output only a plain-language result:
- "Found 2 workspaces."
- "Ticket created successfully."
- "Project **projectWeb** is active."

Extract only the meaningful data. Never echo the API response structure.

### Auto-selection

When logic auto-selects an item (single result, or matches saved state), always tell the user explicitly:

```
Auto-selecting <item-name> — it's the only one available.
Auto-selecting <item-name> — matches your saved session.
```

Never silently select without telling the user.

## MCP Server

All DuploCloud backend calls go through the **`duplo-helpdesk` MCP server** configured in `.mcp.json`.
The server auto-generates tools from the helpdesk Swagger spec. Skills and docs use the generic name `duplo-helpdesk::<OperationId>`. In Claude Code the actual tool name is `mcp__duplo-helpdesk__<OperationId>` — map accordingly.

Environment variables required before launching Claude:
```bash
source .env   # sets DUPLO_TOKEN and DUPLO_HELPDESK_URL
```

- `DUPLO_TOKEN` — Bearer token for API auth
- `DUPLO_HELPDESK_URL` — Helpdesk server base URL (also used as `platform_context.duplo_base_url` when sending messages to the agent)

## Agent Communication

**HARD RULE: Claude must never act as an agent replacement.** If an agent call returns no response, an empty response, or an error — display the error and stop. Do not attempt to answer the user's question yourself. The agent is the sole responder; Claude only handles ticket/project lifecycle.

**The agent writes canvas files (spec.md, plan.md, execution_tasks.json) but cannot call platform APIs directly. The plugin is responsible for reading the canvas content from `present_file` SSE events and pushing it to the project via `Projects_patch` or `Projects_update_plan_execution`.**

When a ticket is active, **the assigned agent is the sole responder to the user's messages**. Claude Code handles ticket lifecycle only (activate, create, close, spec, plan). Do not add your own response to user messages — forward them to the agent and display the agent's reply.

When the user sends a message with an active ticket:

1. Read state + env in a single Bash call (see "State + env reads" above). Extract `workspace_id`, `active_ticket_name`, `DUPLO_TOKEN`, and `DUPLO_HELPDESK_URL`.
2. Call `duplo-helpdesk::Ticket_send_message_streaming` with:
   ```json
   {
     "workspaceId": "<workspace_id>",
     "ticketName": "<active_ticket_name>",
     "content": "<user message>",
     "message_mode": 0,
     "data": {},
     "platform_context": {
       "duplo_base_url": "<value of DUPLO_HELPDESK_URL>",
       "duplo_token": "<value of DUPLO_TOKEN>"
     }
   }
   ```
3. **Parse the streaming response.** The tool returns raw SSE events. From the response:

   **Assemble agent text** — concatenate all `text_delta` values in order:
   ```
   event: message
   data: {"type":"text_delta","text":"..."}
   ```
   Join every `"type":"text_delta"` block's `"text"` value into a single string. That is the agent's full response.

   **Capture canvas files** — collect any `present_file` events:
   ```
   event: message
   data: {"type":"present_file","path":"canvas-documents/execution_tasks.json","content":"..."}
   ```
   Store the `path` and `content` for each `present_file` event. These are needed by skills that save canvas content back to the project (e.g., ai_planner execution phase).

   Ignore all other event types (`message_id`, `executed_tool_calls`, `turn_usage`, `done`, etc.).

4. If the assembled text is empty, or the tool call failed entirely, display:
   > "Agent not available."
   Then fetch the agent list: call `duplo-helpdesk::Workspaces_get_agents` with `id = workspace_id` and show:
   > "Would you like to switch to a different agent?
   > 1. <agent name>
   > 2. ..."
   On selection, call `duplo-helpdesk::Ticket_put_assignee` with `workspaceId`, `ticketName`, and `agentId` of the selected agent. Tell the user the new agent is assigned, then stop and wait for their next message.
   Do not answer the user's original message yourself under any circumstances.
5. Output the assembled agent text as your reply text verbatim. Do not add commentary or wrap it.

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
2. If confirmed — call `duplo-helpdesk::Ticket_put_status` with `workspaceId`, `ticketName`, and body:
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

## MCP Tool Logging

All MCP tool calls and their responses must be logged to `.duplocloud/duplo-plugin.log.json`. This file is gitignored.

**Log every `duplo-helpdesk::*` tool call** — both the request and the response. Accumulate entries in memory during the flow. Flush them in the single end-of-flow Bash call (combined with state write — see "State write + log flush" above).

**Log entry schema:**
```json
{
  "timestamp": "<ISO 8601 UTC>",
  "project_name": "<project_name from state, or null>",
  "ticket_name": "<active_ticket_name from state, or null>",
  "tool": "<duplo-helpdesk::OperationId>",
  "request": { },
  "response": { }
}
```

- `request` — the full parameters passed to the tool.
- `response` — the full tool result (truncate individual string values to 2000 chars).
- Timestamp format: `2006-01-02T15:04:05Z` (UTC).

**Do not let logging failures block the main flow.** If the log write fails, continue silently.

---

## End of Turn Summary

After every response where meaningful work was done (code written, tests run, files changed, commands executed, decisions made), append a brief **Work Done** section at the end of your reply:

```
---
**Work Done**
- <bullet: what was done>
- <bullet: what was done>
```

Keep it factual and concise — one line per meaningful action. Omit this section for pure question/answer exchanges where no work was performed.
