import type { FounderTask, Objective } from "./api";
import {
  TASK_STATUSES,
  formatTaskTimestamp,
  taskStatusLabel,
} from "./tasks";
import { objectiveTitleById } from "./operating";

export type WorkspaceTask = FounderTask & {
  objectiveTitle: string | null;
};

export type StatusFilterValue =
  | "all"
  | "needs_attention"
  | "in_progress"
  | "upcoming"
  | "completed";

export type SortOption = "attention" | "recent";

export type TaskGroupKey =
  | "needs_attention"
  | "in_progress"
  | "upcoming"
  | "completed";

export const STATUS_FILTER_OPTIONS: Array<{ value: StatusFilterValue; label: string }> = [
  { value: "all", label: "All" },
  { value: "needs_attention", label: "Needs attention" },
  { value: "in_progress", label: "In progress" },
  { value: "upcoming", label: "Upcoming" },
  { value: "completed", label: "Completed" },
];

export const SORT_OPTIONS: Array<{ value: SortOption; label: string }> = [
  { value: "attention", label: "Priority" },
  { value: "recent", label: "Recent" },
];

const GROUP_ORDER: TaskGroupKey[] = [
  "needs_attention",
  "in_progress",
  "upcoming",
  "completed",
];

const GROUP_LABELS: Record<TaskGroupKey, string> = {
  needs_attention: "Needs attention",
  in_progress: "In progress",
  upcoming: "Upcoming",
  completed: "Completed",
};

const PRIORITY_WEIGHT: Record<string, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export type WorkspaceFilters = {
  search: string;
  status: StatusFilterValue;
  priority: string;
  sort: SortOption;
};

export type WorkspaceCounts = {
  needs_attention: number;
  in_progress: number;
  upcoming: number;
  completed: number;
};

export function enrichTasksWithObjectives(
  tasks: FounderTask[],
  objectives: Objective[],
): WorkspaceTask[] {
  return tasks.map((task) => ({
    ...task,
    objectiveTitle: objectiveTitleById(objectives, task.objective_id),
  }));
}

export function computeTaskCounts(tasks: WorkspaceTask[]): WorkspaceCounts {
  return {
    needs_attention: tasks.filter((task) => task.status === TASK_STATUSES.blocked).length,
    in_progress: tasks.filter((task) => task.status === TASK_STATUSES.in_progress).length,
    upcoming: tasks.filter((task) => task.status === TASK_STATUSES.pending).length,
    completed: tasks.filter((task) => task.status === TASK_STATUSES.completed).length,
  };
}

export function derivePriorityOptions(tasks: WorkspaceTask[]): string[] {
  const values = new Set<string>();
  for (const task of tasks) {
    if (task.priority) {
      values.add(task.priority);
    }
  }
  return Array.from(values).sort((a, b) => priorityWeight(b) - priorityWeight(a));
}

export function matchesStatusFilter(task: WorkspaceTask, status: StatusFilterValue): boolean {
  if (status === "all") {
    return true;
  }
  if (status === "needs_attention") {
    return task.status === TASK_STATUSES.blocked;
  }
  if (status === "in_progress") {
    return task.status === TASK_STATUSES.in_progress;
  }
  if (status === "upcoming") {
    return task.status === TASK_STATUSES.pending;
  }
  return task.status === TASK_STATUSES.completed;
}

export function filterWorkspaceTasks(
  tasks: WorkspaceTask[],
  filters: Pick<WorkspaceFilters, "search" | "status" | "priority">,
): WorkspaceTask[] {
  const query = filters.search.trim().toLowerCase();

  return tasks.filter((task) => {
    if (!matchesStatusFilter(task, filters.status)) {
      return false;
    }
    if (filters.priority !== "all" && task.priority !== filters.priority) {
      return false;
    }
    if (!query) {
      return true;
    }
    const title = task.title.toLowerCase();
    const description = (task.description ?? "").toLowerCase();
    const objective = (task.objectiveTitle ?? "").toLowerCase();
    return title.includes(query) || description.includes(query) || objective.includes(query);
  });
}

export function sortWorkspaceTasks(tasks: WorkspaceTask[], sort: SortOption): WorkspaceTask[] {
  const sorted = [...tasks];
  if (sort === "recent") {
    sorted.sort((a, b) => compareRecent(b, a));
    return sorted;
  }
  sorted.sort((a, b) => {
    const priorityDiff = priorityWeight(b.priority) - priorityWeight(a.priority);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }
    return compareRecent(b, a);
  });
  return sorted;
}

export function groupWorkspaceTasks(tasks: WorkspaceTask[]): Array<{
  key: TaskGroupKey;
  label: string;
  tasks: WorkspaceTask[];
}> {
  const buckets: Record<TaskGroupKey, WorkspaceTask[]> = {
    needs_attention: [],
    in_progress: [],
    upcoming: [],
    completed: [],
  };

  for (const task of tasks) {
    if (task.status === TASK_STATUSES.blocked) {
      buckets.needs_attention.push(task);
    } else if (task.status === TASK_STATUSES.in_progress) {
      buckets.in_progress.push(task);
    } else if (task.status === TASK_STATUSES.pending) {
      buckets.upcoming.push(task);
    } else if (task.status === TASK_STATUSES.completed) {
      buckets.completed.push(task);
    }
  }

  return GROUP_ORDER
    .map((key) => ({
      key,
      label: GROUP_LABELS[key],
      tasks: buckets[key],
    }))
    .filter((group) => group.tasks.length > 0);
}

export function taskDetailPath(taskId: string): string {
  return `/dashboard/tasks/${taskId}`;
}

export function taskPriorityLabel(priority: string): string {
  if (!priority) {
    return priority;
  }
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

export function describeTaskTimestamp(task: WorkspaceTask): string | null {
  if (task.status === TASK_STATUSES.completed && task.completed_at) {
    return `Completed ${formatTaskTimestamp(task.completed_at)}`;
  }
  if (task.status === TASK_STATUSES.in_progress && task.started_at) {
    return `Started ${formatTaskTimestamp(task.started_at)}`;
  }
  if (task.updated_at) {
    return `Updated ${formatTaskTimestamp(task.updated_at)}`;
  }
  return null;
}

export function truncateDescription(text: string | null, maxLength = 120): string | null {
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

export function hasActiveFilters(filters: WorkspaceFilters): boolean {
  return (
    filters.search.trim() !== "" ||
    filters.status !== "all" ||
    filters.priority !== "all"
  );
}

export function selectPreviewTasks(tasks: WorkspaceTask[], limit = 3): WorkspaceTask[] {
  const blocked = tasks.filter((task) => task.status === TASK_STATUSES.blocked);
  const inProgress = tasks.filter((task) => task.status === TASK_STATUSES.in_progress);
  const pending = sortWorkspaceTasks(
    tasks.filter((task) => task.status === TASK_STATUSES.pending),
    "attention",
  );
  const combined = [...blocked, ...inProgress, ...pending];
  return combined.slice(0, limit);
}

function priorityWeight(priority: string): number {
  return PRIORITY_WEIGHT[priority] ?? 0;
}

function compareRecent(a: WorkspaceTask, b: WorkspaceTask): number {
  const aTime = Date.parse(a.updated_at);
  const bTime = Date.parse(b.updated_at);
  if (Number.isNaN(aTime) || Number.isNaN(bTime)) {
    return 0;
  }
  return aTime - bTime;
}

export function taskStatusLabelForFilter(value: StatusFilterValue): string {
  const option = STATUS_FILTER_OPTIONS.find((item) => item.value === value);
  return option?.label ?? taskStatusLabel(value);
}
