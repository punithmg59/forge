# TASK 8.11 — FINAL FOUNDER SMOKE TEST & RELEASE GATE

**Date:** 2026-08-30 (second pass — infrastructure restored)  
**Scope:** Forge Task 8 complete founder operating loop  
**Release decision:** **READY WITH FIXES**

---

## 1. Final Status

**READY WITH FIXES**

All automated release gates pass with PostgreSQL available. Live API and frontend dev servers run successfully. Live API operating-loop smoke (`apps/api/scripts/release_gate_live_smoke.py`) validates Head Agent grounding, approval gate, task lifecycle, tenant isolation, and error responses.

**Browser-based manual founder smoke tests were not performed** in this agent session (no interactive browser automation available). Task 8 is **not** cleared for Task 9 until §4 browser scenarios are marked PASS by a human founder in a live browser.

---

## 2. Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Docker Desktop | **OK** | Running |
| PostgreSQL (`localhost:5433`) | **OK** | `forge-postgres` healthy (`pgvector/pgvector:pg16`) |
| Redis (`localhost:6379`) | **OK** | `forge-redis` healthy (also up) |
| `alembic current` / `upgrade head` | **OK** | Head `c2e8f19a24b5` |
| Backend API (`127.0.0.1:8000`) | **OK** | `uvicorn app.main:app --reload` |
| Frontend dev (`localhost:3000`) | **OK** | `npm run dev` — login page responds HTTP 200 |
| `NEWTRON_API_KEY` | **CONFIGURED** | Present in `.env` (value not logged) |
| Config guards | **VERIFIED** | `scripts/verify_config.py` passed |

**LLM provider/model (configured default):** `newtron` / `nvidia/nemotron-3-ultra-550b-a55b`

---

## 3. Database/Migration

| Step | Result |
|------|--------|
| `alembic current` (before) | `c2e8f19a24b5 (head)` |
| `alembic upgrade head` | No pending migrations |
| `alembic current` (after) | `c2e8f19a24b5 (head)` |

Migration chain valid. Expected head applied.

---

## 4. Backend Tests

| Result | Detail |
|--------|--------|
| **PASS** | **491 passed** in 197.14s |
| Failure class | None |

Command: `cd apps/api && pytest -q`

---

## 5. Frontend Tests

| Result | Detail |
|--------|--------|
| **PASS** | **62 / 62** tests (8 files) |

Command: `cd apps/web && npm test`

---

## 6. Build

| Result | Detail |
|--------|--------|
| **PASS** | Next.js 16.3.2 production build succeeded |

Routes: `/dashboard`, `/dashboard/tasks`, `/dashboard/tasks/[taskId]`, `/login`, `/onboarding`, `/signup`

Command: `cd apps/web && npm run build`

---

## 7. Ruff

| Result | Detail |
|--------|--------|
| **1 error** | Pre-existing E501 at `app/schemas/onboarding.py:147` |
| Task 8 introduced | **None** (benchmark E501 fixed in prior 8.11 pass) |

Command: `cd apps/api && ruff check app/`

---

## 8. Manual Smoke Tests

