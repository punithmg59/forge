import Link from "next/link";

import { ApprovalCard } from "@/components/dashboard/ApprovalCard";
import { SectionCard } from "@/components/dashboard/SectionCard";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import type { Approval } from "@/lib/api";
import {
  FOUNDER_DASHBOARD_EMPTY,
  summarizeAttentionCounts,
  type AttentionCounts,
} from "@/lib/founder-dashboard";
import { taskDetailPath } from "@/lib/task-workspace";
import type { WorkspaceTask } from "@/lib/task-workspace";
import { taskPriorityLabel } from "@/lib/task-workspace";

type AttentionPanelProps = {
  pendingApprovals: Approval[];
  blockedTasks: WorkspaceTask[];
  objectiveTitle: string | null;
  loading: boolean;
  error: string | null;
  approvalActionId: string | null;
  onRetry: () => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
};

export function AttentionPanel({
  pendingApprovals,
  blockedTasks,
  objectiveTitle,
  loading,
  error,
  approvalActionId,
  onRetry,
  onApprove,
  onReject,
}: AttentionPanelProps) {
  const counts = summarizeAttentionCounts(pendingApprovals, blockedTasks);
  const isEmpty = counts.total === 0;

  return (
    <SectionCard
      title="Needs your attention"
      subtitle="Pending approvals and blocked founder tasks."
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={isEmpty ? <p>{FOUNDER_DASHBOARD_EMPTY.approvals}</p> : undefined}
    >
      {!isEmpty ? (
        <div className="space-y-4">
          <AttentionCountsRow counts={counts} />
          {pendingApprovals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              objectiveTitle={objectiveTitle}
              busy={approvalActionId === approval.id}
              onApprove={() => onApprove(approval.id)}
              onReject={() => onReject(approval.id)}
            />
          ))}
          {blockedTasks.map((task) => (
            <BlockedTaskCard key={task.id} task={task} />
          ))}
        </div>
      ) : null}
    </SectionCard>
  );
}

function AttentionCountsRow({ counts }: { counts: AttentionCounts }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-white/55">
      {counts.pendingApprovals > 0 ? (
        <span>{counts.pendingApprovals} pending approval{counts.pendingApprovals === 1 ? "" : "s"}</span>
      ) : null}
      {counts.blockedTasks > 0 ? (
        <span>{counts.blockedTasks} blocked task{counts.blockedTasks === 1 ? "" : "s"}</span>
      ) : null}
    </div>
  );
}

function BlockedTaskCard({ task }: { task: WorkspaceTask }) {
  return (
    <Link
      href={taskDetailPath(task.id)}
      className="block rounded-xl border border-red-400/20 bg-red-500/5 p-4 transition hover:border-red-400/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400/50"
    >
      <div className="flex flex-wrap items-center gap-2">
        <TaskStatusBadge status={task.status} />
        <span className="text-xs text-white/45">Priority: {taskPriorityLabel(task.priority)}</span>
      </div>
      <h3 className="mt-2 font-medium text-white">{task.title}</h3>
      {task.blocked_reason ? (
        <p className="mt-2 text-sm text-red-200/80">Blocked: {task.blocked_reason}</p>
      ) : null}
      <span className="mt-3 inline-block text-sm text-violet-200/80">Open task →</span>
    </Link>
  );
}
