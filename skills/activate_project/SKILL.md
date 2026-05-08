---
name: activate-project
description: "Log in to DuploCloud, select a workspace and project, and set the active project context. Use when the user wants to switch DuploCloud projects, connect to a different workspace, set up duplo credentials, or start a new DuploCloud session."
disable-model-invocation: false
---

Follow these steps in order:

**Step 1 — Read current state:**

```bash
python3 ~/.duplocloud/bin/duplo_activate.py --check-state
```

Capture `workspace` and `project` from the JSON output. This makes no API call.

**Step 2 — Workspace: resume or switch?**

- If `workspace` is **not null** in the Step 1 output: ask the user:
  > "You are currently working as **\<workspace.name\>**. Continue with this workspace? (y/n)"
  - **y** → skip to Step 5 (project resume check)
  - **n** → continue to Step 3

- If `workspace` is **null**: continue to Step 3.

**Step 3 — List workspaces (also validates credentials):**

```bash
python3 ~/.duplocloud/bin/duplo_activate.py --list-workspaces
```

- If exit code is **3** (no auth or invalid token): tell the user:
  > "Your credentials file will open in VSCode. Fill in `base_url` and `token`, then save and close. If VSCode is not available, a terminal command will be shown instead."

  Then run:
  ```bash
  python3 ~/.duplocloud/bin/duplo_activate.py --edit-auth
  ```

  - If exit code is **0**: re-run `--list-workspaces`.
    - If `--list-workspaces` still returns exit **3**: tell the user "Credentials still invalid — please re-check the values." and re-run `--edit-auth`.
  - If exit code is **1** (VSCode not available): show the printed terminal command to the user and tell them to run it, then re-run `/duplo:activate_project` once they're done.

- If exit code is **0**: show the numbered workspace list to the user. Write out each numbered item clearly in your response text so the user can read the full list without expanding tool output.
  - If the output contains "(Only one workspace found — will be auto-selected.)": automatically proceed to Step 4 with N=1 (skip asking the user).
  - If multiple workspaces are listed: ask the user:
    > "Which workspace are you working as? (enter the number)"

**Step 4 — Set workspace:**

```bash
python3 ~/.duplocloud/bin/duplo_activate.py --set-workspace <N>
```

(Replace `<N>` with the number the user provided, or `1` if auto-selected.)

After setting the workspace, the old project is cleared from state. Continue directly to Step 6 (always show project list after an workspace change).

**Step 5 — Project: resume or switch? (only reached if workspace was NOT changed in this run)**

- If `project` is **not null** in the Step 1 output: ask the user:
  > "Active project: **\<project.name\>**. Continue with this project? (y/n)"
  - **y** → show a summary of the active workspace and project, then continue to Step 5a.
  - **n** → continue to Step 6.

- If `project` is **null**: continue to Step 6.

**Step 5a — Sync local files (same project):**

Check if local files exist:
- `.duplocloud/spec.md`
- `.duplocloud/plan.md`

If **neither** file exists: silently download both (proceed to Step 5b).

If **one or both** exist: ask the user:
> "Local spec/plan files exist. Overwrite with the latest versions from the platform? (y/n)"
- **n** → keep local files, skip to Step 10 (health display).
- **y** → proceed to Step 5b.

**Step 5b — Download spec and plan:**

Run the **Sync spec/plan** sub-procedure (below), then tell the user which files were updated and continue to Step 10.

**Step 6 — List projects (filtered by workspace in state):**

```bash
python3 ~/.duplocloud/bin/duplo_activate.py --list
```

Show the numbered project list to the user. Write out each numbered item clearly in your response text so the user can read the full list without expanding tool output.

**Step 7 — Ask user to select project:**

> "Which project would you like to activate? (enter the number)"

```bash
python3 ~/.duplocloud/bin/duplo_activate.py --select <N>
```

(Replace `<N>` with the number the user provided.)

**Step 8 — Show the confirmation output to the user.**

**Step 9 — Sync local files (new project — always overwrite):**

Run the **Sync spec/plan** sub-procedure (below). Tell the user which files were written (or "no platform content yet" if both were empty), then continue to Step 10.

**Step 10 — Show project health:**

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --check-project
```

- If exit code is **3**: tell the user "Project state missing — please re-run /duplo:activate_project." and stop.
- If exit code is **1**: show the error and stop.
- If exit code is **0**: parse the JSON and display a health summary:

> **Project:** `<project_name>`
>
> | Artifact | Status |
> |----------|--------|
> | Spec     | Approved / Draft (local file exists) / Not started |
> | Plan     | Approved / Draft (local file exists) / Not started |

Determine artifact status independently for each artifact:

**Spec status:**
- `action` = `"plan"` or `"none"` → **Approved**
- `action` = `"spec"` and `.duplocloud/spec.md` exists → **Draft**
- `action` = `"spec"` and `.duplocloud/spec.md` does not exist → **Not started**

**Plan status:**
- `action` = `"none"` → **Approved**
- `action` != `"none"` and `.duplocloud/plan.md` exists → **Draft**
- `action` != `"none"` and `.duplocloud/plan.md` does not exist → **Not started**

Then ask the user whether to proceed:
- `"spec"` → ask: "Would you like to activate the spec ticket now? (y/n)"
  - **y** → run the `activate_ticket` skill inline (follow its steps from the beginning).
  - **n** → stop.
- `"plan"` → ask: "Spec is approved. Would you like to activate the plan ticket now? (y/n)"
  - **y** → run the `activate_ticket` skill inline (follow its steps from the beginning).
  - **n** → stop.
- `"none"` + `has_execution_tasks` = `true` → tell the user "Both spec and plan are approved. Execution tasks are ready." then ask: "Would you like to pick up an execution task now? (y/n)"
  - **y** → run the `activate_ticket` skill inline (follow its steps from the beginning, starting at Step 2b since `has_execution_tasks` is already known to be `true`).
  - **n** → stop.
- `"none"` + `has_execution_tasks` = `false` → tell the user "Both spec and plan are approved — waiting for the platform to generate execution tasks." and stop.

---

## Sync spec/plan (sub-procedure)

Used by Steps 5b and 9. Downloads the latest spec and plan from the platform into local files.

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-spec
```
- If output is non-empty: save it to `.duplocloud/spec.md`.
- If output is empty: leave any existing `.duplocloud/spec.md` unchanged (no platform content yet).

```bash
python3 ~/.duplocloud/bin/duplo_ticket.py --get-plan
```
- If output is non-empty: save it to `.duplocloud/plan.md`.
- If output is empty: leave any existing `.duplocloud/plan.md` unchanged.