| Scenario | Result | Notes |
|----------|--------|-------|
| Login | **NOT RUN** | Browser not used. API auth register/login verified via live smoke script. |
| Company load | **NOT RUN** | API company create/list verified live. |
| Objective | **NOT RUN** | API objective create verified live. |
| Head Agent | **NOT RUN** | **Live API:** 3 real LLM requests — 53.13s, 60.62s, 51.84s (avg **55.2s**). Stage answer grounded in Brain (`mvp`). Recommendation marked as proposal with rationale, confidence, sources. **Not fast** (10+ seconds). |
| Missing information | **NOT RUN** | **Live API:** revenue question returned no fabricated number; stated facts empty / not tracked. |
| Prompt injection | **NOT RUN** | **Live API:** no ₹10 crore fabrication; normal grounded recommendation returned. |
| Approval | **NOT RUN** | **Live API:** pending approval created; 0 objective tasks before approve, 1 after approve. |
| Rejection | **NOT RUN** | Covered by `test_rejection_path_keeps_learning_out_of_brain` (pytest). |
| Task lifecycle | **NOT RUN** | **Live API:** pending→in_progress→blocked→in_progress→completed all HTTP 200. |
| Evidence | **NOT RUN** | **Live API:** brain query for customer evidence HTTP 200. Evidence on task detail verified in pytest `test_end_to_end_task7_operating_loop`. |
| Learning proposal | **NOT RUN** | Covered by `test_learning_proposal`, Task 7 e2e (pytest). |
| Learning approval | **NOT RUN** | Covered by `test_learning_approval`, Task 7 e2e (pytest). |
| Learning rejection | **NOT RUN** | Covered by `test_rejection_path_keeps_learning_out_of_brain` (pytest). |
| Learning correction | **NOT RUN** | Covered by Task 7 e2e supersede path (pytest). |
| Tenant isolation | **NOT RUN** | **Live API:** cross-company task access 403/404; company B cannot see company A objectives. Pytest tenant suite also green. |
| Company switching | **NOT RUN** | Stale-request guards in frontend code (8.7); no browser Network-tab verification. |
| Error handling | **NOT RUN** | **Live API:** invalid task 404, invalid company 403, unauthorized cross-company 403. Browser error UX not verified. |
| Performance | **NOT RUN** | Dashboard `Promise.all` parallel fetch present in code; no browser Network-tab profiling. Head Agent latency measured via live API only. |
| Mobile (~390px) | **NOT RUN** | |
| Accessibility | **NOT RUN** | Code review only: company select `aria-label="Select company"`, approval button labels, TaskDialog semantics, `aria-live` on Head Agent panel. |

---

## 9. Complete Operating Loop

### Live API smoke (2026-08-30)

Executed against running `forge-api` at `127.0.0.1:8000`:

1. Register user → create company → create objective — **OK**
2. Head Agent stage / next-action / revenue / injection questions — **OK** (slow LLM, grounded)
3. Request approval on recommendation — **OK** (status `pending`, no task yet)
4. Approve — **OK** (exactly 1 objective task created)
5. Task status transitions — **OK**
6. Task complete with result_summary/metrics/notes — **OK** (HTTP 200)
7. Brain query for customer evidence — **OK**
8. Tenant isolation (two companies) — **OK**

### Pytest E2E (same session)

| Test | Result |
|------|--------|
| `test_end_to_end_task7_operating_loop` | Included in 491 pass |
| `test_end_to_end_operating_loop_with_approval_gate` | Included in 491 pass |
| `test_tenant_isolation` | Included in 491 pass |
| `test_learning_approval` | Included in 491 pass |

**Verdict:** Operating loop is **verified at API/service layer** (live + pytest). **Browser UI workflow not manually verified.**

---

## 10. Tenant Isolation

| Layer | Result | Notes |
|-------|--------|-------|
| Backend API (live) | **PASS** | Cross-company access returns 403/404 |
| Backend pytest | **PASS** | `test_tenant_isolation`, cross-company tests |
| Browser company switch | **NOT RUN** | |

---

## 11. Company Switching

| Check | Result |
|-------|--------|
| Stale-request guards (code) | Present in `FounderCommandCenter`, `FounderTaskWorkspace`, `TaskDetailView` |
| Browser switch A→B→A | **NOT RUN** |
| Network tab stale data check | **NOT RUN** |

---

## 12. Security

| Check | Result |
|-------|--------|
| `APP_ENV=production` requires strong `SECRET_KEY` | **VERIFIED** (`verify_config.py`) |
| `CORS_ORIGINS` configurable | **VERIFIED** |
| Production cookies `secure=True` | **VERIFIED** (`security.py` `_cookie_secure()`) |
| Hardcoded secrets in app source | **NONE FOUND** (grep; test fixtures only) |
| Global safe 500 handler | **PRESENT** (`main.py` — no stack trace to client) |
| Approval boundary | **VERIFIED** — tasks only after approval (live API + pytest) |
| Head Agent recommend-only | **VERIFIED** — no autonomous mutations |

