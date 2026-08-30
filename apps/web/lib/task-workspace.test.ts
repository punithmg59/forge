import { describe, expect, it } from "vitest";

import type { FounderTask, Objective } from "./api";
import { ApiError } from "./api";
import { mapTaskApiError } from "./tasks";
import {
  computeTaskCounts,
  derivePriorityOptions,
  enrichTasksWithObjectives,
  filterWorkspaceTasks,
  groupWorkspaceTasks,
  hasActiveFilters,
  sortWorkspaceTasks,
  taskDetailPath,
  taskPriorityLabel,
  truncateDescription,
  type WorkspaceFilters,
  type WorkspaceTask,
} from "./task-workspace";

const OBJECTIVES: Objective[] = [
  {
    id: "obj-1",
    company_id: "company-1",
    title: "Get first 100 customers",
    description: null,
    status: "active",
    priority: 1,
    target_value: null,
    target_unit: null,
    deadline: null,
    created_at: "2026-08-26T00:00:00Z",
    updated_at: "2026-08-26T00:00:00Z",
  },
  {
    id: "obj-2",
    company_id: "company-1",
    title: "Improve activation",
    description: null,
    status: "active",
    priority: 2,
    target_value: null,
    target_unit: null,
    deadline: null,
    created_at: "2026-08-26T00:00:00Z",
    updated_at: "2026-08-26T00:00:00Z",
  },
];

function makeTask(overrides: Partial<FounderTask> = {}): FounderTask {
  return {
    id: "task-1",
    company_id: "company-1",
    objective_id: "obj-1",
    title: "Interview customers",
    description: "Talk to early users about onboarding.",
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
    updated_at: "2026-08-26T12:00:00Z",
    ...overrides,
  };
}

function workspaceTasks(): WorkspaceTask[] {
  return enrichTasksWithObjectives(
    [
      makeTask({
        id: "blocked-1",
        title: "Customer interviews",
        status: "blocked",
        priority: "high",
        blocked_reason: "Waiting for customer access",
        updated_at: "2026-08-26T10:00:00Z",
      }),
      makeTask({
        id: "progress-1",
        title: "Interview customers",
        status: "in_progress",
        priority: "high",
        started_at: "2026-08-26T08:00:00Z",
        updated_at: "2026-08-26T11:00:00Z",
      }),
      makeTask({
        id: "pending-1",
        title: "Prepare onboarding experiment",
        objective_id: "obj-2",
        status: "pending",
        priority: "medium",
        updated_at: "2026-08-26T09:00:00Z",
      }),
      makeTask({
        id: "pending-2",
        title: "Low priority follow-up",
        status: "pending",
        priority: "low",
        updated_at: "2026-08-26T07:00:00Z",
      }),
      makeTask({
        id: "completed-1",
        title: "Ship landing page",
        status: "completed",
        priority: "medium",
        completed_at: "2026-08-25T18:00:00Z",
        updated_at: "2026-08-25T18:00:00Z",
      }),
    ],
    OBJECTIVES,
  );
}

