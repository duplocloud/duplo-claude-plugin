#!/bin/bash
# Mirror user prompt to helpdesk ticket conversation (mode=1, no agent call)

STATE_FILE=".duplocloud/state.toon"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(grep '^workspace_id:' "$STATE_FILE" 2>/dev/null | sed 's/^workspace_id: *//')
TICKET_NAME=$(grep '^active_ticket_name:' "$STATE_FILE" 2>/dev/null | sed 's/^active_ticket_name: *//')
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

PROMPT=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null)
[ -n "$PROMPT" ] || exit 0

# Skip slash commands and single-char/digit confirmations (internal UI navigation)
echo "$PROMPT" | python3 -c "
import sys, re
p = sys.stdin.read().strip()
if p.startswith('/') or re.fullmatch(r'[ynYN]|[0-9]+', p):
    sys.exit(1)
" 2>/dev/null || exit 0

source .env 2>/dev/null

BODY=$(python3 -c "
import json, sys
print(json.dumps({
    'content': sys.argv[1],
    'role': 'user',
    'message_mode': 1,
    'data': {}
}))
" "$PROMPT" 2>/dev/null)
[ -n "$BODY" ] || exit 0

curl -s -X POST "http://localhost:60021/v1/aiservicedesk/tickets/$WORKSPACE_ID/$TICKET_NAME/sendMessage" \
  -H "Authorization: Bearer $DUPLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BODY" > /dev/null 2>&1

exit 0
