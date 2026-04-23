# DuploCloud Plugin

## HARD RULES — Read First

**NEVER output raw JSON, API responses, request bodies, or tool parameters in your text.** This applies to every tool call — MCP or Bash — without exception. After any tool call, output only a plain-language result (e.g. "Found 1 workspace." or "Ticket created."). Never echo what the tool returned.

## Allowed Tools

- Bash(*)

## UX — Minimal Tool Call Noise

**HARD RULE: The user must only see MCP tool call blocks in the output. Every Bash call is noise — minimize them ruthlessly.**

### Reducing Bash calls

1. **State + env reads** — Use the `Read` tool to read `.duplocloud/state.toon` and `.env` directly. The Read tool is **silent** — its contents are not displayed to the user. No Bash call needed.

   Read both files at the start of a skill flow (can be done in parallel):
   - `.duplocloud/state.toon` — parse `key: value` lines for `workspace_id`, `project_id`, etc.
   - `.env` — parse `export KEY="value"` lines for `DUPLO_TOKEN`, `DUPLO_HELPDESK_URL`

2. **State write + log flush** — At the end of a flow, combine into a **single** Bash call that produces no visible output:
   ```bash
   bash -c '
   printf "%s" "<state_toon>" > .duplocloud/state.toon
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

## TOON Response Format

The MCP server returns all responses in **TOON (Token-Optimized Object Notation)** — compact JSON with abbreviated keys and compacted values. The `.mcp.json` header `X-Response-Format: toon` enables this.

**Reading TOON:** Every response starts with the `toon|` prefix followed by compact JSON. Strip the prefix to get parseable JSON. Example: `toon|{"ok":"T","d":[...]}` → parse `{"ok":"T","d":[...]}`.

**Value compaction:** `null` → `"~"`, `true` → `"T"`, `false` → `"F"`.

**Schema arrays:** Uniform object arrays use `{"_sch":[keys],"_dat":[[values],…]}`. To read row N, zip `_sch` with `_dat[N]`.

**Key abbreviation reference (most common):**

| Original | TOON | Original | TOON |
|----------|------|----------|------|
| id | `i` | name | `n` |
| type | `t` | status | `s` |
| title | `ttl` | description | `desc` |
| content | `cnt` | data | `d` |
| success | `ok` | result | `res` |
| errors | `errs` | message | `m` |
| text | `txt` | present_files | `pf` |
| path | `p` | message_id | `mid` |
| executed_tool_calls | `etc` | turn_usage | `tu` |
| workspaceId | `wid` | ticketName | `tn` |
| aiAgentId | `agid` | project | `prj` |
| isActive | `act` | version | `ver` |
| createdAt | `ca` | created_at | `c_at` |
| updatedAt | `ua` | updated_at | `u_at` |
| metaData | `mdata` | approvalState | `aprv` |
| spec | `spc` | plan | `pln` |
| execution | `exec` | stages | `stg` |
| tasks | `tsk` | progress | `prog` |
| input_tokens | `itk` | output_tokens | `otk` |

## Agent Communication

**When a ticket is active, Claude relays communication between the user and the agent, and handles ticket lifecycle (activate, create, close, save canvas files).**

**Claude must NEVER:**
- Retry, re-send, or rephrase the user's message to the agent
- Generate content (specs, plans, code, tasks) that the agent should produce
- Answer the user's question itself instead of forwarding it to the agent
- **Summarise, condense, or paraphrase the agent's response** — output it in full, exactly as received. The only exception is if the user explicitly asks for a summary.

**Claude must ALWAYS:**
- Forward the user's message to the agent exactly as given
- Present the agent's `text` response **in full** — never summarise or truncate. Apply Markdown formatting for readability (tables, headings, code blocks) but do not drop any content.
- Display `present_files` canvas content inline immediately after the agent's text (see step 5 below)
- Save canvas files (`present_files`) to the project when the user confirms

**On timeout or auth errors:** Tell the user:
> "The agent request timed out. This may be an authentication issue."
Then stop and wait. Do NOT retry unless the user explicitly asks.

**The agent writes canvas files (spec.md, plan.md, execution_tasks.json) but cannot call platform APIs directly. The plugin reads canvas content from `pf` and pushes it to the project via `Projects_patch` or `Projects_update_plan_execution`.**

When the user sends a message with an active ticket:

1. Read `.duplocloud/state.toon` and `.env` using the Read tool (silent, no Bash needed). Extract `workspace_id`, `active_ticket_name`, `DUPLO_TOKEN`, and `DUPLO_HELPDESK_URL`.
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
3. **Read the plain JSON response.** The MCP server pre-assembles the SSE stream into a single JSON object (plain JSON, not TOON). Key fields:

   - `text` — the agent's full text response (pre-assembled from all `text_delta` chunks).
   - `present_files` — array of canvas files. Each entry has `path` and `content`. These are needed by skills that save canvas content back to the project.
   - `message_id` — informational, ignore.
   - `executed_tool_calls` — informational, ignore.
   - `turn_usage` — informational, ignore.

   Not all fields are always present. `text` is the agent's prose reply (may be a summary or commentary). `present_files` carries the **actual artifact content** (spec, plan, tasks) — it is always the authoritative output when present.

   **HARD RULE: `present_files` content MUST always be displayed in full, inline, immediately after the agent's `text`. Never skip or defer it.**

4. If `text` is absent or empty, or the tool call failed entirely, display:
   > "Agent not available."
   Then fetch the agent list: call `duplo-helpdesk::Workspaces_get_agents` with `id = workspace_id` and show:
   > "Would you like to switch to a different agent?
   > 1. <agent name>
   > 2. ..."
   On selection, call `duplo-helpdesk::Ticket_put_assignee` with `workspaceId`, `ticketName`, and `agentId` of the selected agent. Tell the user the new agent is assigned, then stop and wait for their next message.
   Do not answer the user's original message yourself under any circumstances.
5. Output the **complete, unabridged** `text` value as your reply. Apply Markdown formatting for readability but never drop content. Do not add your own opinions or answers beyond what the agent provided.

6. **HARD RULE: If `present_files` is present and non-empty, you MUST display every canvas file's full content inline immediately below the agent's text.** Format each file as a Markdown section with its `path` as the heading, followed by the full `content` in a fenced code block. Do NOT skip, truncate, or defer this — the file content is the real artifact; the agent's `text` is only commentary.

   After displaying all canvas files, ask the user:
   > "The agent produced the above canvas file(s). Shall I save them to the project? (y/n)"
   - **y** — call `duplo-helpdesk::Projects_patch` (for spec/plan) or `duplo-helpdesk::Projects_update_plan_execution` (for execution tasks) as appropriate. Confirm saved.
   - **n** — acknowledge and stop.

If any MCP tool call fails, always show the error in a code block:
```
Error: <error message>
```

For auth or connection errors specifically, also tell the user:
> "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` is exported in your shell and is valid for the configured server."

