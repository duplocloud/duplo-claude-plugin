---
name: check_mcp
description: Check connectivity to the duplo-helpdesk MCP server.
disable-model-invocation: false
---

Call any lightweight `duplo-helpdesk` MCP tool to verify the server is reachable.
Use `Engineers_get_allowed` or any list tool that requires no parameters.

- If the call succeeds — tell the user:
  > "MCP server is connected and responding."

- If the call fails with an auth or connection error — tell the user:
  > "Cannot reach the duplo-helpdesk MCP server. Ensure `DUPLO_TOKEN` and `DUPLO_HELPDESK_URL` are set correctly (`source .env`) and the server is running."
