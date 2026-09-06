# Task 9.8.4: Execution Review and Approval

## Overview

Task 9.8.4 implements a deterministic, founder-controlled execution plan review and approval gate between the ExecutionPlanner and ExecutionRunner. This ensures that founders explicitly approve execution plans before any tools are executed, with cryptographic guarantees that the approved plan cannot be modified.

## Architecture

```
ExecutionPlanner
    ↓
validated ExecutionPlan (persisted in AgentTask)
    ↓
create_execution_approval()
    ↓
Approval record with plan_fingerprint and expires_at
    ↓
Founder views ExecutionReview via UI
    ↓
Founder approves (POST /approvals/{id}/approve)
    ↓
ExecutionRunner calls verify_execution_approved()
    ↓
Server verifies:
  - Approval exists and is approved
  - Approval belongs to requesting company
  - Approval is not expired
  - Plan fingerprint matches current plan
    ↓
ToolExecutor executes approved read-only tools
    ↓
Execution result returned/audited
```

## Key Components

### 1. Approval Model Extension

**File:** `app/models/approval.py`

Added fields:
- `plan_fingerprint`: SHA256 hash of the canonical execution plan (64 chars)
- `expires_at`: ISO8601 timestamp when approval expires (32 chars, 24-hour default)

### 2. Plan Fingerprinting

**File:** `app/services/execution/approval_verification.py`

Function: `compute_plan_fingerprint(plan: ExecutionPlan) -> str`

Computes a deterministic SHA256 hash of:
- `goal`
- `rationale`
- `risk_level`
- `steps` (sorted by sequence, including: step_id, sequence, tool_name, tool_version, purpose, input, risk_level)

Properties:
- Deterministic: same plan → same fingerprint
- Dictionary-order independent: sorted keys
- Whitespace independent: compact JSON separators
- Material-field sensitive: any change → different fingerprint

### 3. Expiration

**File:** `app/services/execution/approval_verification.py`

- Default expiration: 24 hours after approval request
- Format: ISO8601 string without microseconds
- Timezone: UTC
- Check: `datetime.now(UTC) >= expires_at` (exact time is rejected)
- Missing expiration: allowed (no expiration check)

### 4. Execution Review API

**Endpoint:** `GET /companies/{company_id}/approvals/{approval_id}/execution-review`

**File:** `app/api/routes/approvals.py`

Parameters:
- `company_id`: from URL path
- `approval_id`: from URL path
- `execution_id`: query parameter

Security:
- Requires authentication (`require_authenticated_user`)
- Requires company membership (`require_company_access`)
- Verifies approval belongs to company
- Verifies approval is an execution approval (not learning)

Response: `ExecutionReview` schema

### 5. Review Presenter

**File:** `app/services/execution/review_presenter.py`

Function: `execution_review_from_approval(db, approval, execution_id)`

Builds founder-facing review from Approval and AgentTask:
- Extracts execution plan from AgentTask output
- Sanitizes step inputs (redacts secrets)
- Builds step reviews with all relevant fields
- Includes tool summary, risk, expiration, fingerprint

### 6. Frontend Component

**File:** `apps/web/components/dashboard/ExecutionReviewCard.tsx`

Displays:
- Execution goal and rationale
- Risk level badge
- Step count and tool summary
- Requested and expiration timestamps
- Expandable step details
- Sanitized inputs (secrets redacted)
- Approve & Execute / Reject buttons

## Security Model

### Approval Boundary

- **Mandatory**: ExecutionRunner cannot execute without valid approval
- **Server-side verification**: All checks happen server-side
- **No client trust**: Frontend cannot bypass approval checks
- **No self-approval**: ExecutionRunner cannot create its own approvals

### Plan Immutability

- **Fingerprint binding**: Approval is bound to exact plan fingerprint
- **Change detection**: Any plan change → fingerprint mismatch → rejection
- **No substitution**: Client cannot substitute different plan with same fingerprint

### Tenant Isolation

- **Company scoping**: All queries filter by `company_id`
- **Membership check**: API requires company membership
- **Cross-company rejection**: Company A cannot access Company B approvals
- **Execution isolation**: ExecutionRunner checks company_id match

### Secret Redaction