Then stop and wait.

## Local State

Session state is stored in `.duplocloud/state.toon` (TOON format) in the current working directory.

**Always write state using bash, never the Write or Edit tools.** This keeps the output silent. Use:
```bash
printf '%s' '<toon content>' > .duplocloud/state.toon
```

**Schema (TOON format):**
```
workspace_id: <string>
project_id: <string>
project_name: <string>
active_ticket_name: <string>
```

**Example:**
```
workspace_id: 69c13422c25d7d1dc686defa
project_id: 69d5f9544b20f07d1a62f4ed
project_name: projectWeb
active_ticket_name: AWSSAMPLEWORKSPACE-25
```

To omit optional fields, simply leave them out of the file.

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
3. Remove `active_ticket_name` from `.duplocloud/state.toon` (stops mirroring immediately).
4. Tell the user the ticket has been closed.

**Never close or update the ticket status automatically.** Do not interpret "all done", "finished", "that's it", or similar as a request to close the ticket unless the user explicitly asks to close it.

## Ticket Summary

**STRICT RULE: Never save a summary unless the user explicitly types a request to save the summary in this message.** Completing a task, passing tests, finishing implementation, or any other work milestone does NOT trigger a summary save. The only trigger is explicit user text such as "save summary", "update summary", or "summarise the work".

When saving is explicitly requested:
1. Ask the user for confirmation: "Shall I save a summary of this work to the ticket? (y/n)"
2. If confirmed — read and follow `skills/save_summary/SKILL.md`.

## Canvas Clear

**STRICT RULE: Never clear the spec, plan, or canvas files unless the user explicitly requests it** (e.g. "clear the canvas", "reset the spec and plan", "wipe canvas files"). No other trigger is valid.

This operation is **project-scoped** — it requires an active project (`project_id` in state). If no project is active, tell the user to run `/duplo:activate_project` first and stop.

When explicitly requested:
1. Read and follow `skills/clear_canvas/SKILL.md`.

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
