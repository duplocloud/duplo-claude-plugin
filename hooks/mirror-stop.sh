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

last_assistant = None
for msg in reversed(messages):
    if msg.get('role') == 'assistant':
        last_assistant = msg
        break

if not last_assistant:
    sys.exit(0)

content = last_assistant.get('content', '')

if isinstance(content, list):
    displayed_text = ''.join(
        c.get('text', '') for c in content
        if isinstance(c, dict) and c.get('type') == 'text'
    )
else:
    displayed_text = str(content)

if not displayed_text.strip():
    sys.exit(0)

mirrored_assistant_contents = []
used_streaming_send = False

if isinstance(content, list):
    for block in content:
        if not isinstance(block, dict) or block.get('type') != 'tool_use':
            continue

        tool_name = str(block.get('name', ''))
        tool_input = block.get('input', {})

        if 'Ticket_send_message_streaming' in tool_name:
            used_streaming_send = True

        if 'Ticket_send_message' in tool_name and isinstance(tool_input, dict):
            if str(tool_input.get('role', '')) == 'assistant' and str(tool_input.get('message_mode', '')) == '1':
                mirrored_assistant_contents.append(str(tool_input.get('content', '')))

# Streaming already mirrors conversation in-ticket; avoid duplicates.
if used_streaming_send:
    sys.exit(1)

# Skip only when the exact displayed assistant text was already mirrored.
if displayed_text in mirrored_assistant_contents:
    sys.exit(1)

print(displayed_text)
" "$TRANSCRIPT_PATH" 2>/dev/null)
[ -n "$RESULT" ] || exit 0

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

enqueue_and_flush "assistant" "$RESULT" "stop:assistant"

exit 0
