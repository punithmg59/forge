import Link from "next/link";

import { SectionCard } from "@/components/dashboard/SectionCard";
import { TaskListItem } from "@/components/tasks/TaskListItem";
import { FOUNDER_DASHBOARD_EMPTY } from "@/lib/founder-dashboard";
import type { WorkspaceTask } from "@/lib/task-workspace";

type FocusTasksPanelProps = {
  tasks: WorkspaceTask[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

export function FocusTasksPanel({ tasks, loading, error, onRetry }: FocusTasksPanelProps) {
  return (
    <SectionCard
      title="What you should focus on"
      subtitle="In-progress and high-priority upcoming tasks."
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={tasks.length === 0 ? <p>{FOUNDER_DASHBOARD_EMPTY.focusTasks}</p> : undefined}
    >
      {tasks.length > 0 ? (
        <div className="space-y-4">
          <ol className="space-y-3">
            {tasks.map((task, index) => (
              <li key={task.id} className="flex gap-3">
                <span className="mt-4 text-sm font-medium text-white/35">{index + 1}.</span>
                <div className="min-w-0 flex-1">
                  <TaskListItem task={task} compact />
                </div>
              </li>
            ))}
          </ol>
          <Link
            href="/dashboard/tasks"
            className="text-sm text-violet-200/80 transition hover:text-violet-100"
          >
            View all tasks →
          </Link>
        </div>
      ) : null}
    </SectionCard>
  );
}
