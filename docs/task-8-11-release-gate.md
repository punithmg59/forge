# TASK 8.11 — FINAL FOUNDER SMOKE TEST & RELEASE GATE

**Date:** 2026-08-30  
**Scope:** Forge Task 8 complete founder operating loop  
**Release decision:** **READY WITH FIXES**

---

## 1. Final status

**READY WITH FIXES**

Automated frontend gates pass. Production config guards verified. Backend automated regression **could not be executed** in this environment because Docker Desktop and PostgreSQL are unavailable (`ConnectionRefusedError` on `localhost:5433`). **No browser-based manual smoke tests were performed** in this session.

Task 8 is **not** cleared for Task 9 until:
1. PostgreSQL is running and `alembic upgrade head` succeeds
2. Full `pytest` passes (491 tests in suite at time of gate)
3. Manual founder workflow smoke tests are executed in a live browser

---

## 2. Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Docker Desktop | **NOT AVAILABLE** | `dockerDesktopLinuxEngine` pipe missing |
| PostgreSQL (`localhost:5433`) | **NOT AVAILABLE** | Connection refused |
| `alembic current` / `upgrade head` | **BLOCKED** | Requires PostgreSQL |
| Backend API server | **NOT STARTED** | Requires database |
| Frontend dev server | **NOT STARTED** | Browser smoke not run |
| `email-validator` | **OK** | v2.3.0 installed |
| `NEWTRON_API_KEY` | **CONFIGURED** | Present in `.env` (not logged) |
| Config guards | **VERIFIED** | `scripts/verify_config.py` passed |

**LLM provider/model (configured default):** `newtron` / `nvidia/nemotron-3-ultra-550b-a55b`

OpenAI and Anthropic are **not implemented** in `get_llm_provider()` — external provider comparison was not possible.

---

## 3. Automated tests

### Backend (`pytest`)

| Result | Detail |
|--------|--------|
| **BLOCKED (environment)** | All DB-dependent tests fail with `ConnectionRefusedError` |
| Last known green run (Task 8.9) | **491 passed** with PostgreSQL on Docker port 5433 |
| Failure class | **Environment** — not a product regression observed in this session |

### Frontend (`npm test`)

| Result | Detail |
|--------|--------|
| **PASS** | 62 / 62 tests (8 files) |

### Frontend build (`npm run build`)

| Result | Detail |
|--------|--------|
| **PASS** | Routes: `/dashboard`, `/dashboard/tasks`, `/dashboard/tasks/[taskId]` compile |

### Ruff (`ruff check app/`)

| Result | Detail |
|--------|--------|
| **1 pre-existing E501** | `app/schemas/onboarding.py:147` |
| Benchmark lint | Fixed E501 in `app/benchmarks/` during 8.11 |

---

## 4. Manual test results

| Scenario | Result | Notes |
|----------|--------|-------|
| Login | **NOT RUN** | Browser smoke not performed |
| Company load | **NOT RUN** | |
| Objective | **NOT RUN** | |
| Head Agent | **NOT RUN** | API-level Head Agent covered by mocked tests when DB available |
| Missing information | **NOT RUN** | Benchmark eval + head agent tests cover conservative behavior |
| Prompt injection | **NOT RUN** | `test_malicious_question_cannot_override_grounding_instructions` |
| Approval | **NOT RUN** | `test_approvals_api`, Task 6 e2e when DB available |
| Rejection | **NOT RUN** | `test_rejection_path_keeps_learning_out_of_brain` |
| Task lifecycle | **NOT RUN** | `test_objective_task_status`, `test_objective_task_complete` |
| Evidence | **NOT RUN** | `test_end_to_end_task7_operating_loop` |
| Learning proposal | **NOT RUN** | Task 7 evaluation suite |
| Learning approval | **NOT RUN** | `test_learning_approval` |
| Learning rejection | **NOT RUN** | `test_rejection_path_keeps_learning_out_of_brain` |
| Learning correction | **NOT RUN** | `test_end_to_end_task7_operating_loop` (supersede) |
| Tenant isolation | **NOT RUN** (browser) | **API VERIFIED** via `test_tenant_isolation`, cross-company tests when DB available |
| Company switching | **NOT RUN** | Stale-request guards present in code (8.7); no integration test |
| Error handling | **NOT RUN** (browser) | Safe 500 handler + `mapRecommendationApiError` in frontend |
| Performance | **NOT RUN** | Task 8.9 measured Head Agent ~9–104s e2e (LLM-bound) |
| Mobile (~390px) | **NOT RUN** | |
| Accessibility | **PARTIAL (code review)** | Company select `aria-label`, Head Agent `aria-live`, TaskDialog semantics |

---

## 5. End-to-end workflow result

**Automated service-layer E2E (when PostgreSQL available):**

