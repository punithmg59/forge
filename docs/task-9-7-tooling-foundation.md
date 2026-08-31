# Task 9.7 — Enterprise Tool Registry + Safe Tool Execution Foundation

## Overview

Task 9.7 introduces a **read-only** enterprise tool layer: a registry, centralized executor, authorization, tenant isolation, timeouts, size limits, audit, and three internal tools. This is infrastructure only — **not** autonomous execution.

**Explicitly not implemented:** Task 9.8, public arbitrary tool APIs, write tools (by default), automatic Evidence creation, agent-driven tool loops, external CRM/analytics integrations.

## Architecture

```
Agent (future)
    ↓
ToolExecutor.execute(ToolCall, ToolExecutionContext)
    ↓
ToolRegistry.get_tool(name:version)
    ↓
authorize → validate input → execute (timeout) → validate output
    ↓
ToolResult (structured, safe errors)
    ↓
Optional AgentTask audit (task_type=tool_execution)
```

Agents must **not** call `tool.execute()` directly or import external API clients. The executor is the single security boundary.

## Tool contract

Each tool implements `Tool[InputT, OutputT]` with:

| Field | Purpose |
|-------|---------|
| `name` | Stable identifier (e.g. `company_context`) |
| `version` | Version suffix (e.g. `v1`) → qualified `company_context:v1` |
| `description` | Human-readable summary |
| `category` | `ToolCategory` enum |
| `effect` | `read` or `write` (write rejected at registration unless `tool_allow_write_tools`) |
| `required_permissions` | `ToolPermission` set |
| `input_model` / `output_model` | Pydantic models with `extra="forbid"` |

## Registry

- **Location:** `app/services/tools/registry.py`
- Code-based registry (no DB table — tools are compile-time capabilities).
- `register()`, `get_tool()`, `list_tools()`, `disable_tool()`, `enable_tool()`
- Duplicate qualified names raise `ValueError`.
- Unknown tools raise `ToolNotFoundError` — no silent fallback.
- Write tools raise `ToolWriteNotAllowedError` unless `settings.tool_allow_write_tools` is true.

## Executor

- **Location:** `app/services/tools/executor.py`
- Flow: policy check → resolve → authorize → validate input → execute with timeout → validate output → size check → audit → `ToolResult`.
- Policy limits: max calls per request, max total execution time, input/output bytes, record counts (via `ToolExecutionPolicy` + `settings`).

## Authorization

- **Location:** `app/services/tools/authorization.py`
- Permissions derived from membership role via `permissions_for_role()`.
- `authorize_tool_execution()` runs **before** tool execution.
- `ToolExecutionContext` is built from `CompanyMember` — tools never trust `company_id` in tool arguments.

## Tenant isolation

- All builtin tools filter by `context.company_id` from server-side context.
- Cross-company resource IDs in tool inputs are not accepted (sensitive inputs use `extra="forbid"` and omit `company_id`).

## Timeouts and limits

Configured in `app/core/config.py`:

| Setting | Default |
|---------|---------|
| `tool_default_timeout_ms` | 5000 |
| `tool_external_timeout_ms` | 15000 |
| `tool_max_input_bytes` | 8192 |
| `tool_max_output_bytes` | 65536 |
| `tool_max_records` | 100 |
| `tool_max_calls_per_request` | 10 |
| `tool_max_total_execution_ms` | 30000 |

Timeouts return `TOOL_TIMEOUT` with a safe message. Oversized results return `TOOL_RESULT_TOO_LARGE` without silent truncation.

## Error taxonomy

`ToolErrorCode` in `app/schemas/tool.py`:

- `TOOL_NOT_FOUND`, `TOOL_DISABLED`, `TOOL_UNAUTHORIZED`
- `TOOL_INVALID_INPUT`, `TOOL_INVALID_OUTPUT`
- `TOOL_TIMEOUT`, `TOOL_RESULT_TOO_LARGE`
- `TOOL_EXECUTION_FAILED`, `TOOL_WRITE_NOT_ALLOWED`, `TOOL_POLICY_LIMIT`

Internal exceptions are mapped to safe `ToolResult` fields — no stack traces or provider strings in results.

## Audit and observability

- Reuses `AgentRun` / `AgentTask` with `task_type=tool_execution`.
- Audit payload stores tool name, version, trace_id, success, duration — **not** full inputs/outputs or secrets.
- Structured logs: `tool_execution_started`, `tool_execution_completed`, `tool_execution_failed`.

## Initial read-only tools

| Qualified name | Permission | Returns |
|----------------|------------|---------|
| `company_context:v1` | `company_read` | Company metadata (name, stage, mission, etc.) |
| `objective_status:v1` | `company_read` | Current objective status |
| `customer_evidence:v1` | `customer_read` | Company-scoped evidence summaries |

These reuse existing models/services — not a second Brain.

## Tools are not Brain truth

Tool results are **temporary retrieved data**. They are **not** automatically persisted as Evidence or Learning. Promotion to Company Brain requires explicit future approval workflows.

## Prompt injection boundary

Tool output is **untrusted data**. Tests verify malicious strings are returned in structured `data` fields only — never interpreted as instructions by the tool layer.

## No public execute endpoint

There is no `POST /tools/execute`. Tool execution is an internal service capability invoked by future agent code through `ToolExecutor`.

## Future external integrations

Registry design supports future tools (`github:v1`, `stripe:v1`, `analytics:v1`) behind the same executor, authorization, and audit boundaries.

## Security model

- Centralized executor boundary
- Read-only default; write tools blocked at registration
- Company-scoped context from authenticated membership
- Input/output Pydantic validation with `extra="forbid"`
- Per-request call and time limits
- No secrets in logs or audit records

## Testing

| File | Coverage |
|------|----------|
| `tests/test_tool_registry.py` | Registration, duplicates, disabled, write rejection, lookup speed |
| `tests/test_tool_executor.py` | Input validation, timeout, size limits, policy limits |
| `tests/test_tool_security.py` | Auth, tenant isolation, audit, no mutations, injection, logs |
| `tests/test_internal_tools.py` | Builtin tool behavior |

Run (requires PostgreSQL on `localhost:5433`):

```bash
cd apps/api
pytest -q tests/test_tool_registry.py tests/test_tool_executor.py tests/test_tool_security.py tests/test_internal_tools.py
pytest -q
ruff check app/
```

Registry tests run without a database. Integration tests require Docker (`docker compose up -d`).

## Limitations

- No LLM-driven tool selection in 9.7
- No specialist agents wired to tools yet (foundation only)
- No external API tools
- No write/mutation tools
- Registry is in-process code, not dynamically loaded

## Task 9.8 boundary

Task 9.8 (autonomous / controlled action execution) is **not implemented**. Tools cannot create tasks, approve recommendations, mutate objectives, or write to external systems.