describe("task workspace helpers", () => {
  it("enriches tasks with objective titles", () => {
    const tasks = workspaceTasks();
    expect(tasks[0].objectiveTitle).toBe("Get first 100 customers");
    expect(tasks[2].objectiveTitle).toBe("Improve activation");
  });

  it("searches by title", () => {
    const tasks = workspaceTasks();
    const filtered = filterWorkspaceTasks(tasks, {
      search: "experiment",
      status: "all",
      priority: "all",
    });
    expect(filtered.map((task) => task.id)).toEqual(["pending-1"]);
  });

  it("searches by description", () => {
    const tasks = workspaceTasks();
    const filtered = filterWorkspaceTasks(tasks, {
      search: "early users",
      status: "all",
      priority: "all",
    });
    expect(filtered.length).toBeGreaterThan(0);
    expect(filtered.every((task) => task.description?.includes("early users"))).toBe(true);
  });

  it("searches by objective title", () => {
    const tasks = workspaceTasks();
    const filtered = filterWorkspaceTasks(tasks, {
      search: "improve activation",
      status: "all",
      priority: "all",
    });
    expect(filtered.map((task) => task.id)).toEqual(["pending-1"]);
  });

  it("searches case-insensitively with trimmed query", () => {
    const tasks = workspaceTasks();
    const filtered = filterWorkspaceTasks(tasks, {
      search: "  CUSTOMER ",
      status: "all",
      priority: "all",
    });
    expect(filtered.map((task) => task.id)).toEqual(
      expect.arrayContaining(["blocked-1", "progress-1"]),
    );
  });

  it("filters by status groups", () => {
    const tasks = workspaceTasks();
    expect(
      filterWorkspaceTasks(tasks, {
        search: "",
        status: "needs_attention",
        priority: "all",
      }).every((task) => task.status === "blocked"),
    ).toBe(true);
    expect(
      filterWorkspaceTasks(tasks, {
        search: "",
        status: "in_progress",
        priority: "all",
      }).map((task) => task.id),
    ).toEqual(["progress-1"]);
    expect(
      filterWorkspaceTasks(tasks, {
        search: "",
        status: "upcoming",
        priority: "all",
      }).every((task) => task.status === "pending"),
    ).toBe(true);
    expect(
      filterWorkspaceTasks(tasks, {
        search: "",
        status: "completed",
        priority: "all",
      }).map((task) => task.id),
    ).toEqual(["completed-1"]);
  });

  it("filters by priority", () => {
    const tasks = workspaceTasks();
    const filtered = filterWorkspaceTasks(tasks, {
      search: "",
      status: "all",
      priority: "high",
    });
    expect(filtered.every((task) => task.priority === "high")).toBe(true);
    expect(filtered.length).toBe(2);
  });

  it("sorts by attention priority then recency", () => {
    const tasks = workspaceTasks();
    const sorted = sortWorkspaceTasks(
      filterWorkspaceTasks(tasks, {
        search: "",
        status: "upcoming",
        priority: "all",
      }),
      "attention",
    );
    expect(sorted.map((task) => task.id)).toEqual(["pending-1", "pending-2"]);
  });

  it("sorts by recent updates", () => {
    const tasks = workspaceTasks();
    const sorted = sortWorkspaceTasks(tasks, "recent");
    expect(sorted[0].id).toBe("progress-1");
  });

  it("groups tasks into execution sections with blocked first", () => {
    const tasks = workspaceTasks();
    const groups = groupWorkspaceTasks(tasks);
    expect(groups.map((group) => group.key)).toEqual([
      "needs_attention",
      "in_progress",
      "upcoming",
      "completed",
    ]);
    expect(groups[0].tasks[0].id).toBe("blocked-1");
  });

  it("computes section counts", () => {
    const counts = computeTaskCounts(workspaceTasks());
    expect(counts).toEqual({
      needs_attention: 1,
      in_progress: 1,
      upcoming: 2,
      completed: 1,
    });
  });

  it("detects active filters and clears state shape", () => {
    const filters: WorkspaceFilters = {
      search: "customer",
      status: "all",
      priority: "all",
      sort: "attention",
    };
    expect(hasActiveFilters(filters)).toBe(true);
    expect(hasActiveFilters({ ...filters, search: "" })).toBe(false);
  });

  it("handles optional fields safely", () => {
    const task = enrichTasksWithObjectives(
      [
        makeTask({
          description: null,
          blocked_reason: null,
          started_at: null,
          completed_at: null,
          objective_id: "missing-obj",
        }),
      ],
      OBJECTIVES,
    )[0];
    expect(task.objectiveTitle).toBeNull();
    expect(truncateDescription(task.description)).toBeNull();
    expect(taskPriorityLabel(task.priority)).toBe("Medium");
  });

  it("builds task detail links", () => {
    expect(taskDetailPath("task-abc")).toBe("/dashboard/tasks/task-abc");
  });

  it("derives priority options from loaded tasks", () => {
    expect(derivePriorityOptions(workspaceTasks())).toEqual(["high", "medium", "low"]);
  });

  it("maps API errors for workspace load failures", () => {
    expect(mapTaskApiError(new ApiError(403, "Forbidden"), "fallback")).toBe(
      "You don't have access to this task.",
    );
    expect(mapTaskApiError(new ApiError(422, "Invalid"), "fallback")).toBe("Invalid");
  });
});