| Step | Automated test coverage | Manual browser |
|------|-------------------------|----------------|
| Company → Objective | `test_objectives_api`, onboarding tests | NOT RUN |
| Head Agent recommendation | `test_head_agent`, Task 6 evaluation | NOT RUN |
| Approval gate | `test_end_to_end_operating_loop_with_approval_gate` | NOT RUN |
| Founder Task creation | Approvals API + Task 6 e2e | NOT RUN |
| Task status machine | `test_objective_task_status` | NOT RUN |
| Task completion | `test_objective_task_complete` | NOT RUN |
| Evidence | `test_end_to_end_task7_operating_loop` | NOT RUN |
| Learning proposal | `test_learning_proposal` | NOT RUN |
| Learning approval | `test_learning_approval` | NOT RUN |
| Active Brain knowledge | Task 7 e2e retrieval checks | NOT RUN |
| Learning correction | `test_end_to_end_task7_operating_loop` | NOT RUN |

**Verdict:** Workflow is **extensively covered by backend integration tests** but **not manually verified in browser** in this gate.

---

## 6. Security result

| Check | Result |
|-------|--------|
| Hardcoded API keys in app source | **NONE FOUND** (grep + evaluation scans) |
| Production `SECRET_KEY` guard | **VERIFIED** |
| CORS configurable | **VERIFIED** |
| Secure cookies in production | **VERIFIED** (`security.py`) |
| Global safe 500 handler | **PRESENT** (`main.py`) |
| Tenant isolation (API) | **VERIFIED** in test suite when DB available |
| Approval boundary | **VERIFIED** — tasks created only via approval path in tests |
| Head Agent recommend-only | **VERIFIED** — no autonomous mutations |

---

## 7. Tenant isolation result

- Backend: `test_tenant_isolation.py`, cross-company tests across objectives, tasks, brain, approvals, learnings
- `test_cross_company_learning_list_blocked` (Task 8.7)
- Frontend company-switch stale-request guards in `FounderCommandCenter`, `FounderTaskWorkspace`, `TaskDetailView`
- **Browser company-switch:** NOT RUN

---

## 8. Performance result

From Task 8.9 (live Newtron, not re-measured in 8.11):

| Metric | Value |
|--------|-------|
| Head Agent best e2e | ~9,027 ms |
| Head Agent avg e2e (5 samples) | ~44,710 ms (high provider variance) |
| Retrieval p50 | ~108 ms |
| LLM p50 | ~39,491 ms |

Frontend: Task 8.9 loading UX (`Forge is analyzing your company context…`, duplicate-submit guard) — **code present**, **not browser-verified** in 8.11.

Dashboard parallel load (`Promise.all` for objectives, approvals, tasks, learnings) — **code verified**, not network-profiled in browser.

---

## 9. Bugs found

| ID | Severity | Finding |
|----|----------|---------|
| E1 | Environment | Docker Desktop not running — blocks PostgreSQL, alembic, pytest, live API |
| E2 | Process | Manual browser smoke tests not yet executed for Task 8 release |
| — | None | No new product bugs identified in this gate session |

---

## 10. Bugs fixed

| File | Change |
|------|--------|
| `app/benchmarks/evaluation.py` | Ruff E501 line-length fixes (style only) |
| `app/benchmarks/head_agent_dataset.py` | Ruff E501 line-length fix (style only) |

No functional product bugs were found requiring fixes in this gate.

---

## 11. Remaining risks

1. **Manual founder workflow never browser-verified** — highest release risk
2. **Backend pytest not green in current environment** — must re-run with PostgreSQL
3. **Head Agent latency** — LLM provider dominates; variable 9s–100s+ responses
4. **No frontend integration tests** for company switching
5. **Task 8.10 LLM benchmark report** incomplete in repo — model selection may need re-validation
6. **Solo-founder MVP auth** — any member can trigger LLM endpoints (documented)

---

## 12. Production requirements

```env
APP_ENV=production
SECRET_KEY=<strong-random-secret>
DATABASE_URL=<production-postgres-with-pgvector>
CORS_ORIGINS=https://<frontend-origin>
NEWTRON_API_KEY=<secret>
LLM_MODEL=<benchmark-selected-model>
NEXT_PUBLIC_API_URL=<api-origin>  # frontend build
```

**Pre-release checklist:**
1. `docker compose up -d postgres` (or managed Postgres with pgvector)
2. `alembic upgrade head` && `alembic current` at head (`c2e8f19a24b5`)
3. `pytest` — all green
4. Manual founder smoke (§4 table) in browser
5. Verify Head Agent UX under real network latency

---

## 13. Task 9 recommendation

**Forge is NOT ready to begin Task 9** based on this release gate.

**Reason:** Critical release verification steps remain incomplete:
- PostgreSQL-backed `pytest` regression not executed in current environment
- Full manual founder operating-loop smoke test not performed in browser

**When ready for Task 9:**
- All §4 manual scenarios marked PASS in a live environment
- `pytest` fully green
- No blocking security or tenant-isolation failures

Task 8 deliverable status: **implementation complete**, **release verification incomplete**.

---

## Appendix: Prior Task 8 automated baseline (PostgreSQL available)

When Docker Postgres was running (Task 8.8–8.9):

- `pytest`: 488–491 passed
- `npm test`: 62 passed
- `npm run build`: passed
- Migration head: `c2e8f19a24b5`
- Core E2E: `test_end_to_end_task7_operating_loop`, `test_end_to_end_operating_loop_with_approval_gate`, `test_end_to_end_pipeline_with_mock_llm`
