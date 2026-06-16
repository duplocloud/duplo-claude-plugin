#!/bin/bash
# Mirror Ticket_send_message request/response to portal conversation (mode=1)

STATE_FILE=".duplocloud/state.toon"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(grep '^workspace_id:' "$STATE_FILE" 2>/dev/null | sed 's/^workspace_id: *//')
TICKET_NAME=$(grep '^active_ticket_name:' "$STATE_FILE" 2>/dev/null | sed 's/^active_ticket_name: *//')
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

source .env 2>/dev/null
MIRROR_MAX_CHARS=${MIRROR_MAX_CHARS:-12000}
QUEUE_FILE=".duplocloud/.mirror_sendmessage_queue.jsonl"
QUEUE_HELPER="$(cd "$(dirname "$0")" && pwd)/mirror_queue.py"
mkdir -p .duplocloud

enqueue_and_flush() {
    local role="$1"
    local text="$2"
    local source="$3"
    [ -n "$text" ] || return 0

    printf '%s' "$text" | python3 "$QUEUE_HELPER" enqueue "$QUEUE_FILE" "$role" "$source" >/dev/null 2>&1
    python3 "$QUEUE_HELPER" flush "$QUEUE_FILE" "$WORKSPACE_ID" "$TICKET_NAME" "$DUPLO_TOKEN" "$MIRROR_MAX_CHARS" >/dev/null 2>&1
}

INPUT=$(cat)

# Mirror request content exactly as sent (preserve role)
REQ_PARSED=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
inp = d.get('tool_input', {}) if isinstance(d, dict) else {}
content = inp.get('content', '') if isinstance(inp, dict) else ''
role = inp.get('role', '') if isinstance(inp, dict) else ''
mode = inp.get('message_mode', '') if isinstance(inp, dict) else ''
if not role:
    role = 'user'
print(str(role))
print(str(mode))
print(str(content))
" 2>/dev/null)

REQ_ROLE=$(printf '%s' "$REQ_PARSED" | sed -n '1p')
REQ_MODE=$(printf '%s' "$REQ_PARSED" | sed -n '2p')
REQ_CONTENT=$(printf '%s' "$REQ_PARSED" | sed '1,2d')

if [ -n "$REQ_CONTENT" ]; then
    case "$REQ_ROLE" in
        user|assistant)
            ;;
        *)
            REQ_ROLE="user"
            ;;
    esac

    # Mirror only record-only messages (mode=1) or messages where mode is absent.
    if [ -z "$REQ_MODE" ] || [ "$REQ_MODE" = "1" ]; then
        enqueue_and_flush "$REQ_ROLE" "$REQ_CONTENT" "api:request"
    fi
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
    enqueue_and_flush "assistant" "$AGENT_REPLY" "api:response"
fi

exit 0
