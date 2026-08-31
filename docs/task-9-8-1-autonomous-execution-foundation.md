# Task 9.8.1 — Autonomous Execution Architecture Foundation

## Overview

Task 9.8.1 establishes **contracts and orchestration boundaries** for controlled autonomous execution. It does **not** run tools, mutate company state, or bypass founder approval.

**Not implemented:** full autonomous execution (9.8.x remainder), external integrations, write tools, background workers, automatic execution.

## Existing infrastructure reused

| Layer | Reuse |
|-------|-------|
| Audit | `AgentRun` / `AgentTask` via `execution/audit.py` |
| Tools | `ToolRegistry` + validation only — **not** `ToolExecutor.execute()` |
| ObjectiveTask | Existing state machine — not modified |
| Approval | Existing `approval_service` boundary — not modified |
| Tenant scope | `CompanyMember` via `execution/identity.py` |

## Execution domain model

**Schemas:** `app/schemas/execution.py`

| Concept | Purpose |
|---------|---------|
| `ExecutionIdentity` | Stable `execution_id`, tenant scope, trace |
| `ExecutionRequest` | Request + server-controlled `status` |
| `ExecutionPlan` | Goal, rationale, ordered `ExecutionStep` list |
| `ExecutionStep` | Tool reference, input, risk, approval flags |
| `ExecutionAttempt` | Per-step attempt record |
| `ExecutionResult` | Aggregated outcome |
| `ExecutionPolicy` | Runtime limits schema |
| `ApprovalRequirement` | Policy evaluation output |

### Execution status lifecycle

```
requested → planned → waiting_for_approval → approved → running → succeeded
                              ↓                ↓           ↓
                           cancelled        cancelled   failed → retrying → running
```

Terminal: `succeeded`, `failed`, `cancelled`

Transitions validated in `app/services/execution/state.py` — no arbitrary client transitions.

### Step status lifecycle

`pending` → `waiting_for_approval` / `approved` / `running` → `succeeded` | `failed` | `skipped` | `cancelled`

## Execution identity

Built server-side via `new_execution_identity(membership, ...)`:

- `company_id` from `CompanyMember` — never from plan/tool input
- `requested_by` = authenticated user
- `trace_id` for audit correlation
- Optional `objective_id`, `objective_task_id`

## Execution plan contract

Plans are **data**. Validation (`plan_validation.py`):

1. Step uniqueness (`step_id`, `sequence`)
2. Tool exists in registry and is enabled
3. Write tools rejected
4. Input validated against tool Pydantic models (`extra="forbid"`)
5. Input size limits
6. Max steps per policy

Tools must still pass through `ToolExecutor` when execution is implemented — planners cannot bypass the registry.

## Approval policy

`approval_policy.py` classifies steps:

| Category | Meaning |
|----------|---------|
| `read_only_low_risk` | Internal read, low cost |
| `read_only_high_cost` | Read with elevated risk/cost |
| `write_low_risk` / `write_high_risk` | Mutation-capable (future) |
| `external_side_effect` | External reads/effects |
| `financial_action` | Payments (future) |
| `communication_to_customer` | Outbound comms (future) |

**Task 9.8.1:** all categories return `approval_required=True` and `auto_execution_eligible=False`. Policy boundary only — no auto-execution.

## Orchestrator boundary

`ExecutionFoundationOrchestrator` (`orchestrator.py`):

| Method | Behavior |
|--------|----------|
| `build_request()` | Create `ExecutionRequest` in `requested` |
| `validate_request_scope()` | Tenant check |
| `validate_and_annotate_plan()` | Validate + apply approval policy |
| `attach_plan()` | Transition to `planned` |
| `cancel_execution()` | Transition to `cancelled` |
| `run_execution()` | **Raises `ExecutionNotImplementedError`** |
| `execute_step()` | **Raises `ExecutionNotImplementedError`** |

Does **not** call `ToolExecutor.execute()`.

## Audit

`execution/audit.py` task types:

- `execution_plan` — plan JSON in `AgentTask.output`
- `execution_status` — status transitions
- `AgentRun.task_id` wired to `objective_task_id` when present

No secrets or full tool payloads in audit metadata.

## Policy limits

`app/core/config.py`:

- `execution_max_steps_per_plan` (default 20)
- `execution_max_tool_calls_per_step` (default 5)
- `execution_max_retries_per_step` (default 3)
- `execution_max_duration_ms` (default 120000)

## Security

- Tenant isolation via `assert_execution_tenant()`
- Plans cannot include write tools
- Unknown/disabled tools rejected at validation
- No public execution API in 9.8.1
- Founder approval boundary unchanged

## Testing

```bash
cd apps/api
pytest -q tests/test_execution_state.py tests/test_execution_approval_policy.py tests/test_execution_plan_validation.py
pytest -q tests/test_execution_orchestrator.py  # requires PostgreSQL
pytest -q
ruff check app/schemas/execution.py app/services/execution/
```

## Task 9.8 remainder boundary

Future work may implement:

- `run_execution()` with `ToolExecutor` per step
- Approval integration for `waiting_for_approval`
- ObjectiveTask status coordination

9.8.1 intentionally stops at contracts and validation.
