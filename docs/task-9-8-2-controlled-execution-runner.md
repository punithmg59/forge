# Task 9.8.2 — Controlled Autonomous Execution Runner

## Overview

Task 9.8.2 implements the first real execution runner for Forge's controlled autonomous execution engine. It enables **approved, read-only execution plans** to execute through the `ToolExecutor` boundary.

The runner may **only** execute:
- Already-approved execution plans (verified via server-side `Approval` records)
- Registered read-only tools (`company_context:v1`, `objective_status:v1`, `customer_evidence:v1`)

---

## Architecture

```
Authenticated Founder / User
          ↓
  CompanyMember (authoritative identity)
          ↓
  ExecutionRequest (with ExecutionIdentity)
          ↓
  ExecutionRunner.run()
          ↓
  ┌─────────────────────────────────┐
  │  1. Tenant isolation check      │  assert_execution_tenant()
  │  2. Lifecycle state guard       │  cancelled/terminal fast-fail
  │  3. Plan validation             │  validate_execution_plan()
  │  4. Approval verification       │  verify_execution_approved() [DB]
  │  5. Sequential step loop        │  for step in sorted(steps):
  │     a. Idempotency skip         │    if already succeeded → skip
  │     b. Deadline enforcement     │    if now >= deadline → fail
  │     c. Tool call via executor   │    ToolExecutor.execute(call, context)
  │     d. Retry on transient error │    per RetryPolicy
  │     e. Record step result       │    ExecutionStepResult
  └─────────────────────────────────┘
          ↓
  ExecutionResult (succeeded / failed)
          ↓
  Audit (via ToolExecutor → AgentTask)
```

---

## Execution Lifecycle

### Execution statuses

```
requested → planned → waiting_for_approval → approved → running → succeeded
                                                                 ↘ failed → retrying → running
                                          ↘ cancelled (from any non-terminal)
```

**Terminal statuses**: `succeeded`, `cancelled`

### Step statuses

```
pending → running → succeeded
               ↘ failed → running (retry)
               ↘ cancelled
```

**Terminal statuses**: `succeeded`, `failed`, `skipped`, `cancelled`

---

## Approval Boundary

Approval is **server-authoritative**. The runner:

1. Queries the `approvals` table for a row with:
   - `company_id` = authenticated membership's `company_id`
   - `agent_task_id` = `plan_agent_task_id`
   - `action_type` = `"execution"`
   - `status` = `"approved"`

2. If no such record exists → raises `ExecutionNotApprovedError` → **zero tools execute**.

The runner **cannot**:
- Create its own approval record
- Modify an existing approval record
- Accept `approval=true` from any frontend payload, LLM output, or JSON field

---

## Tool Execution Boundary

Every tool invocation **must** go through `ToolExecutor.execute()`:

```
ExecutionRunner
    → ToolExecutor.execute(call, context)
        → is_tool_enabled() / get_tool()
        → authorize_tool_execution()
        → _validate_input()
        → asyncio.wait_for(tool.execute(...), timeout)
        → _validate_output()
        → _enforce_output_size()
        → persist_tool_execution_audit()
```

The runner **cannot** call `tool.execute()`, `tool.run()`, or `tool.handler()` directly.

---

## Read-Only Tools (Task 9.8.2)

| Tool | Qualified Name | Effect |
|------|---------------|--------|
| Company Context | `company_context:v1` | READ |
| Objective Status | `objective_status:v1` | READ |
| Customer Evidence | `customer_evidence:v1` | READ |

**Rejected at plan validation:**
- Any unknown tool → `ExecutionPlanError`
- Any tool with `effect=WRITE` → `ExecutionPlanError`
- Any disabled tool → `ExecutionPlanError`

---

## State Transitions

### Execution state machine

