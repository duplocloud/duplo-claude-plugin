#!/bin/bash
# Mirror user prompt to helpdesk ticket conversation (mode=1, no agent call)

STATE_FILE=".duplocloud/state.toon"
[ -f "$STATE_FILE" ] || exit 0

WORKSPACE_ID=$(grep '^workspace_id:' "$STATE_FILE" 2>/dev/null | sed 's/^workspace_id: *//')
TICKET_NAME=$(grep '^active_ticket_name:' "$STATE_FILE" 2>/dev/null | sed 's/^active_ticket_name: *//')
[ -n "$WORKSPACE_ID" ] && [ -n "$TICKET_NAME" ] || exit 0

INPUT=$(cat)

PROMPT=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null)
[ -n "$PROMPT" ] || exit 0

TRANSCRIPT_PATH=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null)

# Skip slash commands and single-char/digit confirmations (internal UI navigation)
echo "$PROMPT" | python3 -c "
import sys, re
p = sys.stdin.read().strip()
if p.startswith('/') or re.fullmatch(r'[ynYN]|[0-9]+', p):
    sys.exit(1)
" 2>/dev/null || exit 0

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

maybe_mirror_latest_assistant() {
  [ -f "$TRANSCRIPT_PATH" ] || return 0

  DEBUG_LOG=".duplocloud/.mirror_debug.log"
  mkdir -p .duplocloud
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] maybe_mirror_latest_assistant called" >> "$DEBUG_LOG"

  local assistant_text
  assistant_text=$(python3 - "$TRANSCRIPT_PATH" <<'PY'
import json
import sys

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
  raise SystemExit(0)

content = last_assistant.get('content', '')
if isinstance(content, list):
  displayed_text = ''.join(
    c.get('text', '') for c in content
    if isinstance(c, dict) and c.get('type') == 'text'
  )
else:
  displayed_text = str(content)

if not displayed_text.strip():
  raise SystemExit(0)

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

if used_streaming_send:
  raise SystemExit(0)

if displayed_text in mirrored_assistant_contents:
  raise SystemExit(0)

print(displayed_text)
PY
)

  [ -n "$assistant_text" ] || {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] no assistant_text extracted" >> "$DEBUG_LOG"
    return 0
  }

  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] extracted_text_length=$(printf '%s' "$assistant_text" | wc -c)" >> "$DEBUG_LOG"

  local hash_file
  hash_file=".duplocloud/.last_mirrored_assistant_hash"

  local current_hash
  current_hash=$(printf '%s' "$assistant_text" | shasum -a 256 | awk '{print $1}')
  local prev_hash
  prev_hash=$(cat "$hash_file" 2>/dev/null || true)

  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] current_hash=$current_hash prev_hash=$prev_hash" >> "$DEBUG_LOG"

  if [ "$current_hash" != "$prev_hash" ]; then
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] queueing assistant message" >> "$DEBUG_LOG"
    enqueue_and_flush "assistant" "$assistant_text" "prompt:assistant"
    printf '%s' "$current_hash" > "$hash_file"
  else
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] hash match - skipping (duplicate)" >> "$DEBUG_LOG"
  fi
}

DEBUG_LOG=".duplocloud/.mirror_debug.log"
mkdir -p .duplocloud
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] mirror-prompt.sh started, TRANSCRIPT_PATH=$TRANSCRIPT_PATH" >> "$DEBUG_LOG"

maybe_mirror_latest_assistant

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] queueing user prompt" >> "$DEBUG_LOG"
enqueue_and_flush "user" "$PROMPT" "prompt:user"

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] mirror-prompt.sh completed" >> "$DEBUG_LOG"

exit 0
