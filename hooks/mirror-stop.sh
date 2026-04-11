#!/bin/bash
# Mirror Claude's own lifecycle messages to helpdesk ticket (mode=1, no agent call).
# Skips mirroring when the last action was a Ticket_send_message_streaming or
# Ticket_send_message call — those conversations are already in the ticket via mode=0.

STATE_FILE=".duplocloud/state.toon"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(grep '^workspace_id:' "$STATE_FILE" 2>/dev/null | sed 's/^workspace_id: *//')
TICKET_NAME=$(grep '^active_ticket_name:' "$STATE_FILE" 2>/dev/null | sed 's/^active_ticket_name: *//')
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

# Transcript is at a file path, not inline
TRANSCRIPT_PATH=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null)
[ -f "$TRANSCRIPT_PATH" ] || exit 0

RESULT=$(python3 -c "
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

# Check if the last assistant message used Ticket_send_message_streaming or Ticket_send_message.
# If so, those conversations are already in the ticket — do not mirror again.
for msg in reversed(messages):
    if msg.get('role') == 'assistant':
        content = msg.get('content', [])
        if isinstance(content, list):
            for block in content:
                if block.get('type') == 'tool_use':
                    tool = block.get('name', '')
                    if 'Ticket_send_message' in tool:
                        sys.exit(1)  # skip — already in ticket
        break

# Find last assistant message text
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
[ -n "$RESULT" ] || exit 0

source .env 2>/dev/null

BODY=$(python3 -c "
import json, sys
print(json.dumps({
    'content': sys.argv[1],
    'role': 'assistant',
    'message_mode': 1,
    'data': {}
}))
" "$RESULT" 2>/dev/null)
[ -n "$BODY" ] || exit 0

curl -s -X POST "http://localhost:60021/v1/aiservicedesk/tickets/$WORKSPACE_ID/$TICKET_NAME/sendMessage" \
  -H "Authorization: Bearer $DUPLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BODY" > /dev/null 2>&1

exit 0
