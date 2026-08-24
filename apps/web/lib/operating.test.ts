import { describe, expect, it } from "vitest";

import type { Approval, HeadAgentRecommendation, Objective } from "./api";
import {
  OPERATING_ERRORS,
  filterPendingApprovals,
  formatObjectiveMetric,
  hasPendingApprovalForAgentTask,
  isActionableRecommendation,
  objectiveTitleById,
} from "./operating";

const recommendation = (
  actionType: HeadAgentRecommendation["proposed_action"]["type"],
): HeadAgentRecommendation => ({
  title: "Talk to founders",
  recommendation: "Interview five technical founders.",
  rationale: "Grounded in the current objective.",
  proposed_action: {
    type: actionType,
    title: "Run interviews",
    description: "Ask about onboarding pain.",
  },
  sources: [{ entity_type: "fact", entity_id: "1", source_type: "manual", source_reference: null, title: null }],
  confidence: "medium",
});

describe("operating view helpers", () => {
  it("filters pending approvals only", () => {
    const approvals: Approval[] = [
      {
        id: "1",
        company_id: "c1",
        agent_task_id: "t1",
        action_type: "task",
        description: "Pending",
        risk_level: "low",
        status: "pending",
        requested_at: "2026-08-24T00:00:00Z",
        resolved_at: null,
        resolved_by: null,
        objective_task_id: null,
        recommendation: null,
      },
      {
        id: "2",
        company_id: "c1",
        agent_task_id: "t2",
        action_type: "task",
        description: "Approved",
        risk_level: "low",
        status: "approved",
        requested_at: "2026-08-24T00:00:00Z",
        resolved_at: "2026-08-24T01:00:00Z",
        resolved_by: "u1",
        objective_task_id: "task-1",
        recommendation: null,
      },
    ];
    expect(filterPendingApprovals(approvals)).toHaveLength(1);
    expect(filterPendingApprovals(approvals)[0].id).toBe("1");
  });

  it("detects actionable recommendations", () => {
    expect(isActionableRecommendation(recommendation("task"))).toBe(true);
    expect(isActionableRecommendation(recommendation("none"))).toBe(false);
  });

  it("formats objective metrics without inventing values", () => {
    const objective: Objective = {
      id: "o1",
      company_id: "c1",
      title: "Grow",
      description: null,
      status: "active",
      priority: 100,
      target_value: "10",
      target_unit: "customers",
      deadline: null,
      created_at: "",
      updated_at: "",
    };
    expect(formatObjectiveMetric(objective)).toBe("10 customers");
    expect(formatObjectiveMetric({ ...objective, target_value: null, target_unit: null })).toBeNull();
  });

  it("maps objective titles by id", () => {
    const objectives: Objective[] = [
      {
        id: "o1",
        company_id: "c1",
        title: "Get customers",
        description: null,
        status: "active",
        priority: 100,
        target_value: null,
        target_unit: null,
        deadline: null,
        created_at: "",
        updated_at: "",
      },
    ];
    expect(objectiveTitleById(objectives, "o1")).toBe("Get customers");
    expect(objectiveTitleById(objectives, "missing")).toBeNull();
  });

  it("detects existing pending approval for an agent task", () => {
    const approvals: Approval[] = [
      {
        id: "1",
        company_id: "c1",
        agent_task_id: "task-1",
        action_type: "task",
        description: "Pending",
        risk_level: "low",
        status: "pending",
        requested_at: "2026-08-24T00:00:00Z",
        resolved_at: null,
        resolved_by: null,
        objective_task_id: null,
        recommendation: null,
      },
    ];
    expect(hasPendingApprovalForAgentTask(approvals, "task-1")).toBe(true);
    expect(hasPendingApprovalForAgentTask(approvals, "task-2")).toBe(false);
    expect(hasPendingApprovalForAgentTask(approvals, null)).toBe(false);
  });

  it("uses safe operating error copy", () => {
    expect(OPERATING_ERRORS.recommendation).toContain("Forge could not generate a recommendation");
    expect(OPERATING_ERRORS.objective).toContain("Unable to load the current objective");
  });
});

describe("operating API contracts", () => {
  it("does not invent recommendation content in empty states", () => {
    expect(recommendation("none").proposed_action.type).toBe("none");
    expect(recommendation("task").title).toBe("Talk to founders");
  });
});
