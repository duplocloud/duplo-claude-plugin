#!/usr/bin/env bash
# Stop hook — mirrors Claude's response to the active ticket (record-only).
# Reads hook JSON from stdin. Runs async/silent. Exits 0 always.
exec 2>/dev/null

set -euo pipefail

HOOK_DATA=$(cat)
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path // empty' 2>/dev/null)
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

[ -f ".env" ] && source ".env"

STATE_FILE=".duplocloud/state.json"
[ ! -f "$STATE_FILE" ] && exit 0

WS=$(jq -r '.workspace_id // empty' "$STATE_FILE" 2>/dev/null)
TICKET=$(jq -r '.active_ticket_name // empty' "$STATE_FILE" 2>/dev/null)
[ -z "$WS" ] || [ -z "$TICKET" ] && exit 0
[ -z "${DUPLO_TOKEN:-}" ] && exit 0

# Read turn start timestamp (written by mirror-prompt.sh)
SINCE=""
[ -f /tmp/duplo_mirror_turn_start ] && SINCE=$(cat /tmp/duplo_mirror_turn_start)

# Retry up to 10 times (0.5s apart) waiting for assistant message to appear in transcript
TEXT=""
for _ in $(seq 1 10); do
  if [ -n "$SINCE" ]; then
    TEXT=$(jq -rs --arg since "$SINCE" '
      [ .[]
        | select(.timestamp >= $since)
        | select((.role // .message.role) == "assistant")
        | (.content // .message.content)
        | if type == "string" then .
          else (map(select(.type == "text") | .text) | join("\n"))
          end
        | select(length > 0)
      ] | join("\n\n")
    ' "$TRANSCRIPT" 2>/dev/null || true)
  else
    TEXT=$(jq -rs '
      [ .[]
        | select((.role // .message.role) == "assistant")
        | (.content // .message.content)
        | if type == "string" then .
          else (map(select(.type == "text") | .text) | join("\n"))
          end
        | select(length > 0)
      ] | last // ""
    ' "$TRANSCRIPT" 2>/dev/null || true)
  fi
  [ -n "$TEXT" ] && break
  sleep 0.5
done

[ -z "$TEXT" ] && exit 0

CONTENT=$(printf '**Claude Code:**\n\n%s' "$TEXT")

ARGS=$(jq -n \
  --arg ws "$WS" \
  --arg ticket "$TICKET" \
  --arg content "$CONTENT" \
  '{
    workspaceId: $ws,
    ticketName: $ticket,
    threadName: "claude-code",
    content: $content,
    author: "claude-code"
  }')

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/mcp-call.sh" "Ticket_create_chat" "$ARGS"
