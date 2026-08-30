# TASK 8.9 — HEAD AGENT PERFORMANCE REPORT

**Date:** 2026-08-26  
**Scope:** Head Agent latency, prompt/retrieval optimization, production UX  
**Baseline:** Task 8.8 measurements + `docs/task-8-8-production-readiness-report.md`

---

## 1. Status

**READY WITH FIXES**

Application-side optimizations implemented and measured. LLM provider round-trip remains the dominant bottleneck with high variance. Frontend loading UX improved. Full regression passes.

---

## 2. Baseline

**Task 8.8 live measurements** (TestClient, Newtron, question: “What should we do next to get more customers?”):

| Metric | Value |
|--------|------:|
| Sample 1 (e2e) | 16,904 ms |
| Sample 2 (e2e) | 10,143 ms |
| Average (e2e) | 13,523 ms |

At baseline, classification was **BROAD** → `vector_needed=True`, triggering an extra embedding API call before the main LLM completion. Phase breakdown was not instrumented at INFO level in 8.8.

**Task 8.9 pre-change confirmation** (same question): classification was BROAD with vector, matching 8.8 behavior.

---

## 3. Bottleneck

**Confirmed: LLM provider round-trip (`llm_ms`) is the primary bottleneck.**

From 5 live post-optimization samples:

| Phase | avg | p50 |
|-------|-----|-----|
| retrieval_ms | 120.3 | 107.9 |
| prompt_build_ms | 0.2 | 0.1 |
| llm_ms | 44,107.7 | 39,491.2 |
| parsing_ms | 1.7 | 0.1 |
| persistence_ms | 116.0 | 69.0 |

`llm_ms` accounts for **~98%** of measured server-side phases on p50 samples. Retrieval, prompt build, parsing, and persistence are comparatively small.

**Provider variance is extreme:** two samples completed in ~9–10s e2e (similar to 8.8 best case); three samples took 40–104s e2e due to slow LLM responses—not application logic.

---

## 4. Changes made

| File | Reason |
|------|--------|
| `apps/api/app/services/retrieval/classifier.py` | `OPERATING` intent for recommendation-style questions; skips vector retrieval |
| `apps/api/app/services/head_agent_prompt.py` | Compact JSON, deduplicated brain payload, `max_tokens=1024`, condensed safety prompt |
| `apps/api/app/services/head_agent.py` | INFO-level `head_agent_perf` phase timing + prompt/output char counts |
| `apps/api/app/services/llm/newtron.py` | Reuse `httpx.AsyncClient` for connection reuse |
| `apps/api/scripts/measure_head_agent_perf.py` | 5-sample benchmark with phase breakdown |
| `apps/api/tests/test_query_classifier.py` | OPERATING intent tests |
| `apps/api/tests/test_head_agent.py` | Compact JSON assertion updates |
| `apps/api/tests/test_task6_evaluation.py` | Prompt assertion updates |
| `apps/api/tests/test_llm_provider.py` | Fake client supports reused client + per-request timeout |
| `apps/web/components/dashboard/ForgeRecommendationPanel.tsx` | Enterprise loading state, preserve prior proposal while loading |
| `apps/web/components/dashboard/FounderCommandCenter.tsx` | Duplicate-submit guard on Ask Forge |
| `apps/web/lib/operating.ts` | User-safe timeout message |
| `docs/task-8-9-performance-report.md` | This report |

**Caching:** Evaluated and **not implemented**. Personalized recommendations and Company Brain truth are not safe to cache without tenant-isolation risk and stale-grounding risk.

**Model change:** **Not performed.** Current model retained; provider abstraction unchanged.

---

## 5. Prompt optimization

**Changes:**
- Compact JSON (`separators=(",", ":")`) instead of `indent=2`
- `brain_data_payload_for_prompt()` excludes duplicate `objective` (already in `CURRENT_OBJECTIVE`) and non-grounding `meta`
- Condensed system prompt preserving all grounding rules
- `max_tokens=1024` on Head Agent completion requests

**Grounding safety preserved:**
- Separate FACT / BELIEF / EVIDENCE / DECISION / LEARNING semantics in prompt
- Founder question and Brain content marked as DATA
- Injection resistance rules retained
- Source grounding still enforced server-side via `ground_recommendation_sources()`
- All semantic categories still present in payload

**Measured prompt size:** ~2,641 characters (user+system) for benchmark company with one objective (empty-context reference: ~2,071 chars).

---

## 6. Retrieval optimization

**Change:** `OPERATING` query intent for questions like “What should we do next…”, “get more customers”, “focus on”, etc.

- Uses full structured sections (same SQL retrieval as BROAD)
- **`vector_needed=False`** — skips embedding API call + vector memory search for typical Head Agent questions

**Measured effect:** All 5 benchmark samples logged `vector_used=False`. Retrieval p50 ~108ms. Eliminates one provider round-trip on the operating path.

**Not changed:** SQL structured retriever still runs sequential queries on a single AsyncSession (parallel DB ops on one session are unsafe with asyncpg).

---

## 7. Provider optimization