| From | To | Condition |
|------|-----|----------|
| `approved` | `running` | On `runner.run()` invocation |
| `failed` | `retrying` | On re-invocation with prior failed results |
| `retrying` | `running` | At start of retry loop |
| `running` | `succeeded` | All steps succeeded |
| `running` | `failed` | Any step failed non-retryably |
| Any non-terminal | `cancelled` | Via `orchestrator.cancel_execution()` |

Invalid transitions raise `ExecutionStateError`.

### Step state machine

| From | To | Condition |
|------|-----|----------|
| `pending` | `running` | Step starts |
| `failed` | `running` | Retry attempt |
| `running` | `succeeded` | Tool returned success |
| `running` | `failed` | Tool failed, retry exhausted or non-retryable |

---

## Retry Behavior

Retry is governed by `RetryPolicy` on each `ExecutionStep` and `ExecutionRuntimePolicy` limits:

| Error Code | Retryable? |
|-----------|-----------|
| `TOOL_TIMEOUT` | ✅ Yes |
| `TOOL_EXECUTION_FAILED` | ✅ Yes |
| `TOOL_NOT_FOUND` | ❌ No |
| `TOOL_DISABLED` | ❌ No |
| `TOOL_UNAUTHORIZED` | ❌ No |
| `TOOL_INVALID_INPUT` | ❌ No |
| `TOOL_INVALID_OUTPUT` | ❌ No |
| `TOOL_WRITE_NOT_ALLOWED` | ❌ No |
| `TOOL_RESULT_TOO_LARGE` | ❌ No |
| `TOOL_POLICY_LIMIT` | ❌ No |

**Retry is synchronous within the same `run()` invocation.** No background retry workers.

---

## Timeout Behavior

| Limit | Source | Action on Breach |
|-------|--------|-----------------|
| `max_total_duration_ms` | `ExecutionRuntimePolicy` | Stop execution, mark `failed` |
| `max_tool_calls_per_step` | `ExecutionRuntimePolicy` | Stop step, mark `failed` |
| Per-step `timeout_ms` | `ExecutionStep.timeout_ms` | Passed to `ToolExecutor` as `timeout_override_ms` |
| Tool category timeout | `ToolExecutionPolicy` | Enforced by `ToolExecutor` |

---

## Tenant Isolation

**Authoritative source**: `CompanyMember` from the authenticated session.

1. `ExecutionIdentity.company_id` is set from `membership.company_id` at identity creation time — never from request payloads.
2. `assert_execution_tenant()` verifies `identity.company_id == membership.company_id` before any logic runs.
3. `ToolExecutionContext.company_id` is set from `membership.company_id` — tools cannot access other tenants' data.

**Tests verify:**
- Company A user cannot execute Company B plan → `ExecutionScopeError`
- `ToolExecutionContext.company_id` always equals the authenticated company

---

## Idempotency

Calling `runner.run()` multiple times is safe:

- If `execution.status == "succeeded"` → return existing result immediately, no tool calls.
- If a step's `prior_results` contains `status="succeeded"` → skip that step.
- Only unfinished or failed steps are re-attempted.

---

## Failure Semantics

### Safe error structure

Every step failure produces a `StepExecutionError`:

```python
{
    "code": "TOOL_TIMEOUT",      # from ToolErrorCode enum
    "message": "Tool execution timed out.",  # safe, scrubbed
    "retryable": True / False
}
```

**Secrets are scrubbed**: If an error message contains `api_key`, `password`, `secret`, `authorization`, or `bearer`, it is replaced with `"Tool execution failed."`.

### Partial execution

If a step fails mid-execution:
- Preceding succeeded steps remain `succeeded` in `step_results`
- The execution status becomes `failed`
- A subsequent `run()` with `prior_results` will skip succeeded steps and retry the failed one

---

## Observability

### Structured log events

