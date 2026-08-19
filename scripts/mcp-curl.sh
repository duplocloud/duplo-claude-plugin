#!/usr/bin/env bash
# Call the duplo-helpdesk MCP server from the shell.
#
# The MCP Streamable HTTP transport needs two things a plain curl does not do:
#   1. Accept: application/json, text/event-stream   (both, on every POST)
#   2. an initialize handshake, then the returned Mcp-Session-Id on every later POST
#
# Usage:
#   scripts/mcp-curl.sh tools/list
#   scripts/mcp-curl.sh tools/call '{"name":"Workspaces_list","arguments":{}}'
set -euo pipefail

METHOD="${1:-tools/list}"
PARAMS="${2:-{\}}"

: "${DUPLO_HELPDESK_URL:?source .env first}"
: "${DUPLO_TOKEN:?source .env first}"

URL="${DUPLO_HELPDESK_URL%/}/mcp"
ACCEPT="application/json, text/event-stream"
HDRS=(-H "Authorization: Bearer $DUPLO_TOKEN"
      -H "Content-Type: application/json"
      -H "Accept: $ACCEPT"
      -H "X-Response-Format: ${X_RESPONSE_FORMAT:-toon}")

TMP_HDR="$(mktemp)"
trap 'rm -f "$TMP_HDR"' EXIT

# 1. initialize — grab the session id off the response headers
curl -sS -D "$TMP_HDR" -o /dev/null -X POST "$URL" "${HDRS[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"mcp-curl","version":"1"}}}'

SID="$(tr -d '\r' < "$TMP_HDR" | awk 'tolower($1)=="mcp-session-id:"{print $2}')"
[ -n "$SID" ] || { echo "no Mcp-Session-Id returned — check DUPLO_TOKEN / server" >&2; exit 1; }
HDRS+=(-H "Mcp-Session-Id: $SID")

# 2. complete the handshake
curl -sS -o /dev/null -X POST "$URL" "${HDRS[@]}" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. the actual call — strip the SSE framing so the JSON is pipeable into jq
curl -sS -X POST "$URL" "${HDRS[@]}" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"$METHOD\",\"params\":$PARAMS}" \
  | sed -n 's/^data: //p'
