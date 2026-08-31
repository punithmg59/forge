"use client";

import Link from "next/link";

import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import {
  describeTaskTimestamp,
  taskDetailPath,
  taskPriorityLabel,
  truncateDescription,
  type WorkspaceTask,
} from "@/lib/task-workspace";

type TaskListItemProps = {
  task: WorkspaceTask;
  compact?: boolean;
};

export function TaskListItem({ task, compact = false }: TaskListItemProps) {
  const description = truncateDescription(task.description, compact ? 80 : 120);
  const timestamp = describeTaskTimestamp(task);

  return (
    <Link
      href={taskDetailPath(task.id)}
      className="block rounded-xl border border-white/8 bg-white/3 p-4 transition hover:border-white/14 hover:bg-white/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-400/60"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <TaskStatusBadge status={task.status} />
            <span className="text-xs font-medium uppercase tracking-wide text-white/45">
              Priority: {taskPriorityLabel(task.priority)}
            </span>
          </div>
          <h3 className="font-medium text-white">{task.title}</h3>
          {task.objectiveTitle ? (
            <p className="text-sm text-white/55">Objective: {task.objectiveTitle}</p>
          ) : null}
          {description && !compact ? (
            <p className="text-sm text-white/60">{description}</p>
          ) : null}
          {task.status === "blocked" && task.blocked_reason ? (
            <p className="text-sm text-red-200/80">
              Blocked: {task.blocked_reason}
            </p>
          ) : null}
          {timestamp ? (
            <p className="text-xs text-white/40">{timestamp}</p>
          ) : null}
        </div>
        <span className="text-sm text-violet-200/80 shrink-0">Open task →</span>
      </div>
    </Link>
  );
}
