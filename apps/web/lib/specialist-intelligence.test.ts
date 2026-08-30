import { describe, expect, it } from "vitest";

import type {
  Approval,
  HeadAgentRecommendResponse,
  HeadAgentRecommendation,
  RecommendationSource,
} from "./api";
import {
  confidenceExplanation,
  confidenceLabel,
  formatOrchestrationMode,
  formatSourceLabel,
  formatSpecialistAgentType,
  groupSourceLabels,
  hasSpecialistAnalyses,
  normalizeRecommendResponse,
  recommendationApprovalStatus,
  shouldShowMultiSpecialistPerspectives,
} from "./specialist-intelligence";

const baseRecommendation = (
  overrides: Partial<HeadAgentRecommendation> = {},
): HeadAgentRecommendation => ({
  title: "Interview founders",
  recommendation: "Run five customer interviews.",
  rationale: "Grounded in objective.",
  proposed_action: {
    type: "task",
    title: "Run interviews",
    description: "Focus on onboarding friction.",
  },
  sources: [
    {
      entity_type: "evidence",
      entity_id: "e1",
      source_type: "manual",
      source_reference: null,
      title: "Interview notes",
    },
  ],
  confidence: "medium",
  ...overrides,
});

const headOnlyResponse = (
  overrides: Partial<HeadAgentRecommendResponse> = {},
): HeadAgentRecommendResponse => ({
  agent_task_id: "task-1",
  recommendation: baseRecommendation(),
  orchestration_mode: "head_only",
  specialist_agents: [],
  specialist_analyses: [],
  founder_question: "What should we do next?",
  ...overrides,
});

const approval = (status: Approval["status"], agentTaskId = "task-1"): Approval => ({
  id: `approval-${status}`,
  company_id: "company-1",
  agent_task_id: agentTaskId,
  action_type: "task",
  description: "Approve task",
  risk_level: "low",
  status,
  requested_at: "2026-08-24T00:00:00Z",
  resolved_at: status === "pending" ? null : "2026-08-24T01:00:00Z",
  resolved_by: status === "pending" ? null : "user-1",
  objective_task_id: status === "approved" ? "objective-task-1" : null,
  learning_id: null,
  recommendation: null,
  learning_proposal: null,
});

