import { describe, expect, it } from "vitest";

import type { Approval, CompanyLearning, FounderTask } from "./api";
import {
  buildOperatingLoopState,
  FOUNDER_DASHBOARD_EMPTY,
  selectActiveLearnings,
  selectBlockedTasks,
  selectFocusTasks,
  selectRecentCompletedTasks,
  summarizeAttentionCounts,
} from "./founder-dashboard";
import { enrichTasksWithObjectives } from "./task-workspace";

function makeTask(overrides: Partial<FounderTask> = {}): FounderTask {
  return {
    id: overrides.id ?? "task-1",
    company_id: "company-1",
    objective_id: "obj-1",
    title: overrides.title ?? "Interview customers",
    description: null,
    capability: "founder",
    status: overrides.status ?? "pending",
    priority: overrides.priority ?? "medium",
    requires_approval: false,
    started_at: null,
    blocked_reason: overrides.blocked_reason ?? null,
    result_summary: overrides.result_summary ?? null,
    result_metrics: overrides.result_metrics ?? null,
    result_notes: null,
    completed_by: null,
    completed_at: overrides.completed_at ?? null,
    created_at: "2026-08-26T00:00:00Z",
    updated_at: overrides.updated_at ?? "2026-08-26T12:00:00Z",
  };
}

function makeApproval(id: string): Approval {
  return {
    id,
    company_id: "company-1",
    agent_task_id: `agent-${id}`,
    learning_id: null,
    action_type: "task",
    description: "Approve task",
    risk_level: "low",
    status: "pending",
    requested_at: "2026-08-26T00:00:00Z",
    resolved_at: null,
    resolved_by: null,
    objective_task_id: null,
    recommendation: null,
    learning_proposal: null,
  };
}

function makeLearning(status: string): CompanyLearning {
  return {
    id: "learning-1",
    company_id: "company-1",
    evidence_id: "evidence-1",
    objective_id: "obj-1",
    statement: "Customers prefer workflow tools.",
    evidence_summary: null,
    confidence: 0.8,
    status,
    created_at: "2026-08-26T00:00:00Z",
    updated_at: "2026-08-26T00:00:00Z",
    corrected_by: null,
    corrected_at: null,
    correction_reason: null,
    provenance: null,
    approval_status: null,
  };
}

describe("founder dashboard helpers", () => {
  const tasks = enrichTasksWithObjectives(
    [
      makeTask({
        id: "blocked-1",
        status: "blocked",
        priority: "high",
        blocked_reason: "Waiting for access",
      }),
      makeTask({ id: "progress-1", status: "in_progress", priority: "high" }),
      makeTask({ id: "pending-high", status: "pending", priority: "high", title: "Outreach" }),
      makeTask({ id: "pending-low", status: "pending", priority: "low" }),
      makeTask({
        id: "completed-1",
        status: "completed",
        completed_at: "2026-08-26T10:00:00Z",
        result_summary: "12 interviews completed.",
        result_metrics: { interviewed: 12 },
      }),
    ],
    [{ id: "obj-1", company_id: "c1", title: "Grow", description: null, status: "active", priority: 1, target_value: null, target_unit: null, deadline: null, created_at: "", updated_at: "" }],
  );

  it("prioritizes blocked tasks for attention", () => {
    expect(selectBlockedTasks(tasks).map((task) => task.id)).toEqual(["blocked-1"]);
  });

  it("counts pending approvals and blocked tasks", () => {
    const counts = summarizeAttentionCounts([makeApproval("1"), makeApproval("2")], selectBlockedTasks(tasks));
    expect(counts).toEqual({ pendingApprovals: 2, blockedTasks: 1, total: 3 });
  });

  it("selects focus tasks with in-progress before high-priority pending", () => {
    const focus = selectFocusTasks(tasks);
    expect(focus.map((task) => task.id)).toEqual(["progress-1", "pending-high", "pending-low"]);
  });

  it("selects recent completed tasks", () => {
    const recent = selectRecentCompletedTasks([
      makeTask({
        id: "completed-1",
        status: "completed",
        completed_at: "2026-08-26T10:00:00Z",
      }),
    ]);
    expect(recent.map((task) => task.id)).toEqual(["completed-1"]);
  });

  it("filters active learnings only for brain summary", () => {
    const learnings = [
      makeLearning("active"),
      makeLearning("proposed"),
      { ...makeLearning("superseded"), id: "learning-2", statement: "Old insight." },
    ];
    expect(selectActiveLearnings(learnings).every((l) => l.status === "active")).toBe(true);
    expect(selectActiveLearnings(learnings).length).toBe(1);
  });

  it("builds operating loop from actual records", () => {
    const stages = buildOperatingLoopState({
      hasObjective: true,
      hasPendingApprovals: true,
      hasTasks: true,
      hasCompletedTasks: true,
      hasLearnings: true,
      hasActiveLearnings: true,
    });
    expect(stages.filter((stage) => stage.active).length).toBeGreaterThan(0);
    expect(stages[0].label).toBe("Objective");
  });

  it("uses safe empty messages without inventing content", () => {
    expect(FOUNDER_DASHBOARD_EMPTY.brain).toContain("No active");
    expect(FOUNDER_DASHBOARD_EMPTY.recommendation).toBe("No recommendation yet.");
  });

  it("handles empty dashboard state", () => {
    expect(selectFocusTasks([])).toEqual([]);
    expect(selectRecentCompletedTasks([])).toEqual([]);
    expect(summarizeAttentionCounts([], []).total).toBe(0);
  });
});
