import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approveApproval,
  rejectApproval,
  requestHeadAgentRecommendation,
} from "./api";

describe("operating API integration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits head agent questions to the recommend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        agent_task_id: "task-1",
        recommendation: {
          title: "Talk to founders",
          recommendation: "Interview five founders.",
          rationale: "Grounded.",
          proposed_action: { type: "task", title: "Interview", description: "Ask questions" },
          sources: [],
          confidence: "medium",
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await requestHeadAgentRecommendation("company-1", "What should I focus on next?");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/head-agent/recommend",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ question: "What should I focus on next?" }),
      }),
    );
    expect(response.agent_task_id).toBe("task-1");
  });

  it("approve calls the existing approval endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "approval-1",
        company_id: "company-1",
        agent_task_id: "task-1",
        action_type: "task",
        description: "Talk to founders",
        risk_level: "low",
        status: "approved",
        requested_at: "2026-08-24T00:00:00Z",
        resolved_at: "2026-08-24T01:00:00Z",
        resolved_by: "user-1",
        objective_task_id: "objective-task-1",
        recommendation: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await approveApproval("company-1", "approval-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/approvals/approval-1/approve",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });

  it("reject calls the existing approval endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "approval-1",
        company_id: "company-1",
        agent_task_id: "task-1",
        action_type: "task",
        description: "Talk to founders",
        risk_level: "low",
        status: "rejected",
        requested_at: "2026-08-24T00:00:00Z",
        resolved_at: "2026-08-24T01:00:00Z",
        resolved_by: "user-1",
        objective_task_id: null,
        recommendation: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await rejectApproval("company-1", "approval-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/approvals/approval-1/reject",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });
});