| Event | Fields |
|-------|--------|
| `execution_started` | execution_id, company_id, trace_id, agent_type |
| `execution_step_started` | execution_id, step_id, tool_name, trace_id |
| `execution_step_succeeded` | execution_id, step_id, tool_name, duration_ms |
| `execution_step_failed` | execution_id, step_id, tool_name, error_code |
| `execution_retry` | execution_id, step_id, attempt |
| `execution_completed` | execution_id, company_id, trace_id, status, total_ms |

**Never logged**: API keys, authorization headers, credentials, secrets, or unrestricted tool payloads.

### Execution metrics

`ExecutionRunMetrics` records:
- `validation_ms`: time for plan validation
- `tool_execution_ms`: cumulative tool call time
- `persistence_ms`: DB write time (reserved)
- `total_ms`: wall-clock total

---

## Audit Model

Every tool execution is audited via `ToolExecutor` → `persist_tool_execution_audit()`:

| Field | Value |
|-------|-------|
| `company_id` | from `ToolExecutionContext` |
| `agent_type` | from `ToolExecutionContext` |
| `task_type` | `"tool_execution"` |
| `trace_id` | from `ToolCall` |
| `tool_name` | tool name |
| `tool_version` | tool version |
| `status` | `"completed"` or `"failed"` |
| `error_code` | error code if failed |
| `duration_ms` | tool execution time |

**Not audited by runner**: Evidence, Learning, Objective, Approval, Brain records.

---

## Explicit Limitations (Task 9.8.2)

| Not implemented | Reason |
|----------------|--------|
| Write tools | Task 9.8.3+ |
| External integrations | Task 9.8.3+ |
| Email / communication | Task 9.8.3+ |
| Payment actions | Task 9.8.3+ |
| CRM mutations | Task 9.8.3+ |
| Background retry workers | Task 9.8.4+ |
| Scheduled autonomy | Task 9.8.5+ |
| Automatic Evidence creation | Task 9.8.6+ |
| Automatic Learning creation | Task 9.8.6+ |
| Public execution endpoint | Task 9.8.3+ |
| LLM-driven plan generation | Task 9.8.4+ |
| Self-approval | **Never** — architectural prohibition |

---

## Database Changes

**No new migrations required.**

Task 9.8.2 reuses:
- `agent_runs` — for execution tracing
- `agent_tasks` — for execution plan, status, and tool audit records
- `approvals` — read-only, for approval verification

---

## Files Added / Modified

### New files
- `tests/test_execution_runner.py` — 33+ comprehensive tests covering all acceptance criteria
- `docs/task-9-8-2-controlled-execution-runner.md` — this document

### Modified files
- `tests/test_execution_orchestrator.py` — Updated stale 9.8.1 test (`test_orchestrator_does_not_execute_tools` → `test_orchestrator_delegates_to_runner`)

### Existing files (no modification needed)
- `app/services/execution/runner.py` — `ExecutionRunner` (fully implemented)
- `app/services/execution/orchestrator.py` — `ExecutionFoundationOrchestrator` (fully implemented)
- `app/services/execution/approval_verification.py` — server-authoritative approval check
- `app/services/execution/plan_validation.py` — plan and tool validation
- `app/services/execution/state.py` — state machine
- `app/services/execution/errors.py` — typed errors
- `app/services/execution/policy.py` — runtime policy
- `app/services/execution/audit.py` — execution audit helpers
- `app/services/execution/identity.py` — tenant-scoped identity
- `app/services/tools/executor.py` — mandatory tool execution gate
- `app/services/tools/registry.py` — tool registry
- `app/services/tools/authorization.py` — permission enforcement
- `app/services/tools/audit.py` — tool-level audit

---

## Verification

```bash
# Run execution-specific tests
pytest tests/test_execution_runner.py tests/test_execution_orchestrator.py \
       tests/test_execution_plan_validation.py tests/test_execution_state.py \
       tests/test_execution_approval_policy.py -v

# Ruff lint
ruff check app/services/execution app/services/tools

# Full regression
pytest -q
```
