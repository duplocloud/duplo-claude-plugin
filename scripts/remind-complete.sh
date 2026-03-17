#!/bin/bash
STATE_FILE=".duplocloud/state.json"
[ ! -f "$STATE_FILE" ] && exit 0

TICKET=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('active_ticket_id',''))" 2>/dev/null)
[ -z "$TICKET" ] && exit 0

TITLE=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('active_ticket_title',''))" 2>/dev/null)
echo "Active ticket: [$TITLE] ($TICKET). If this work is complete, call the DuploCloud MCP tool to mark the ticket done and update .duplocloud/state.json active_ticket_id to the next ticket (or clear it if all done)."
exit 0
