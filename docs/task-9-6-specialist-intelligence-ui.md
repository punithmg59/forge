# Task 9.6 — Founder Specialist Intelligence UI

## Overview

Task 9.6 upgrades the Founder Command Center so founders can see how Forge orchestrates Head Agent routing, optional specialist analysis, synthesis, grounding, and approval-gated proposals.

**Scope:** presentation only. No new autonomy, tools, integrations, or automatic mutations.

## UI architecture

```
FounderCommandCenter
  └── SectionCard ("Forge recommendation")
        └── ForgeRecommendationPanel
              ├── ForgeAnalyzingState (loading)
              ├── OrchestrationHeader (question, mode, specialists)
              ├── HeadSynthesisPanel (final recommendation)
              ├── ProposedActionCard (approval-gated proposal)
              └── SpecialistAnalysisPanel (when backend provides analyses)
```

Supporting components:

- `RecommendationConfidence.tsx` — confidence label + explanation
- `RecommendationSources.tsx` — Company Brain provenance (distinct from AI analysis)
- `lib/specialist-intelligence.ts` — pure display helpers (no orchestration logic)

## API contract

Single request: `POST /companies/{company_id}/head-agent/recommend`

Response (`HeadAgentRecommendResponse`):

| Field | Purpose |
|-------|---------|
| `agent_task_id` | Recommendation task for approval linkage |
| `recommendation` | Head Agent synthesis (title, recommendation, rationale, confidence, sources, proposed_action) |
| `orchestration_mode` | `head_only`, `single_specialist`, or `multi_specialist` |
| `specialist_agents` | Specialist types consulted |
| `specialist_analyses` | Per-specialist summaries when specialists ran |
| `founder_question` | Resolved founder question |

The frontend does **not** call specialists directly. It renders only what this response provides.

## Specialist attribution

Centralized in `formatSpecialistAgentType()`:

| Backend `agent_type` | UI label |
|----------------------|----------|
| `customer_growth` | Customer & Growth |
| `product` | Product |
| unknown | Specialist analysis |

Orchestration labels (`formatOrchestrationMode`):

| Mode | Label |
|------|-------|
| `head_only` | Forge analysis |
| `single_specialist` | Specialist analysis |
| `multi_specialist` | Multi-specialist analysis |

## Orchestration display

- **Head-only:** synthesis panel only; no specialist cards or fake attribution.
- **Single/multi specialist:** orchestration header shows consulted specialists; `SpecialistAnalysisPanel` renders backend `specialist_analyses`.
- If mode implies specialists but analyses are empty: show “No specialist analysis was used for this recommendation.”

## Grounding display

- Head synthesis sources use `RecommendationSources` with “Grounded in Company Brain” and explicit note that these are Brain sources, not AI analysis.
- Specialist cards may show their own grounding references separately.
- Specialist output is never styled as Company Brain truth.

## Approval behavior

Reuses existing approval APIs:

- `createApproval` — request approval on `agent_task_id`
- `approveApproval` / `rejectApproval` — via `AttentionPanel`

`ProposedActionCard` states proposals do not mutate company state until approved. No auto-approval or direct `ObjectiveTask` creation from the UI.

## Loading and error behavior

- Previous recommendation stays visible while a new request is in flight.
- “Preparing a new recommendation…” + `ForgeAnalyzingState` during loading.
- Ask Forge disabled while loading (duplicate requests prevented).
- Errors use `mapRecommendationApiError` — no stack traces or provider details.
- Retry preserves prior successful recommendation when applicable.

## Security

- Frontend displays `company_id`, specialist metadata, and IDs only; authorization remains on the backend.
- No client-side orchestration or grounding logic.
- Company switch clears recommendation state (`resetCompanyState`).

## Performance

- One Head Agent request per Ask Forge action.
- No polling, no per-specialist browser calls, no N+1 fetches.

## Testing

Frontend: `apps/web/lib/specialist-intelligence.test.ts` (pure helpers).

Run:

```bash
cd apps/web && npm test
cd apps/web && npm run build
cd apps/api && pytest -q
cd apps/api && ruff check app/
```

## Manual verification checklist

1. **Head-only** — “What should we do next?” → Forge analysis, no specialist UI.
2. **Customer/Growth** — acquisition question → Customer & Growth + analysis + synthesis.
3. **Product** — feature prioritization → Product + analysis + synthesis.
4. **Mixed** — onboarding + conversion → both specialists + synthesis.
5. **Approval** — request → approve → one founder task, no duplicate.
6. **Reject** — request → reject → no task created.
7. **Loading** — previous recommendation visible; duplicate click blocked.
8. **Error** — safe message + retry; no stack trace.
9. **Company switch** — old recommendation cleared; no cross-tenant leakage.
10. **Mobile** — single column, no horizontal overflow, usable buttons.

## Limitations

- No structured conflict payload from backend; UI does not infer conflicts from text.
- Loading stages are generic (backend does not expose per-phase telemetry).
- Specialist analysis content is exactly what specialists returned — no frontend reinterpretation.

## Out of scope (not implemented)

- Task 9.7
- Task 9.8
- Autonomous execution, external tools, CRM/analytics integrations, background agents
