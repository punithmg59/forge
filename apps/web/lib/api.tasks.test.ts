import { afterEach, describe, expect, it, vi } from "vitest";

import {
  completeObjectiveTask,
  getObjectiveTaskDetail,
  listFounderTasks,
  transitionObjectiveTaskStatus,
  updateObjectiveTask,
  type ObjectiveTaskDetail,
} from "./api";

const DETAIL: ObjectiveTaskDetail = {
  id: "task-1",
  company_id: "company-1",
  objective_id: "objective-1",
  title: "Interview founders",
  description: "Ask about onboarding pain.",
  capability: "founder",
  status: "pending",
  priority: "medium",
  requires_approval: false,
  started_at: null,
  blocked_reason: null,
  result_summary: null,
  result_metrics: null,
  result_notes: null,
  completed_by: null,
  completed_at: null,
  created_at: "2026-08-26T00:00:00Z",
  updated_at: "2026-08-26T00:00:00Z",
  objective: { id: "objective-1", title: "Get customers", status: "active" },
  result: null,
  provenance: {
    agent_task_id: "agent-1",
    agent_run_id: null,
    approval_id: "approval-1",
    objective_id: "objective-1",
  },
  evidence: [],
  learnings: [],
  recommendation: null,
  recommendation_question: null,
  approval_context: null,
};

describe("objective task API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists founder tasks from the correct path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tasks: [{ ...DETAIL }] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await listFounderTasks("company-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/objective-tasks",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(response.tasks.length).toBe(1);
    expect(response.tasks[0].title).toBe("Interview founders");
  });

  it("fetches task detail from the correct path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => DETAIL,
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getObjectiveTaskDetail("company-1", "task-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/objective-tasks/task-1",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(response.objective?.title).toBe("Get customers");
    expect(response.evidence).toEqual([]);
  });

  it("updates task metadata via PATCH", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...DETAIL, title: "Updated title" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await updateObjectiveTask("company-1", "task-1", {
      title: "Updated title",
      priority: "high",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/objective-tasks/task-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "Updated title", priority: "high" }),
      }),
    );
  });

  it("transitions status via PATCH /status", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...DETAIL, status: "in_progress" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await transitionObjectiveTaskStatus("company-1", "task-1", {
      status: "in_progress",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/objective-tasks/task-1/status",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "in_progress" }),
      }),
    );
  });

  it("blocks task with reason", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...DETAIL,
        status: "blocked",
        blocked_reason: "Waiting for access.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await transitionObjectiveTaskStatus("company-1", "task-1", {
      status: "blocked",
      blocked_reason: "Waiting for access.",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/status"),
      expect.objectContaining({
        body: JSON.stringify({
          status: "blocked",
          blocked_reason: "Waiting for access.",
        }),
      }),
    );
  });

  it("completes task via POST /complete", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...DETAIL,
        status: "completed",
        result_summary: "Done.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await completeObjectiveTask("company-1", "task-1", {
      result_summary: "Done.",
      result_metrics: { interviewed: 12 },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/companies/company-1/objective-tasks/task-1/complete",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          result_summary: "Done.",
          result_metrics: { interviewed: 12 },
        }),
      }),
    );
  });
});