**File:** `app/services/execution/review_presenter.py`

Sanitized keys:
- `api_key`
- `password`
- `secret`
- `token`
- `authorization`
- `bearer`
- `credential`

Recursive sanitization for nested dicts and lists.

## Idempotency

The existing 9.8.2 ExecutionRunner idempotency is preserved:
- Partial execution resumes from last successful step
- Repeated execution of completed steps is skipped
- Execution identity provides stable tracking

## Failure Handling

### Safe Errors

All errors return safe, user-facing messages:
- `ExecutionNotApprovedError`: "Execution not approved"
- `ExecutionRunnerError`: "Execution plan has expired" or "Execution plan has changed"
- No stack traces or internal details exposed

### Error Cases

- Invalid approval → safe error
- Expired approval → safe error
- Fingerprint mismatch → safe error
- Unknown tool → rejected at plan validation
- Write tool → rejected at plan validation
- Invalid input → rejected at plan validation
- ToolExecutor failure → safe result, no execution
- DB failure → rollback where appropriate

## What 9.8.4 Does NOT Enable

9.8.4 does NOT enable:
- Autonomous background agents
- Unrestricted write tools
- External integrations
- Arbitrary autonomous mutations
- Scheduled autonomous execution
- Bypassing founder approval
- Self-approval by execution system

## Database Changes

### Migration

**File:** `alembic/versions/add_execution_approval_fingerprint.py`

Revision: `add_execution_approval_fingerprint`
Revises: `c2e8f19a24b5`

Columns added:
- `plan_fingerprint`: `VARCHAR(64)` (nullable)
- `expires_at`: `VARCHAR(32)` (nullable)

### Model

**File:** `app/models/approval.py`

```python
plan_fingerprint: Mapped[str | None] = mapped_column(nullable=True)
expires_at: Mapped[str | None] = mapped_column(nullable=True)
```

## API Changes

### New Endpoint

`GET /companies/{company_id}/approvals/{approval_id}/execution-review`

Response model: `ExecutionReview`

### New Schemas

**File:** `app/schemas/execution.py`

- `ExecutionStepReview`: Founder-facing step representation
- `ExecutionReview`: Founder-facing plan representation

## Frontend Changes

### New Component

**File:** `apps/web/components/dashboard/ExecutionReviewCard.tsx`

### API Types

**File:** `apps/web/lib/api.ts`

- `ExecutionReview` type
- `ExecutionStepReview` type
- `getExecutionReview()` function

## Testing

### Unit Tests

**File:** `tests/test_execution_approval_fingerprint.py`

- Deterministic fingerprint for same plan
- Different fingerprint for different tool/version/input/sequence/risk
- Same fingerprint for reordered dict keys
- Steps sorted by sequence for fingerprint

**File:** `tests/test_execution_approval_expiration.py`

- ISO8601 format validation
- 24-hour expiration duration
- Boundary conditions (exact, before, after)
- Timezone handling (UTC)
- Missing expiration handling

**File:** `tests/test_execution_approval_tenant_isolation.py`

- Company scoping in queries
- Cross-company rejection
- Fingerprint does not bypass isolation
- Expiration does not bypass isolation

**File:** `tests/test_execution_review_api.py`

- Authentication required
- Company membership required
- Wrong company rejection
- Non-execution approval rejection
- Non-existent approval handling
- Secret redaction verification

### Integration Tests

Existing 9.8.2 tests cover:
- Idempotency
- Partial execution resume
- Tenant isolation
- Failure safety
- ToolExecutor boundary

## Migration Notes

### Before Migration

Current head: `c2e8f19a24b5` (Add blocked_reason to objective tasks for Task 8.1)

### After Migration

New head: `add_execution_approval_fingerprint`

### Rollback

Downgrade removes `plan_fingerprint` and `expires_at` columns.

## Dependencies

- Task 9.8.2: ExecutionRunner (provides execution infrastructure)
- Task 9.8.3: ExecutionPlanner (provides plan generation)
- Existing approval system (provides approval workflow)

## Future Work

Out of scope for 9.8.4:
- Background autonomous execution
- Scheduled execution
- Multi-step approval workflows
- Approval delegation
- Approval templates
