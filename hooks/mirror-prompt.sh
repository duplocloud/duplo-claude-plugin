#!/usr/bin/env bash
# UserPromptSubmit hook — mirrors the user's prompt to the active ticket (record-only).
# Reads hook JSON from stdin. Runs async/silent. Exits 0 always.
exec 2>/dev/null

set -euo pipefail

HOOK_DATA=$(cat)
PROMPT=$(echo "$HOOK_DATA" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0

[ -f ".env" ] && source ".env"

STATE_FILE=".duplocloud/state.json"
[ ! -f "$STATE_FILE" ] && exit 0

WS=$(jq -r '.workspace_id // empty' "$STATE_FILE" 2>/dev/null)
TICKET=$(jq -r '.active_ticket_name // empty' "$STATE_FILE" 2>/dev/null)
[ -z "$WS" ] || [ -z "$TICKET" ] && exit 0
[ -z "${DUPLO_TOKEN:-}" ] && exit 0

# Record turn start timestamp for mirror-stop.sh to filter by
echo "$(date -u +%Y-%m-%dT%H:%M:%S)" > /tmp/duplo_mirror_turn_start_$$
mv /tmp/duplo_mirror_turn_start_$$ /tmp/duplo_mirror_turn_start

CONTENT="$PROMPT"

ARGS=$(jq -n \
  --arg ws "$WS" \
  --arg ticket "$TICKET" \
  --arg content "$CONTENT" \
  '{
    workspaceId: $ws,
    ticketName: $ticket,
    threadName: "claude-code",
    content: $content,
    author: "user"
  }')

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/mcp-call.sh" "Ticket_create_chat" "$ARGS"
