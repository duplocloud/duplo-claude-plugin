#!/usr/bin/env bash
# Invoke a duplo-helpdesk MCP tool via HTTP.
# Usage: mcp-call.sh <tool-name> <arguments-json>
# Exits 0 always. Outputs nothing on success; errors go to stderr.
#
# Requires env: DUPLO_TOKEN, DUPLO_HELPDESK_URL

set -euo pipefail

TOOL_NAME="${1:-}"
ARGUMENTS="${2:-{\}}"
MCP_URL="${DUPLO_HELPDESK_URL:-http://localhost:8000}/mcp"

[ -z "$TOOL_NAME" ] && exit 0
[ -z "${DUPLO_TOKEN:-}" ] && exit 0

HEADERS_FILE=$(mktemp /tmp/duplo_mcp_headers_XXXXXX)
trap 'rm -f "$HEADERS_FILE"' EXIT

# Step 1 — Initialize session
curl -sf --max-time 5 \
  -D "$HEADERS_FILE" \
  -X POST "$MCP_URL" \
  -H "Authorization: Bearer $DUPLO_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"duplo-mirror","version":"1"}}}' \
  > /dev/null 2>&1 || exit 0

SESSION_ID=$(grep -i "^mcp-session-id:" "$HEADERS_FILE" | awk '{print $2}' | tr -d '\r\n')
[ -z "$SESSION_ID" ] && exit 0

# Step 2 — Call tool
PAYLOAD=$(jq -n \
  --arg name "$TOOL_NAME" \
  --argjson args "$ARGUMENTS" \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":$name,"arguments":$args}}')

curl -sf --max-time 10 \
  -X POST "$MCP_URL" \
  -H "Authorization: Bearer $DUPLO_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d "$PAYLOAD" \
  > /dev/null 2>&1 || true

exit 0
