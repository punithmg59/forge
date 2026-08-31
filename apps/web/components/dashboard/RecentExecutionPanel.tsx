import Link from "next/link";

import { SectionCard } from "@/components/dashboard/SectionCard";
import type { FounderTask } from "@/lib/api";
import { FOUNDER_DASHBOARD_EMPTY, truncateText } from "@/lib/founder-dashboard";
import { taskDetailPath } from "@/lib/task-workspace";
import { formatTaskTimestamp } from "@/lib/tasks";

type RecentExecutionPanelProps = {
  tasks: FounderTask[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

export function RecentExecutionPanel({
  tasks,
  loading,
  error,
  onRetry,
}: RecentExecutionPanelProps) {
  return (
    <SectionCard
      title="Recently completed"
      subtitle="Historical execution results from founder tasks."
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={tasks.length === 0 ? <p>{FOUNDER_DASHBOARD_EMPTY.recentExecution}</p> : undefined}
    >
      {tasks.length > 0 ? (
        <ul className="space-y-4">
          {tasks.map((task) => (
            <li key={task.id}>
              <article className="rounded-xl border border-white/8 bg-white/3 p-4">
                <h3 className="font-medium text-white">{task.title}</h3>
                <p className="mt-1 text-xs text-white/45">
                  Completed {formatTaskTimestamp(task.completed_at)}
                </p>
                {task.result_summary ? (
                  <p className="mt-3 text-sm text-white/70 whitespace-pre-wrap">
                    {truncateText(task.result_summary, 160)}
                  </p>
                ) : null}
                {task.result_metrics && Object.keys(task.result_metrics).length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/55">
                    {Object.entries(task.result_metrics).map(([key, value]) => (
                      <li key={key}>{key}: {value}</li>
                    ))}
                  </ul>
                ) : null}
                <Link
                  href={taskDetailPath(task.id)}
                  className="mt-3 inline-block text-sm text-violet-200/80 transition hover:text-violet-100"
                >
                  View task →
                </Link>
              </article>
            </li>
          ))}
        </ul>
      ) : null}
    </SectionCard>
  );
}
