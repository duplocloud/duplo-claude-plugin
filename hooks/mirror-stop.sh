#!/bin/bash
# Mirror Claude's response to helpdesk ticket conversation (mode=1, no agent call)

STATE_FILE=".duplocloud/state.json"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('workspace_id',''))" 2>/dev/null)
TICKET_NAME=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('active_ticket_name',''))" 2>/dev/null)
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

# Transcript is at a file path, not inline
TRANSCRIPT_PATH=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null)
[ -f "$TRANSCRIPT_PATH" ] || exit 0

RESPONSE=$(python3 -c "
import json, sys

transcript_path = sys.argv[1]
messages = []
with open(transcript_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except Exception:
            continue

# Find last assistant message
for msg in reversed(messages):
    if msg.get('role') == 'assistant':
        content = msg.get('content', '')
        if isinstance(content, list):
            text = ''.join(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text')
        else:
            text = str(content)
        if text.strip():
            print(text)
        break
" "$TRANSCRIPT_PATH" 2>/dev/null)
[ -n "$RESPONSE" ] || exit 0

source .env 2>/dev/null

BODY=$(python3 -c "
import json, sys
print(json.dumps({
    'content': sys.argv[1],
    'role': 'assistant',
    'message_mode': 1,
    'data': {}
}))
" "$RESPONSE" 2>/dev/null)
[ -n "$BODY" ] || exit 0

curl -s -X POST "http://localhost:60021/v1/aiservicedesk/tickets/$WORKSPACE_ID/$TICKET_NAME/sendMessage" \
  -H "Authorization: Bearer $DUPLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BODY" > /dev/null 2>&1

exit 0
