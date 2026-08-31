import type { ObjectiveTaskPriority, ObjectiveTaskStatus } from "./api";

export const TASK_STATUSES = {
  pending: "pending",
  in_progress: "in_progress",
  blocked: "blocked",
  completed: "completed",
} as const;

export type TaskStatus = ObjectiveTaskStatus;

export const TASK_PRIORITIES: ObjectiveTaskPriority[] = ["low", "medium", "high"];

export const MAX_BLOCKED_REASON_LENGTH = 500;
export const MAX_RESULT_SUMMARY_LENGTH = 4000;
export const MAX_RESULT_NOTES_LENGTH = 4000;
export const MAX_TASK_TITLE_LENGTH = 200;
export const MAX_TASK_DESCRIPTION_LENGTH = 4000;

export function taskStatusLabel(status: string): string {
  switch (status) {
    case TASK_STATUSES.pending:
      return "Pending";
    case TASK_STATUSES.in_progress:
      return "In progress";
    case TASK_STATUSES.blocked:
      return "Blocked";
    case TASK_STATUSES.completed:
      return "Completed";
    default:
      return status.replaceAll("_", " ");
  }
}

export function isTerminalTaskStatus(status: string): boolean {
  return status === TASK_STATUSES.completed;
}

export function canStartTask(status: string): boolean {
  return status === TASK_STATUSES.pending;
}

export function canBlockTask(status: string): boolean {
  return status === TASK_STATUSES.in_progress;
}

export function canResumeTask(status: string): boolean {
  return status === TASK_STATUSES.blocked;
}

export function canCompleteTask(status: string): boolean {
  return (
    status === TASK_STATUSES.pending ||
    status === TASK_STATUSES.in_progress ||
    status === TASK_STATUSES.blocked
  );
}

export function formatTaskTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function formatLearningStatus(status: string): string {
  return status.replaceAll("_", " ").toUpperCase();
}

export function learningStatusHint(status: string): string | null {
  switch (status.toLowerCase()) {
    case "proposed":
      return "Proposed — not yet approved as Company Brain truth.";
    case "active":
      return "Active in Company Brain.";
    case "superseded":
      return "Superseded — no longer active Company Brain truth.";
    default:
      return null;
  }
}

export function parseEvidenceContent(content: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(content) as unknown;
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

export type CompletionFormValues = {
  result_summary: string;
  result_metrics: Record<string, number>;
  result_notes: string;
};

export type CompletionFormErrors = Partial<
  Record<"result_summary" | "result_notes" | "metrics", string>
>;

export function validateCompletionForm(values: CompletionFormValues): CompletionFormErrors {
  const errors: CompletionFormErrors = {};
  const summary = values.result_summary.trim();
  if (!summary) {
    errors.result_summary = "Result summary is required.";
  } else if (summary.length > MAX_RESULT_SUMMARY_LENGTH) {
    errors.result_summary = `Result summary must be ${MAX_RESULT_SUMMARY_LENGTH} characters or fewer.`;
  }

  const notes = values.result_notes.trim();
  if (notes.length > MAX_RESULT_NOTES_LENGTH) {
    errors.result_notes = `Result notes must be ${MAX_RESULT_NOTES_LENGTH} characters or fewer.`;
  }

  for (const [key, value] of Object.entries(values.result_metrics)) {
    if (!key.trim()) {
      errors.metrics = "Metric names cannot be empty.";
      break;
    }
    if (!Number.isFinite(value)) {
      errors.metrics = "Metric values must be numbers.";
      break;
    }
  }

  return errors;
}

export function validateBlockedReason(reason: string): string | null {
  const trimmed = reason.trim();
  if (!trimmed) {
    return "Blocked reason is required.";
  }
  if (trimmed.length > MAX_BLOCKED_REASON_LENGTH) {
    return `Blocked reason must be ${MAX_BLOCKED_REASON_LENGTH} characters or fewer.`;
  }
  return null;
}

export function mapTaskApiError(error: unknown, fallback: string): string {
  if (error instanceof Error && "status" in error) {
    const apiError = error as { status: number; message: string };
    if (apiError.status === 404) {
      return "Task not found.";
    }
    if (apiError.status === 403) {
      return "You don't have access to this task.";
    }
    if (apiError.status === 401) {
      return "Please sign in to view this task.";
    }
    if (apiError.message) {
      return apiError.message;
    }
  }
  if (error instanceof Error && error.message === "Failed to fetch") {
    return "Unable to load this task. Please try again.";
  }
  return fallback;
}
