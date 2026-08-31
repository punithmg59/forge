import { describe, expect, it } from "vitest";

import type { ObjectiveTaskDetail } from "./api";
import {
  buildProvenanceChain,
  describeWorkflowNextStep,
  EXECUTION_CONTEXT_MESSAGES,
  formatApprovalStatus,
  recommendationPrimaryText,
} from "./execution-context";

function makeDetail(overrides: Partial<ObjectiveTaskDetail> = {}): ObjectiveTaskDetail {
  return {
    id: "task-1",
    company_id: "company-1",
    objective_id: "obj-1",
    title: "Customer interviews",
    description: "Interview early users.",
    capability: "founder",
    status: "in_progress",
    priority: "high",
    requires_approval: false,
    started_at: "2026-08-26T08:00:00Z",
    blocked_reason: null,
    result_summary: null,
    result_metrics: null,
    result_notes: null,
    completed_by: null,
    completed_at: null,
    created_at: "2026-08-26T00:00:00Z",
    updated_at: "2026-08-26T12:00:00Z",
    objective: { id: "obj-1", title: "Get first 100 customers", status: "active" },
    result: null,
    provenance: {
      agent_task_id: "agent-1",
      agent_run_id: null,
      approval_id: "approval-1",
      objective_id: "obj-1",
    },
    evidence: [],
    learnings: [],
    recommendation: {
      title: "Interview customers",
      recommendation: "Interview 12 potential customers before increasing acquisition spend.",
      rationale: "Validate the customer problem first.",
      proposed_action: { type: "task", title: "Customer interviews", description: "" },
      sources: [],
      confidence: "high",
    },
    recommendation_question: "What should I focus on next?",
    approval_context: {
      status: "approved",
      description: "Approve founder task",
      action_type: "task",
      requested_at: "2026-08-26T00:00:00Z",
      resolved_at: "2026-08-26T01:00:00Z",
    },
    ...overrides,
  };
}

describe("execution context helpers", () => {
  it("builds provenance chain in source order", () => {
    const chain = buildProvenanceChain(makeDetail());
    expect(chain.map((node) => node.key)).toEqual([
      "objective",
      "recommendation",
      "approval",
      "task",
      "evidence",
      "learning",
    ]);
    expect(chain[0].title).toBe("Get first 100 customers");
    expect(chain[1].available).toBe(true);
    expect(chain[3].title).toBe("Customer interviews");
  });

  it("handles missing objective", () => {
    const chain = buildProvenanceChain(makeDetail({ objective: null }));
    expect(chain[0].title).toBe(EXECUTION_CONTEXT_MESSAGES.objectiveUnavailable);
    expect(chain[0].available).toBe(false);
  });

  it("handles missing recommendation without inventing content", () => {
    const chain = buildProvenanceChain(
      makeDetail({
        recommendation: null,
        provenance: {
          agent_task_id: "agent-1",
          agent_run_id: null,
          approval_id: null,
          objective_id: "obj-1",
        },
      }),
    );
    expect(chain[1].title).toBe(EXECUTION_CONTEXT_MESSAGES.recommendationUnavailable);
    expect(chain[1].available).toBe(false);
  });

  it("handles missing approval", () => {
    const chain = buildProvenanceChain(
      makeDetail({
        approval_context: null,
        provenance: {
          agent_task_id: "agent-1",
          agent_run_id: null,
          approval_id: null,
          objective_id: "obj-1",
        },
      }),
    );
    expect(chain[2].title).toBe(EXECUTION_CONTEXT_MESSAGES.approvalUnavailable);
    expect(chain[2].available).toBe(false);
  });

  it("handles missing evidence and learning", () => {
    const chain = buildProvenanceChain(makeDetail());
    expect(chain[4].title).toBe(EXECUTION_CONTEXT_MESSAGES.evidenceEmpty);
    expect(chain[5].title).toBe(EXECUTION_CONTEXT_MESSAGES.learningEmpty);
  });

  it("labels learning status explicitly", () => {
    const chain = buildProvenanceChain(
      makeDetail({
        learnings: [
          {
            id: "learning-1",
            statement: "Customer problem validated.",
            evidence_summary: null,
            confidence: 0.8,
            status: "proposed",
            evidence_id: "evidence-1",
            objective_id: "obj-1",
          },
        ],
      }),
    );
    expect(chain[5].detail).toBe("PROPOSED");
  });

  it("uses recommendation text rather than company fact wording", () => {
    const text = recommendationPrimaryText(makeDetail().recommendation!);
    expect(text).toContain("Interview 12 potential customers");
    expect(text).not.toContain("Company knows");
  });

  it("formats approval status labels", () => {
    expect(formatApprovalStatus("approved")).toBe("Approved");
    expect(formatApprovalStatus("pending")).toBe("Pending");
  });

  it("describes workflow next step without inventing automation", () => {
    expect(describeWorkflowNextStep(makeDetail({ status: "pending" }))).toContain("Start");
    expect(describeWorkflowNextStep(makeDetail({ status: "blocked" }))).toContain("blocked");
    expect(
      describeWorkflowNextStep(
        makeDetail({
          status: "completed",
          learnings: [
            {
              id: "learning-1",
              statement: "Test",
              evidence_summary: null,
              confidence: null,
              status: "proposed",
              evidence_id: "evidence-1",
              objective_id: "obj-1",
            },
          ],
        }),
      ),
    ).toContain("approval");
  });

  it("handles optional fields safely", () => {
    const chain = buildProvenanceChain(
      makeDetail({
        recommendation_question: null,
        started_at: null,
        blocked_reason: null,
      }),
    );
    expect(chain[1].detail).toBeNull();
    expect(chain[3].detail).toBe("In progress");
  });
});
