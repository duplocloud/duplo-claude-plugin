---
name: check_mcp
description: Check connectivity to the duplo-helpdesk MCP server.
disable-model-invocation: false
---

## Step 1 — HTTP health check

Run:
```bash
curl -sf "${DUPLO_HELPDESK_URL}/health"
```

- If it returns `{"status": "ok"}` → server is up, proceed to Step 2.
- If it fails (connection refused, non-200) → tell the user:
  > "MCP server is not reachable at `$DUPLO_HELPDESK_URL`. To start it locally:
  > ```
  > cd /Users/nikhil/work/dc/duplo-ai-helpdesk-mcp
  > DUPLO_HOST=http://localhost:60021 uv run duplo-helpdesk-mcp
  > ```
  > Then ensure `source .env` is run with correct `DUPLO_HELPDESK_URL`."

  Stop here.

## Step 2 — MCP tool call (auth check)

Call the `mcp__duplo-helpdesk__Engineers_list` tool with no arguments.

- If it succeeds → tell the user:
  > "MCP server is connected and responding. Auth is valid."
  > Show the number of results returned.

- If it fails with 401/403 → tell the user:
  > "Server is reachable but auth failed. Ensure `DUPLO_TOKEN` is correct and re-run `source .env`."

- If it fails with any other error → show the raw error message to the user.
