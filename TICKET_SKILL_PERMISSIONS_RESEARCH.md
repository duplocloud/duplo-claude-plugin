# DuploCloud Ticket API - Skill Permissions & Context Research

**Deep scan of duplo-claude-plugin codebase**  
**Date:** April 22, 2026

---

## Executive Summary

Based on comprehensive analysis of the duplo-claude-plugin codebase, the Ticket creation API **does NOT currently expose explicit `allowedSkills` or `allowContext` fields**. Instead, skill permissions and agent context are controlled through:

1. **`ticketContextForAgent`** — Controls which scopes and personas can act on the ticket
2. **`originContext.metadata`** — Carries ticket type and task binding information
3. **`platform_context.project_context`** — Provides execution phase information (spec/plan/execution)

---

## Finding 1: Ticket_create API Payloads

### Three Ticket Creation Patterns

#### Pattern A: Standalone Ticket
```json
{
  "title": "<user-provided title>",
  "aiAgentId": "<agent_id>",
  "workspaceId": "<workspace_id>",
  "origin": "api"
}
```
**Source:** [skills/activate_ticket/SKILL.md](skills/activate_ticket/SKILL.md#L191)  
**Use case:** General purpose ticket, no project binding

#### Pattern B: Spec/Plan Creation Ticket
```json
{
  "title": "<project_name> — <spec_creation or plan_creation>",
  "aiAgentId": "<agent_id>",
  "workspaceId": "<workspace_id>",
  "origin": "api",
  "originContext": {
    "type": "Project",
    "id": "<project_id>",
    "subType": "<project_ticket_type>"
  }
}
```
**Source:** [skills/activate_ticket/SKILL.md](skills/activate_ticket/SKILL.md#L201)  
**Field Details:**
- `originContext.type` = `"Project"` (or other resource types)
- `originContext.id` = The project UUID
- `originContext.subType` = `"project-planner"` (for spec/plan tickets)

#### Pattern C: Execution Task Ticket
```json
{
  "title": "<task_title>",
  "aiAgentId": "<agent_id>",
  "workspaceId": "<workspace_id>",
  "origin": "api",
  "ticketContextForAgent": {
    "personaIds": ["<persona_ids>"]
  },
  "originContext": {
    "type": "Project",
    "id": "<project_id>",
    "subType": "execution",
    "metadata": { 
      "taskId": "<task_id>",
      "projectType": "plan_execution"
    }
  }
}
```
**Source:** [skills/activate_ticket/SKILL.md](skills/activate_ticket/SKILL.md#L216)  
**Field Details:**
- `origin` = `"api"` (when created by skills; `"helpdesk"` when created from portal)
- `originContext.subType` = `"execution"` (for execution task tickets)
- `originContext.metadata.taskId` = UUID of the execution task
- `originContext.metadata.projectType` = `"plan_execution"`

#### Pattern D: AI Planner Ticket (Extended)
```json
{
  "title": "<project_name> AI Planner",
  "aiAgentId": "<agent_id>",
  "workspaceId": "<workspace_id>",
  "source": "helpdesk",
  "ticketContextForAgent": {
    "scopeIds": ["<scope_id1>", "<scope_id2>"],
    "personaIds": ["<persona_id1>", "<persona_id2>"]
  },
  "originContext": {
    "type": "Project",
    "id": "<project_id>",
    "subType": "project-planner",
    "metadata": { "projectType": "spec_creation" }
  }
}
```
**Source:** [skills/ai_planner/SKILL.md](skills/ai_planner/SKILL.md#L67)  
**Key difference:** Includes `ticketContextForAgent` with scopes and personas

---

## Finding 2: Permission/Context Fields

### `ticketContextForAgent` Object
**Purpose:** Controls which scopes and personas can interact with the ticket  
**Availability:** Optional, used primarily in AI Planner ticket creation  
**Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `scopeIds` | `string[]` | Array of scope IDs from workspace | `["scope-123", "scope-456"]` |
| `personaIds` | `string[]` | Array of persona IDs from workspace | `["persona-dev", "persona-ops"]` |

**Fetch source:**
```
Call `duplo-helpdesk::Workspaces_get_scopes` with workspace_id
Call `duplo-helpdesk::Workspaces_get_personas` with workspace_id
```

**Code reference:**
```markdown
- Collect all scope IDs as `scope_ids` (array of `id` from each scope in the response).
- Collect all persona IDs as `persona_ids` (array of `id` from each persona in the response).
- If either call fails or returns empty, use `[]` for that field — do not block ticket creation.
```

### `originContext.metadata` Object
**Purpose:** Carries contextual information about the ticket's origin and type  
**Fields found:**

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `taskId` | `string` | UUID | Links execution ticket to a specific task |
| `projectType` | `string` | `"spec_creation"`, `"plan_execution"` | Indicates ticket phase/type |

**Example:**
```json
"originContext": {
  "type": "Project",
  "id": "<project_id>",
  "subType": "plan_execution",
  "metadata": {
    "taskId": "<task_uuid>",
    "projectType": "plan_execution"
  }
}
```

---

## Finding 3: Execution Context via `platform_context`

### `platform_context` in Message Streaming
**Used when:** Sending messages to agent via `Ticket_send_message_streaming`  
**Purpose:** Provides runtime context about what phase/artifact the agent is working on

#### Structure
```json
{
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "spec_creation|plan_creation|plan_execution",
      "project_id": "<project_id>",
      "spec_content": "<optional: for plan/execution phases>",
      "plan_content": "<optional: for execution phase>"
    }
  }
}
```

### Phase-Specific Variants

#### Spec Creation Phase
```json
{
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "spec_creation",
      "project_id": "<project_id>"
    }
  }
}
```
**Source:** [skills/ai_planner/SKILL.md](skills/ai_planner/SKILL.md#L136)

#### Plan Creation Phase
```json
{
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "plan_creation",
      "project_id": "<project_id>",
      "spec_content": "<full spec markdown from approved spec>"
    }
  }
}
```
**Source:** [skills/ai_planner/SKILL.md](skills/ai_planner/SKILL.md#L178)

#### Execution Phase
```json
{
  "platform_context": {
    "duplo_base_url": "<DUPLO_HELPDESK_URL>",
    "duplo_token": "<DUPLO_TOKEN>",
    "project_context": {
      "ticket_type": "plan_execution",
      "project_id": "<project_id>",
      "spec_content": "<full spec content>",
      "plan_content": "<full plan content>"
    }
  }
}
```
**Source:** [skills/ai_planner/SKILL.md](skills/ai_planner/SKILL.md#L221)

---

## Finding 4: Complete Ticket Creation Workflow Example

### Step 1: Fetch Workspace Context
```bash
# Fetch scopes
Call `duplo-helpdesk::Workspaces_get_scopes` with id = workspace_id

# Fetch personas  
Call `duplo-helpdesk::Workspaces_get_personas` with id = workspace_id

# Extract arrays of IDs from responses
scope_ids = [<scope.id from each scope in response>]
persona_ids = [<persona.id from each persona in response>]
```

### Step 2: Create Ticket with Full Context
```json
POST /v1/aiservicedesk/tickets/{workspaceId}

{
  "title": "AI Planner for ProjectWeb",
  "aiAgentId": "agent-123",
  "workspaceId": "workspace-abc",
  "source": "helpdesk",
  "ticketContextForAgent": {
    "scopeIds": ["scope-cloud", "scope-k8s"],
    "personaIds": ["persona-devops", "persona-security"]
  },
  "originContext": {
    "type": "Project",
    "id": "project-789",
    "subType": "project-planner",
    "metadata": {
      "projectType": "spec_creation"
    }
  },
  "tenantId": "workspace-abc",
  "platform_context": {
    "duplo_base_url": "https://helpdesk.duplocloud.com",
    "duplo_token": "<bearer_token>"
  }
}
```

### Step 3: Send Messages with Project Context
```json
POST /v1/aiservicedesk/tickets/{workspaceId}/{ticketName}/send-message-streaming

{
  "workspaceId": "workspace-abc",
  "ticketName": "WORKSPACE-42",
  "content": "Create a spec for a multi-tenant SaaS platform...",
  "message_mode": 0,
  "data": {},
  "platform_context": {
    "duplo_base_url": "https://helpdesk.duplocloud.com",
    "duplo_token": "<bearer_token>",
    "project_context": {
      "ticket_type": "spec_creation",
      "project_id": "project-789"
    }
  }
}
```

---

## Finding 5: Metadata Structure in Detail

### Metadata is NOT Flexible User-Defined
Based on the codebase analysis, `metadata` in `originContext` is **not a flexible key-value store**. It contains:

1. **For spec/plan tickets:**
   - `projectType` — Required field indicating `"spec_creation"` or `"plan_execution"`

2. **For execution task tickets:**
   - `taskId` — Required field binding ticket to specific task UUID
   - `projectType` — Type of ticket being created

### Metadata Usage in Code
```python
# From codebase patterns:
"metadata": {
    "projectType": ticket_type,  # "spec_creation" or "plan_execution"
    "taskId": task_id,           # Only for execution tickets
}
```

---

## Finding 6: What's NOT Supported

### Explicitly Absent Fields
The following fields were **NOT found** anywhere in the codebase:

| Field Name | Status |
|-----------|--------|
| `allowedSkills` | ❌ Not found |
| `allowContext` | ❌ Not found |
| `skillRestrictions` | ❌ Not found |
| `allowedCapabilities` | ❌ Not found |
| `skillPermissions` | ❌ Not found |
| `restrictedActions` | ❌ Not found |
| `allowedToolCalls` | ❌ Not found |

### Conclusion
**The current API does not support explicit skill/capability restrictions at the ticket creation level.** Permission control appears to be handled at:
- **Scope level** (via `scopeIds` in `ticketContextForAgent`)
- **Persona level** (via `personaIds` in `ticketContextForAgent`)
- **Agent level** (via `aiAgentId` assignment)

---

## Finding 7: File References Summary

### Core Skill Files with Ticket Examples
- **[skills/activate_ticket/SKILL.md](skills/activate_ticket/SKILL.md)** — Three ticket creation patterns (standalone, spec/plan, execution task)
- **[skills/ai_planner/SKILL.md](skills/ai_planner/SKILL.md)** — AI Planner ticket with scopeIds/personaIds and phase-specific platform_context
- **[CLAUDE.md](CLAUDE.md)** — Agent communication protocol and platform_context details

### Configuration Files
- **[.mcp.json](.mcp.json)** — MCP server configuration with Swagger/OpenAPI reference
- **[CHANGELOG.md](CHANGELOG.md)** — Documents removal of Python scripts, migration to MCP tools

### Documentation References
- **TOON format abbreviation table:** `metaData` → `mdata`, `approvalState` → `aprv`
- **No explicit Swagger schema in repo** — Tools are auto-generated from remote helpdesk Swagger spec

---

## Summary of API Fields

### Ticket_create Request Parameters

```
Root Parameters:
├── title* (string) — Ticket display name
├── aiAgentId* (string) — Agent UUID assigned to ticket
├── workspaceId* (string) — Workspace UUID
├── origin (string, optional) — "api" or "helpdesk"
├── source (string, optional) — "helpdesk"
├── description (string, optional) — Ticket description
├── ticketContextForAgent (object, optional)
│   ├── scopeIds (string[])
│   └── personaIds (string[])
├── originContext (object, optional)
│   ├── type (string) — "Project" or other resource types
│   ├── id (string) — Resource UUID
│   ├── subType (string) — "project-planner", "plan_execution", etc.
│   └── metadata (object)
│       ├── projectType (string) — "spec_creation", "plan_execution"
│       └── taskId (string) — Task UUID (execution tickets only)
├── tenantId (string, optional) — Same as workspaceId
└── platform_context (object, optional)
    ├── duplo_base_url (string)
    ├── duplo_token (string)
    └── project_context (object)
        ├── ticket_type (string)
        ├── project_id (string)
        ├── spec_content (string, optional)
        └── plan_content (string, optional)
```

---

## Recommendations

### For Future Implementation of Skill Permissions

If the backend adds support for `allowedSkills` or `allowContext` fields, they would likely follow this pattern:

```json
{
  "originContext": {
    "type": "Project",
    "id": "<project_id>",
    "subType": "project-planner",
    "metadata": {
      "projectType": "spec_creation",
      "allowedSkills": ["spec-generation", "requirements-analysis"],
      "restrictedActions": ["code-generation", "deployment"]
    }
  }
}
```

However, **this is NOT currently supported** in the API.

### Current Permission Model

The permission model is **role/scope/persona-based**:
1. **Agent assignment** — Select which agent can work on the ticket
2. **Scope assignment** — Restrict to specific infrastructure scopes
3. **Persona assignment** — Restrict to specific operational personas
4. **Origin context** — Indicate ticket type and binding (project, task)

---

## Additional Notes

- The API uses **TOON format** for responses (compact JSON with abbreviated keys)
- Tools are **auto-generated from Swagger spec** at `{DUPLO_HELPDESK_URL}/swagger`
- No local Swagger schema file exists in this repo (dynamically fetched)
- Ticket lifecycle is managed through separate endpoints:
  - `Ticket_get_origin_context_list` — List tickets by origin
  - `Ticket_put_status` — Update ticket status
  - `Ticket_put_assignee` — Reassign to different agent
  - `Ticket_send_message_streaming` — Send messages with platform_context

---

**Research Date:** April 22, 2026  
**Scanned:** All `.md` files, config files, and 50+ grep patterns  
**Verdict:** No explicit skill permission fields found in current API implementation.