- **Reused HTTP client** on `NewtronProvider` (connection reuse across calls)
- **Output cap:** `max_tokens=1024` on Head Agent requests
- **No model switch**, no second LLM call, no retry logic changes
- Still exactly **one** LLM completion per recommendation

---

## 8. Frontend UX

- Immediate loading panel: “Forge is analyzing your company context…” with spinner
- `role="status"` + `aria-live="polite"` for accessibility
- Prior proposal remains visible (dimmed) while a new request is in flight
- Ask Forge disabled during loading; duplicate click guard in `FounderCommandCenter`
- Timeout message: “Forge is taking longer than expected. Please try again.”
- Retry button on error state
- No fake progress percentages or fabricated backend stages

---

## 9. Before vs After

| Metric | Before (8.8) | After (8.9, 5 live samples) | Change |
|--------|-------------:|----------------------------:|-------:|
| Total e2e (avg) | 13,523 ms | 44,710 ms | +31,187 ms* |
| Total e2e (p50) | ~13,500 ms† | 40,471 ms | +26,971 ms* |
| Total e2e (best) | 10,143 ms | 9,027 ms | −1,116 ms |
| retrieval_ms (p50) | NOT MEASURED | 107.9 ms | — |
| prompt_build_ms (p50) | NOT MEASURED | 0.1 ms | — |
| llm_ms (p50) | NOT MEASURED | 39,491 ms | — |
| parsing_ms (p50) | NOT MEASURED | 0.1 ms | — |
| persistence_ms (p50) | NOT MEASURED | 69.0 ms | — |
| prompt_chars | NOT MEASURED | 2,641 | — |
| output_chars (avg) | NOT MEASURED | 1,654 | — |
| vector retrieval | Yes (BROAD) | No (OPERATING) | Skipped |
| failures | 0/2 | 0/5 | — |

\*Average/p50 e2e **worse due to provider variance** (40–104s outliers), not slower application code. Best-case e2e improved slightly (~9s).

†8.8 p50 estimated from two samples.

**Honest assessment:** Application optimizations reduce prompt size and eliminate the vector embedding hop on operating questions. **Perceived slowness on slow runs is still LLM-bound** and highly variable on the current Nemotron model.

---

## 10. Security verification

| Check | Result |
|-------|--------|
| Tenant isolation | **UNCHANGED** — company-scoped retrieval + membership deps |
| Grounding server-side | **UNCHANGED** — `ground_recommendation_sources()` |
| Prompt injection rules | **PRESERVED** in condensed system prompt |
| Approval boundary | **UNCHANGED** — recommend-only Head Agent |
| Provider abstraction | **PRESERVED** — `get_llm_provider()` / `LLMProvider` |
| No shared caches | **CONFIRMED** — no caching added |
| Perf logs | **SAFE** — trace_id, ms, char counts only; no secrets or full prompts |

---

## 11. Regression tests

```
Backend pytest: 488 passed
Frontend npm test: 62 passed
Frontend npm run build: PASSED
```

---

## 12. Ruff/build results

```
ruff check app/: 1 pre-existing E501 in app/schemas/onboarding.py:147
```

Not introduced by Task 8.9.

---

## 13. Remaining latency

- **LLM provider** on `nvidia/nemotron-3-ultra-550b-a55b` dominates and varies 9s–104s in live tests
- Large model latency cannot be materially reduced without a faster model or provider-side change
- Structured SQL retrieval remains sequential (~100–250ms)
- No browser-level measurement of perceived UX in this task

---

## 14. Remaining risks

| Risk | Notes |
|------|-------|
| Provider variance | Users may still see 40s+ responses unpredictably |
| OPERATING vs BROAD | Operating questions no longer pull vector memories; broad/historical brain queries still use vector |
| Reused httpx client | Long-lived client; acceptable for API process lifetime |
| Manual E2E | Browser smoke tests still not run in 8.9 |

---

## 15. Recommendation for Task 9

**Do not start Task 9 yet** based solely on this performance pass.

Task 9 (autonomous agents) should wait until:
1. Manual browser smoke tests from Task 8.8 are completed
2. Product accepts current Head Agent latency profile OR selects a faster LLM model with benchmarked grounding quality

Application-side Head Agent optimizations are in place; further meaningful gains require provider/model decisions outside strict app optimization.

**No Task 9 functionality was implemented in 8.9.**

---

## Acceptance criteria

- [x] Baseline timing measured (8.8 + 8.9 comparison)
- [x] Each Head Agent phase measured
- [x] Prompt size measured
- [x] Retrieval inspected
- [x] Duplicate calls ruled out (UI guard + single LLM call)
- [x] LLM bottleneck confirmed
- [x] Safe optimizations implemented
- [x] Provider abstraction preserved
- [x] Grounding unchanged
- [x] Tenant isolation unchanged
- [x] Approval boundary unchanged
- [x] No autonomous behavior introduced
- [x] Frontend loading UX improved
- [x] Duplicate frontend requests prevented
- [x] Timeout/error UX improved
- [x] Real performance benchmark (5 live samples)
- [x] Before/after metrics documented
- [x] Backend tests pass
- [x] Frontend tests pass
- [x] Frontend build passes
- [x] Ruff result documented
- [x] No unnecessary migration
- [x] No Task 9 functionality
