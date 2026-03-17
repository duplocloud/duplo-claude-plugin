---
name: activate_ticket
description: Activate the next work item (ticket) for the currently active DuploCloud project.
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Check project state:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --check-project
```

- If exit code is **3**: ask the user:
  > "No active project found. Would you like to activate one now? (y/n)"
  - **y** → run the `activate_project` skill inline (follow its steps from the beginning), then re-run `--check-project` and continue.
  - **n** → stop.
- Capture from JSON output: `project_name`, `has_execution_tasks`, `spec_empty`, `plan_empty`.

**Step 2 — Route based on execution tasks:**

*If `has_execution_tasks` is `false`:*

Proceed directly to Step 3 with type `spec_creation`. Do not ask the user — they have already chosen to activate a ticket.

*If `has_execution_tasks` is `true`:*

Ask the user:
> Execution tasks are ready for project `<project_name>`. Would you like to work on an execution task?
> 1. Yes — pick an execution task to work on
> 2. No — resume planning work (spec/plan)

Wait for user selection:
- If user picks **2**: proceed to Step 3 with type `spec_creation`.
- If user picks **1**: proceed to Step 2b.

**Step 2b — Select an execution task:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --list-execution-tasks
```

Parse the JSON output. Extract `total` and `stages`.

If `total` is 0: tell the user "No execution tasks found for this project." and stop.

**If `total` > 10** — first ask the user to select a stage:

Show the numbered stage list:
```
Which stage would you like to work on?
1. <stage_name> (<N> tasks) — <stage_description>
2. <stage_name> (<N> tasks) — <stage_description>
...
```

Wait for the user's stage selection. Then show the tasks in that stage, including ticket info where available:

```
Which task would you like to work on?
1. <task_title> — <ticket_status> (<ticket_name>)
2. <task_title> — no ticket
...
```

**If `total` <= 10** — show all tasks flat across all stages with stage context and ticket info:

```
Which task would you like to work on?
1. [<stage_name>] <task_title> — <ticket_status> (<ticket_name>)
2. [<stage_name>] <task_title> — no ticket
...
```

For each task: if `ticket_name` is present in the JSON, show `<ticket_status> (<ticket_name>)`; otherwise show `no ticket`.

Wait for the user's task selection (number N). Resolve it to the definitive task name, title, and ticket info directly from the `--list-execution-tasks` JSON already in memory:

- **If stage was selected** (total > 10 flow): index into `stages[S-1].tasks[N-1]`
- **If flat list** (total <= 10 flow): flatten all `stages[*].tasks` into a single list and take item `[N-1]`

Capture `name` (UUID) as `task_id` and `title` as `task_title`. Use only these values going forward. Do not guess or recall UUIDs from earlier output.

Also capture `ticket_name` and `ticket_id` if present in the task object — these mean a ticket already exists for this task.

**Step 2c — Check or create ticket for selected task:**

- If `ticket_name` is present and non-empty in the `--get-task-by-index` output: the ticket already exists. Run:
  ```bash
  python3 ~/.duplocloud/bin/duplo_ticket.py --check-task-ticket --task-id <task_id>
  ```
  Then run Step 2d (inProgress), then Step 2e (load context), tell the user "Resuming existing ticket for task '<task_title>'. Here's what we've done so far: [brief summary from context]" and stop.

- If `ticket_name` is absent or empty: no ticket yet. Continue below.

List available agents:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --list-agents
```

Show the numbered agent list to the user and ask:
> Which agent should handle this task? (enter the number)

Wait for the user's selection. Look up the corresponding agent ID (`id:` value in parentheses). Then create the ticket:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --create-execution-task-ticket \
  --task-id <task_id> \
  --agent-id <selected_agent_id>
```

- If exit code is **0**: run Step 2d (inProgress), then Step 2e (load context), tell the user "Ticket created for task '<task_title>'. Let's get to work!" and stop.
- If exit code is **1**: show the error output to the user and stop.

**Step 2d — Move ticket to inProgress:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-ticket-status
```

- If the output is `open`: run:
  ```bash
  python3 ~/.duplocloud/bin/duplo_ticket.py --set-ticket-status --status inProgress
  ```
- If the output is already `inProgress` or any other status: skip.

**Step 2e — Load past context:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-ticket-context
```

Read the full output carefully. It contains the mirrored conversation history from previous sessions on this ticket — prior user messages, Claude responses, decisions made, and work done. Use this to restore your understanding of where the work left off before responding to the user. If the output says "No past messages found", proceed without prior context.

**Step 3 — Activate or create spec ticket:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --activate-ticket --type spec_creation
```

- If exit code is **0** (ticket found and activated): run Step 2d (inProgress), then Step 2e (load context), then continue to Step 5.
- If exit code is **1** (not found): continue to Step 4.

**Step 4 — Create spec ticket:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --list-agents
```

Show the numbered agent list to the user. Write out each numbered item clearly so the user can read the full list. Then ask:
> Which agent should handle this ticket? (enter the number)

Wait for the user's selection. Look up the corresponding agent ID from the list output (the `id:` value in parentheses on the selected line). Then create the ticket:

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --create-ticket \
  --type spec_creation \
  --agent-id <selected_agent_id>
```

- If exit code is **0**: run Step 2d (inProgress), then Step 2e (load context), show the ticket creation output to the user, then continue to Step 5.
- If exit code is **1**: show the error output to the user and stop.

**Step 5 — Prompt based on spec/plan content state:**

Using `spec_empty` and `plan_empty` captured in Step 1:

*Case 1 — Both `spec_empty` and `plan_empty` are `true`:*

Ask the user:
> Both spec and plan are empty. What would you like to do?
> 1. Start writing the spec
> 2. Skip spec and go directly to plan creation

*Case 2 — `spec_empty` is `false`, `plan_empty` is `true`:*

Ask the user:
> A spec exists but the plan is empty. What would you like to do?
> 1. Resume writing the spec
> 2. Move to plan creation

*Case 3 — Both `spec_empty` and `plan_empty` are `false`:*

Ask the user:
> Both spec and plan already have content. Resume work on the plan?

- If the user confirms: delegate to `skills/write_plan/SKILL.md`.
- If the user declines: stop.

**Step 6 — Delegate to write skill:**

Based on the user's choice in Step 5:
- "Start writing spec" or "Resume writing spec" → read and follow `skills/write_spec/SKILL.md`.
- "Skip spec / go to plan", "Move to plan creation", or "Resume plan" → read and follow `skills/write_plan/SKILL.md`.
