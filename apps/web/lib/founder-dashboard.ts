import type { Approval, CompanyLearning, FounderTask } from "./api";
import { TASK_STATUSES } from "./tasks";
import type { WorkspaceTask } from "./task-workspace";

const PRIORITY_WEIGHT: Record<string, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export const FOUNDER_DASHBOARD_EMPTY = {
  objective: "No active objective.",
  objectiveHint: "Set a company objective to give Forge a direction.",
  approvals: "No approvals need your attention.",
  tasks: "No founder tasks yet.",
  focusTasks: "No tasks in focus right now.",
  brain: "No active Company Brain learnings yet.",
  recentExecution: "No completed tasks yet.",
  recommendation: "No recommendation yet.",
} as const;

export type AttentionCounts = {
  pendingApprovals: number;
  blockedTasks: number;
  total: number;
};

export type OperatingLoopStage = {
  key: string;
  label: string;
  active: boolean;
};

export function priorityWeight(priority: string): number {
  return PRIORITY_WEIGHT[priority] ?? 0;
}

export function selectBlockedTasks(tasks: WorkspaceTask[]): WorkspaceTask[] {
  return tasks.filter((task) => task.status === TASK_STATUSES.blocked);
}

export function selectActiveLearnings(learnings: CompanyLearning[]): CompanyLearning[] {
  return learnings.filter((learning) => learning.status === "active");
}

export function selectFocusTasks(tasks: WorkspaceTask[], limit = 5): WorkspaceTask[] {
  const blockedIds = new Set(selectBlockedTasks(tasks).map((task) => task.id));

  const inProgress = tasks
    .filter((task) => task.status === TASK_STATUSES.in_progress)
    .sort((a, b) => compareByPriorityThenRecent(b, a));

  const pendingHigh = tasks
    .filter(
      (task) =>
        task.status === TASK_STATUSES.pending &&
        task.priority === "high" &&
        !blockedIds.has(task.id),
    )
    .sort((a, b) => compareByPriorityThenRecent(b, a));

  const pendingOther = tasks
    .filter(
      (task) =>
        task.status === TASK_STATUSES.pending &&
        task.priority !== "high" &&
        !blockedIds.has(task.id),
    )
    .sort((a, b) => compareByPriorityThenRecent(b, a));

  return [...inProgress, ...pendingHigh, ...pendingOther].slice(0, limit);
}

export function selectRecentCompletedTasks(
  tasks: FounderTask[],
  limit = 5,
): FounderTask[] {
  return tasks
    .filter((task) => task.status === TASK_STATUSES.completed)
    .sort((a, b) =>
      compareTimestamp(b.completed_at ?? b.updated_at, a.completed_at ?? a.updated_at),
    )
    .slice(0, limit);
}

export function summarizeAttentionCounts(
  pendingApprovals: Approval[],
  blockedTasks: WorkspaceTask[],
): AttentionCounts {
  return {
    pendingApprovals: pendingApprovals.length,
    blockedTasks: blockedTasks.length,
    total: pendingApprovals.length + blockedTasks.length,
  };
}

export function summarizeTaskCounts(tasks: WorkspaceTask[]) {
  return {
    blocked: selectBlockedTasks(tasks).length,
    inProgress: tasks.filter((task) => task.status === TASK_STATUSES.in_progress).length,
    pending: tasks.filter((task) => task.status === TASK_STATUSES.pending).length,
    completed: tasks.filter((task) => task.status === TASK_STATUSES.completed).length,
  };
}

export function buildOperatingLoopState(input: {
  hasObjective: boolean;
  hasPendingApprovals: boolean;
  hasTasks: boolean;
  hasCompletedTasks: boolean;
  hasLearnings: boolean;
  hasActiveLearnings: boolean;
}): OperatingLoopStage[] {
  return [
    { key: "objective", label: "Objective", active: input.hasObjective },
    { key: "recommendation", label: "Recommendation", active: input.hasPendingApprovals },
    { key: "approval", label: "Approval", active: input.hasPendingApprovals },
    { key: "task", label: "Task", active: input.hasTasks },
    { key: "evidence", label: "Evidence", active: input.hasCompletedTasks },
    { key: "learning", label: "Learning", active: input.hasLearnings },
    { key: "brain", label: "Company Brain", active: input.hasActiveLearnings },
  ];
}

export function truncateText(text: string | null | undefined, maxLength = 120): string | null {
  if (!text) {
    return null;
  }
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 1)}…`;
}

function compareByPriorityThenRecent(a: WorkspaceTask, b: WorkspaceTask): number {
  const priorityDiff = priorityWeight(b.priority) - priorityWeight(a.priority);
  if (priorityDiff !== 0) {
    return priorityDiff;
  }
  return compareTimestamp(b.updated_at, a.updated_at);
}

function compareTimestamp(a: string, b: string): number {
  const aTime = Date.parse(a);
  const bTime = Date.parse(b);
  if (Number.isNaN(aTime) || Number.isNaN(bTime)) {
    return 0;
  }
  return aTime - bTime;
}