describe("specialist intelligence helpers", () => {
  it("formats head_only orchestration display", () => {
    expect(formatOrchestrationMode("head_only")).toBe("Forge analysis");
    expect(hasSpecialistAnalyses(headOnlyResponse())).toBe(false);
  });

  it("formats customer_growth attribution", () => {
    expect(formatSpecialistAgentType("customer_growth")).toBe("Customer & Growth");
    const response = headOnlyResponse({
      orchestration_mode: "single_specialist",
      specialist_agents: ["customer_growth"],
      specialist_analyses: [
        {
          agent_type: "customer_growth",
          domain: "customer_growth",
          display_name: "Customer & Growth",
          agent_task_id: "spec-1",
          title: "Acquisition focus",
          recommendation: "Improve acquisition channels.",
          rationale: "ICP signal is strong.",
          confidence: "medium",
          sources: [],
        },
      ],
    });
    expect(hasSpecialistAnalyses(response)).toBe(true);
  });

  it("formats product attribution", () => {
    expect(formatSpecialistAgentType("product")).toBe("Product");
    expect(
      formatSpecialistAgentType("product"),
    ).not.toBe(formatSpecialistAgentType("customer_growth"));
  });

  it("supports multi-specialist attribution", () => {
    const response = headOnlyResponse({
      orchestration_mode: "multi_specialist",
      specialist_agents: ["customer_growth", "product"],
      specialist_analyses: [
        {
          agent_type: "customer_growth",
          domain: "customer_growth",
          display_name: "Customer & Growth",
          agent_task_id: "spec-1",
          title: "Growth view",
          recommendation: "Improve conversion.",
          rationale: "Funnel data.",
          confidence: "medium",
          sources: [],
        },
        {
          agent_type: "product",
          domain: "product",
          display_name: "Product",
          agent_task_id: "spec-2",
          title: "Product view",
          recommendation: "Improve onboarding.",
          rationale: "UX friction.",
          confidence: "medium",
          sources: [],
        },
      ],
    });
    expect(shouldShowMultiSpecialistPerspectives(response)).toBe(true);
    expect(response.specialist_agents).toEqual(["customer_growth", "product"]);
  });

  it("falls back for unknown specialist types", () => {
    expect(formatSpecialistAgentType("finance_ops")).toBe("Specialist analysis");
  });

  it("maps confidence labels and explanations", () => {
    expect(confidenceLabel("low")).toBe("LOW CONFIDENCE");
    expect(confidenceExplanation("high")).toBe(
      "Strongly grounded in available company evidence.",
    );
  });

  it("formats grounded source labels", () => {
    const sources: RecommendationSource[] = [
      {
        entity_type: "objective",
        entity_id: "o1",
        source_type: "manual",
        source_reference: null,
        title: "Grow revenue",
      },
      {
        entity_type: "evidence",
        entity_id: "e1",
        source_type: "manual",
        source_reference: null,
        title: "Customer call",
      },
    ];
    expect(groupSourceLabels(sources)).toEqual(["objective", "evidence"]);
    expect(formatSourceLabel(sources[0])).toContain("objective");
  });

  it("detects proposed task actions", () => {
    const withTask = baseRecommendation({
      proposed_action: { type: "task", title: "Ship interviews", description: "" },
    });
    const withoutTask = baseRecommendation({
      proposed_action: { type: "none", title: "", description: "" },
    });
    expect(withTask.proposed_action.type).toBe("task");
    expect(withoutTask.proposed_action.type).toBe("none");
  });

  it("derives approval presentation states", () => {
    expect(
      recommendationApprovalStatus([approval("pending")], "task-1", true),
    ).toBe("pending");
    expect(
      recommendationApprovalStatus([approval("approved")], "task-1", true),
    ).toBe("approved");
    expect(
      recommendationApprovalStatus([approval("rejected")], "task-1", true),
    ).toBe("rejected");
    expect(recommendationApprovalStatus([], "task-1", true)).toBe("can_request");
    expect(recommendationApprovalStatus([], "task-1", false)).toBe("none");
  });

  it("handles missing specialist data", () => {
    const response = headOnlyResponse({
      orchestration_mode: "single_specialist",
      specialist_agents: ["customer_growth"],
      specialist_analyses: [],
    });
    expect(hasSpecialistAnalyses(response)).toBe(false);
    expect(normalizeRecommendResponse(response)?.specialist_analyses).toEqual([]);
  });

  it("does not infer conflict data from text", () => {
    const response = headOnlyResponse({
      orchestration_mode: "multi_specialist",
      recommendation: baseRecommendation({
        rationale: "Specialists conflict on priority but synthesis explains tradeoffs.",
      }),
      specialist_analyses: [
        {
          agent_type: "customer_growth",
          domain: "customer_growth",
          display_name: "Customer & Growth",
          agent_task_id: "spec-1",
          title: "Growth",
          recommendation: "Focus acquisition.",
          rationale: "Pipeline weak.",
          confidence: "medium",
          sources: [],
        },
        {
          agent_type: "product",
          domain: "product",
          display_name: "Product",
          agent_task_id: "spec-2",
          title: "Product",
          recommendation: "Focus onboarding.",
          rationale: "Activation weak.",
          confidence: "medium",
          sources: [],
        },
      ],
    });
    expect(shouldShowMultiSpecialistPerspectives(response)).toBe(true);
    expect((response as { conflicts?: unknown }).conflicts).toBeUndefined();
  });

  it("normalizes malformed or partial responses", () => {
    const partial = {
      agent_task_id: "task-1",
      recommendation: baseRecommendation(),
    } as HeadAgentRecommendResponse;
    const normalized = normalizeRecommendResponse(partial);
    expect(normalized?.orchestration_mode).toBe("head_only");
    expect(normalized?.specialist_agents).toEqual([]);
    expect(normalized?.specialist_analyses).toEqual([]);
    expect(normalizeRecommendResponse(null)).toBeNull();
  });
});
