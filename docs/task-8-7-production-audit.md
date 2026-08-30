# Task 8.7 — Production Audit Report

**Date:** 2026-08-26  
**Scope:** Forge Tasks 5–8.6 (`apps/api`, `apps/web`)  
**Assessment:** **READY WITH FIXES** (P0 none; P1 addressed in this pass)

---

## 1. Executive summary

Forge’s Tasks 5–8.6 architecture is structurally sound for production as an **operating console with founder-controlled execution**. Authorization is consistently applied on company-scoped routes via path `company_id` + membership dependencies. Tenant isolation is enforced at the service layer with company_id checks on resources. Core mutation paths (task completion, approval, learning proposal) include intentional idempotency with tests.

**Strengths:**
- No client-trusted `company_id` in mutation bodies
- Cookie sessions with `httponly` and production `secure`
- LLM accessed through `LLMProvider` abstraction
- Task detail uses single aggregated API (no frontend N+1)
- Dashboard loads four list endpoints in parallel; Head Agent is on-demand
- Extensive backend tenant-isolation and evaluation tests

**Gaps found (pre-fix):**
- CORS locked to localhost
- Default `SECRET_KEY` in config without production guard
- No global safe exception handler
- N+1 on approvals/learnings list endpoints
- Company-switch race could apply stale API responses in dashboard
- Task pages did not validate onboarding on company switch

**Fixes applied in Task 8.7:** See §19 Files changed.

---

## 2. Architecture findings

**Pattern:** `HTTP route → deps (auth + membership) → service → DB → (optional LLM) → schema response`

| Area | Assessment | Severity |
|------|------------|----------|
| Routes contain business logic | Minimal; services own mutations | OK |
| Duplicate business rules in frontend | Status/approval helpers mirror display only, not security | P3 |
| Oversized services | `approval_service`, `head_agent` are large but cohesive | P3 |
| Brain retrieval | Structured SQL fan-out (~10 queries) + optional vector path | P2 |
| Head Agent | Persists `AgentRun` + `AgentTask`; recommendation in `output` JSON | OK |

**Coupling:** `ObjectiveTaskDetailResponse.from_detail` parses recommendation from `AgentTask.output` — acceptable, uses existing stored data.

---

## 3. Security findings

| ID | Sev | Finding | Status |
|----|-----|---------|--------|
| S1 | P1 | CORS `allow_origins` hardcoded to localhost | **Fixed** — `CORS_ORIGINS` env |
| S2 | P1 | `SECRET_KEY` default `change-me`; no production validation | **Fixed** — validator rejects in `APP_ENV=production` |
| S3 | P1 | Unhandled exceptions may expose stack traces (deployment-dependent) | **Fixed** — global handler returns safe 500 |
| S4 | P2 | `secret_key` in config unused for sessions today | Open — session tokens independent |
| S5 | P3 | No hardcoded API keys in application source | OK |
| S6 | P3 | `.env.example` documents secrets as empty placeholders | OK |

**Secret scan:** No live `nvapi-`, `sk-proj-`, `sk-ant-` in app code. Test files scan for patterns intentionally.

---

## 4. Tenant isolation findings

**Mechanism:** `require_company_access` / `require_company_role` on path `company_id`; services verify `resource.company_id == company_id`.

**Chains verified in code:**
- ObjectiveTask → company_id on task
- Evidence → company_id + source_reference to task
- Learning → company_id + evidence_id
- Approval → company_id + agent_task_id / learning_id
- AgentTask → company_id + objective_task_id

**Tests:** `test_tenant_isolation.py`, cross-company tests across objectives, tasks, brain, approvals, learnings (GET by id). **Added:** `test_cross_company_learning_list_blocked`.

**Frontend:** API enforces isolation; UI company-switch stale-data was a **display** risk, not a bypass. **Fixed** with request-generation guards.

| ID | Sev | Finding | Status |
|----|-----|---------|--------|
| T1 | P1 | Dashboard loaders could apply stale data after company switch | **Fixed** |
| T2 | P1 | Task detail could flash wrong-company task on switch | **Fixed** — clear state + stale guard; redirect to task list on switch |
| T3 | P1 | Task pages skipped onboarding validation on company switch | **Fixed** |

---

## 5. Authorization findings

| Endpoint class | Member read | Founder write |
|----------------|-------------|---------------|
| Objectives | ✓ | create/patch |
| Objective tasks list/detail | ✓ | patch metadata |
| Task complete/status | ✓ (all members) | P2 — intentional for solo-founder product |
| Approvals approve/reject | — | founder only |
| Learning correct | — | founder only |
| Learning proposal (LLM) | ✓ (all members) | P2 — triggers LLM cost |
| Head Agent recommend | ✓ (all members) | P2 — triggers LLM cost |

