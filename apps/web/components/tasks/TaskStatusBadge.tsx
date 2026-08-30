import { taskStatusLabel } from "@/lib/tasks";

const STATUS_CLASS: Record<string, string> = {
  pending: "task-status-pending",
  in_progress: "task-status-in_progress",
  blocked: "task-status-blocked",
  completed: "task-status-completed",
};

export function TaskStatusBadge({ status }: { status: string }) {
  const className = STATUS_CLASS[status] ?? "task-status-default";
  return (
    <span className={`task-status-badge ${className}`} aria-label={`Status: ${taskStatusLabel(status)}`}>
      {taskStatusLabel(status).toUpperCase()}
    </span>
  );
}