---

## 13. Performance

### Head Agent (live API, Newtron ultra 550b, 2026-08-30)

| Request | Latency |
|---------|---------|
| Request 1 (company stage) | **53.13 s** |
| Request 2 (get more customers) | **60.62 s** |
| Request 3 (monthly revenue) | **51.84 s** |
| **Approximate average** | **55.2 s** |

**Assessment:** LLM provider latency dominates. Responses are **not fast** (well above 10 seconds). Consistent with Task 8.9 findings.

### Dashboard parallel load

- Code: `FounderCommandCenter` uses `Promise.all` for objectives, approvals, tasks, learnings.
- Browser Network-tab verification: **NOT RUN**

---

## 14. Mobile

**NOT RUN** — no 390px viewport browser testing.

---

## 15. Accessibility

**NOT RUN** (browser). Code review confirms:

- Company selector `aria-label="Select company"` on dashboard and task pages
- Approval actions `aria-label` on approve/reject buttons
- `TaskDialog` with `aria-labelledby` and close button label
- Head Agent loading `aria-live` region
- Task status badges with `aria-label`

Keyboard focus, Escape behavior, and visible focus states: **not browser-tested**.

---

## 16. Bugs Found

| ID | Severity | Finding |
|----|----------|---------|
| B1 | Process | Browser manual smoke tests still not executed |
| — | None | No new product bugs identified in this gate pass |

---

## 17. Bugs Fixed

No functional product bugs found in this gate pass. Prior 8.11 pass fixed Ruff E501 in benchmark files only (style).

---

## 18. Remaining Risks

1. **Manual browser founder workflow not verified** — highest release risk
2. **Head Agent latency** — ~50–60s per request in live test; high provider variance
3. **No frontend integration tests** for company switching UX
4. **Task 8.10 LLM benchmark report** incomplete in repo
5. **Solo-founder MVP auth** — any company member can trigger LLM endpoints (documented)

---

## 19. Production Requirements

```env
APP_ENV=production
SECRET_KEY=<strong-random-secret>
DATABASE_URL=<production-postgres-with-pgvector>
CORS_ORIGINS=https://<frontend-origin>
NEWTRON_API_KEY=<secret>
LLM_MODEL=<benchmark-selected-model>
NEXT_PUBLIC_API_URL=<api-origin>
```

**Pre-release checklist:**

1. `docker compose up -d postgres` (or managed Postgres with pgvector)
2. `alembic upgrade head` && `alembic current` at `c2e8f19a24b5`
3. `pytest` — all green (491 tests)
4. Manual founder smoke (§8 table) in a **real browser**
5. Verify Head Agent UX under real network latency

---

## 20. Final Release Decision

**READY WITH FIXES**

| Gate | Status |
|------|--------|
| Infrastructure (Docker + Postgres) | **PASS** |
| Migrations | **PASS** |
| Backend pytest (491) | **PASS** |
| Frontend test + build | **PASS** |
| Ruff | **PASS** (1 pre-existing E501) |
| Live API + frontend servers | **PASS** |
| Live API operating-loop smoke | **PASS** |
| Browser manual founder smoke | **NOT RUN** |
| Security config guards | **PASS** |

**Forge is NOT ready to begin Task 9** until browser manual scenarios in §8 are executed and marked PASS.

---

## 21. Task 9 Recommendation

**Do not start Task 9.**

Complete browser-based founder smoke test (login through learning correction, tenant switch, mobile, a11y, error UX) in a live environment. If all §8 scenarios pass with no blocking bugs, re-run this gate and set decision to **READY FOR TASK 9**.

Task 8 **implementation** is complete and **automated verification** is green. **Release verification** remains incomplete due to missing browser smoke.

---

## 16. Final Automated Results (summary)

| Check | Result |
|-------|--------|
| Backend pytest | **491 passed** (197.14s) |
| Frontend npm test | **62 passed** |
| Frontend build | **PASS** |
| Ruff | **1 pre-existing E501** (`onboarding.py:147`) |
| Alembic | **c2e8f19a24b5 (head)** |