Backend is authoritative; frontend buttons are not security controls.

---

## 6. Database findings

| Area | Query pattern | Severity |
|------|---------------|----------|
| `get_objective_task_detail` | ~6 sequential queries, bounded | P3 — acceptable for single detail |
| Brain structured retrieval | ~10 queries per context build | P2 — inherent fan-out |
| `GET /approvals` (list) | Was N+1 via `approval_to_public` | **Fixed** — batch `approvals_to_public` |
| `GET /learnings` (list) | Was N+1 via `learning_to_public` | **Fixed** — batch `learnings_to_public` |
| List endpoints | Ordered, company-filtered, no unbounded table scans | OK |

**Indexes:** No new indexes added — existing company_id indexes on major tables; no evidence of missing index on hot paths from code review.

---

## 7. Transaction findings

| Mutation | Pattern | Assessment |
|----------|---------|------------|
| Task complete + evidence | evidence `flush`, task `commit` in same flow | OK |
| Approval approve | learning activation + approval commit | OK |
| Learning correct | single learning update + commit | OK |
| Onboarding confirm | `for_update` + rollback on error | Good |

| ID | Sev | Finding |
|----|-----|---------|
| TR1 | P2 | Most services lack explicit `rollback` on failure — relies on session lifecycle |
| TR2 | P2 | Concurrent task completion race before evidence exists — low probability |

---

## 8. Idempotency findings

| Operation | Guarantee | Tested |
|-----------|-----------|--------|
| Task complete (already completed) | Early return, no duplicate evidence | ✓ |
| Evidence per task | Reuses existing evidence row | ✓ |
| Approval approve/reject | Terminal state idempotent | ✓ |
| Pending approval create | Reuses existing pending row | ✓ |
| Learning proposal (proposed exists) | Reuses proposed learning | ✓ |
| Learning correct (superseded) | Idempotent return | ✓ |
| Head Agent recommend | **Not idempotent** — new run each call | By design |
| New pending approval after terminal | Can create new pending for same agent_task | P2 |

---

## 9. LLM / provider findings

- Business logic uses `LLMProvider` / `get_llm_provider()` — not direct Newtron in routes
- Provider errors mapped to 502/504/429 without leaking keys
- Head Agent and learning proposal normalize failures in services
- **No new providers implemented** (Task 9 scope)
- **Latency:** Not measured in this environment (requires live Newtron credentials). Architecture: retrieval → context assembly → provider → persist. Vector path can degrade gracefully (brain_context fix from prior task).

---

## 10. Performance findings

**Frontend (code review):**
- Dashboard: 4 parallel list calls on load — OK
- No automatic Head Agent on dashboard load — OK
- Task detail: 1 API call — OK
- Task workspace: 2 parallel calls — OK
- Duplicate boot sequences across routes (auth + companies + draft) — P2

**Backend (code review):**
- List N+1 fixed for approvals/learnings
- Brain/Head Agent remain latency-sensitive when LLM invoked — expected

**Measurements:** No browser network or LLM timing captured in this audit run.

---

## 11. Frontend findings

| Item | Status |
|------|--------|
| Company switch stale data | **Fixed** |
| Section-level loading/errors | OK (SectionCard skeletons + retry) |
| Error messages | Safe via `safeApiMessage` / `mapTaskApiError` |
| sessionStorage | Only `forge_active_company_id` — no secrets |
| Learning correction modal | P2 — lacks full dialog semantics |
| Company `<select>` labels | P2 — missing `aria-label` on some pages |

---

## 12. API findings

- Consistent `{ detail }` error shape for HTTPException
- Pydantic `extra=forbid` on sensitive request schemas
- UUID path params validated by FastAPI
- List responses use typed wrappers (`tasks`, `approvals`, `learnings`)

No breaking API changes in Task 8.7.

---

## 13. Configuration findings

| Setting | Risk | Status |
|---------|------|--------|
| `APP_ENV` | Controls cookie `secure` | OK |
| `SECRET_KEY` | Production validation added | **Fixed** |
| `DATABASE_URL` | Default local dev credentials | Document in deployment |
| `CORS_ORIGINS` | Configurable | **Fixed** |
| Debug mode | FastAPI default (not explicitly enabled) | P3 |

---

## 14. Observability findings

- No structured request logging middleware — P2
- Global exception handler logs unhandled errors with path — **Added**
- Logs should not include prompts/keys (no evidence of logging prompts in services) — P3

---

## 15. Accessibility findings

