#!/bin/bash
# Mirror Ticket_send_message request/response to portal conversation (mode=1)

STATE_FILE=".duplocloud/state.json"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('workspace_id',''))" 2>/dev/null)
TICKET_NAME=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('active_ticket_name',''))" 2>/dev/null)
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

source .env 2>/dev/null

INPUT=$(cat)

# Mirror user message from request content
USER_MSG=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
inp = d.get('tool_input', {})
print(inp.get('content', ''))
" 2>/dev/null)

if [ -n "$USER_MSG" ]; then
    BODY=$(python3 -c "
import json, sys
print(json.dumps({'content': sys.argv[1], 'role': 'user', 'message_mode': 1, 'data': {}}))
" "$USER_MSG" 2>/dev/null)
    [ -n "$BODY" ] && curl -s -X POST \
        "http://localhost:60021/v1/aiservicedesk/tickets/$WORKSPACE_ID/$TICKET_NAME/sendMessage" \
        -H "Authorization: Bearer $DUPLO_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$BODY" > /dev/null 2>&1
fi

# Mirror agent response from tool result
AGENT_REPLY=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
resp = d.get('tool_response', '')
if isinstance(resp, list):
    # MCP tool format: list of text blocks directly
    print(''.join(c.get('text', '') for c in resp if isinstance(c, dict) and c.get('type') == 'text'))
elif isinstance(resp, dict):
    content = resp.get('content', '')
    if isinstance(content, list):
        print(''.join(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text'))
    else:
        print(content)
elif isinstance(resp, str):
    print(resp)
" 2>/dev/null)

if [ -n "$AGENT_REPLY" ]; then
    BODY=$(python3 -c "
import json, sys
print(json.dumps({'content': sys.argv[1], 'role': 'assistant', 'message_mode': 1, 'data': {}}))
" "$AGENT_REPLY" 2>/dev/null)
    [ -n "$BODY" ] && curl -s -X POST \
        "http://localhost:60021/v1/aiservicedesk/tickets/$WORKSPACE_ID/$TICKET_NAME/sendMessage" \
        -H "Authorization: Bearer $DUPLO_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$BODY" > /dev/null 2>&1
fi

exit 0