- Task dialogs: `role="dialog"`, Escape, focus trap — OK
- Task filters: labels present — OK
- Dashboard company select: missing label — P2
- Status badges include text — OK

---

## 16. Migration findings

Tasks 5–8 migrations: additive columns, FK relationships, no destructive drops observed in review. Migration order valid in alembic versions. **No migration changes in Task 8.7.**

---

## 17. Test coverage

**Backend:** 37+ test modules including tenant isolation, task status, completion, detail, approvals, learnings, brain, evaluations.

**Frontend:** 62 unit tests (helpers + API path mocks). No component/integration tests for company switching — P2.

**Added in 8.7:** `test_cross_company_learning_list_blocked`

---

## 18. Findings table

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| S1 | P1 | CORS localhost-only | **Fixed** — `CORS_ORIGINS` |
| S2 | P1 | Weak default SECRET_KEY in production | **Fixed** — validator |
| S3 | P1 | No safe global exception handler | **Fixed** |
| N3 | P1 | Approvals list N+1 | **Fixed** — batch presenter |
| N4 | P1 | Learnings list N+1 | **Fixed** — batch service |
| T1 | P1 | Company switch stale dashboard data | **Fixed** |
| T2 | P1 | Task detail stale on company switch | **Fixed** |
| T3 | P1 | Task pages onboarding gate on switch | **Fixed** |
| A2 | P2 | Any member can trigger LLM endpoints | Document / future role tighten |
| A3 | P2 | Any member can complete tasks | Acceptable for solo-founder MVP |
| TR1 | P2 | No explicit rollback in services | Monitor; onboarding has rollback |
| I6 | P2 | New pending approval after terminal | Rare; document |
| I10 | P2 | Head Agent not idempotent | By design |
| E2 | P2 | No request logging middleware | Future |
| FE1 | P2 | No web tenant-switch tests | Future |
| FE2 | P2 | Duplicate route boot API calls | Future layout sharing |
| A1 | P3 | Session commit on every auth read | Future optimization |
| C3 | P3 | secret_key unused | Future session hardening |

---

## 19. Files changed (Task 8.7 fixes)

**Backend:**
- `apps/api/app/core/config.py` — `CORS_ORIGINS`, production `SECRET_KEY` validation
- `apps/api/app/main.py` — CORS from settings, exception handlers
- `apps/api/app/services/approval_presenter.py` — `approvals_to_public` batch
- `apps/api/app/services/learning_service.py` — `learnings_to_public` batch
- `apps/api/app/api/routes/approvals.py` — use batch presenter
- `apps/api/app/api/routes/learnings.py` — use batch mapper
- `apps/api/tests/test_learning_visibility.py` — cross-company list test
- `.env.example` — `CORS_ORIGINS`

**Frontend:**
- `apps/web/components/dashboard/FounderCommandCenter.tsx` — stale-request guards
- `apps/web/components/tasks/FounderTaskWorkspace.tsx` — stale-request guards
- `apps/web/components/tasks/TaskDetailView.tsx` — clear state + stale guard
- `apps/web/app/dashboard/tasks/page.tsx` — onboarding on company switch
- `apps/web/app/dashboard/tasks/[taskId]/page.tsx` — onboarding + redirect on switch

**Docs:**
- `docs/task-8-7-production-audit.md` (this file)

---

## 20. Tests run

Run locally after changes:
- `apps/web`: `npm test`, `npm run build`
- `apps/api`: `pytest` relevant suites, `ruff check app/`

(Environment may require `email_validator` for API tests.)

---

## 21. Manual tests

Not performed in this audit session. Recommended manual paths documented in Task 8.7 spec (login, company switch, approval flow, task lifecycle, learning lifecycle, network tab).

---

## 22. Remaining risks

**Required before production:**
- Set `APP_ENV=production`, strong `SECRET_KEY`, production `DATABASE_URL`, `CORS_ORIGINS` for real frontend origin
- Configure `NEWTRON_API_KEY` (or future provider) with timeout awareness
- Deploy with HTTPS so session cookies use `secure`

**Recommended:**
- Tighten LLM endpoint roles if multi-member companies expand beyond solo-founder
- Add frontend integration tests for company switching
- Request logging with `trace_id` propagation
- Measure Head Agent p95 latency in production

**Future (Task 9):**
- Autonomous execution, workers, additional providers — out of scope

---

## 23. Recommended next work

1. Production deployment checklist from §22
2. Role matrix review if team members join companies
3. Optional: shared dashboard layout to reduce duplicate boot API calls
4. Task 9 planning — only after production baseline is deployed and measured

---

## 24. Final confirmation

**Task 9 was NOT implemented.**
