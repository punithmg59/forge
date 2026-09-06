import type { ExecutionStatus } from "@/lib/api";

interface ExecutionStatusCardProps {
  execution: ExecutionStatus;
}

const STATUS_LABELS: Record<string, string> = {
  requested: "Requested",
  planned: "Planned",
  waiting_for_approval: "Review Required",
  approved: "Approved",
  running: "Executing",
  succeeded: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  retrying: "Retrying",
};

const STATUS_COLORS: Record<string, string> = {
  requested: "text-blue-400",
  planned: "text-blue-300",
  waiting_for_approval: "text-yellow-400",
  approved: "text-green-400",
  running: "text-violet-400",
  succeeded: "text-green-500",
  failed: "text-red-400",
  cancelled: "text-gray-400",
  retrying: "text-orange-400",
};

const STEP_STATUS_ICONS: Record<string, string> = {
  pending: "○",
  waiting_for_approval: "○",
  approved: "○",
  running: "⟳",
  succeeded: "✓",
  failed: "✕",
  skipped: "—",
  cancelled: "—",
};

export function ExecutionStatusCard({ execution }: ExecutionStatusCardProps) {
  const statusLabel = STATUS_LABELS[execution.status] || execution.status;
  const statusColor = STATUS_COLORS[execution.status] || "text-white";

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-white">Execution Status</h2>
        <span className={`text-sm font-medium ${statusColor}`}>{statusLabel}</span>
      </div>

      {execution.plan && (
        <div className="space-y-3 text-sm">
          <div>
            <p className="text-white/45">Goal</p>
            <p className="mt-1 text-white/80">{execution.plan.goal}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-white/45">Risk Level</p>
              <p className="mt-1 text-white/75 capitalize">{execution.plan.risk_level}</p>
            </div>
            <div>
              <p className="text-white/45">Steps</p>
              <p className="mt-1 text-white/75">{execution.plan.steps.length}</p>
            </div>
          </div>

          {execution.approval_status && (
            <div>
              <p className="text-white/45">Approval Status</p>
              <p className="mt-1 text-white/75 capitalize">{execution.approval_status}</p>
            </div>
          )}

          {execution.failure_reason && (
            <div>
              <p className="text-white/45">Failure Reason</p>
              <p className="mt-1 text-red-300">{execution.failure_reason}</p>
            </div>
          )}

          {execution.cancel_reason && (
            <div>
              <p className="text-white/45">Cancel Reason</p>
              <p className="mt-1 text-white/75">{execution.cancel_reason}</p>
            </div>
          )}

          {execution.step_results.length > 0 && (
            <div className="mt-4">
              <p className="text-white/45 mb-2">Step Results</p>
              <div className="space-y-2">
                {execution.step_results.map((step) => (
                  <div
                    key={step.step_id}
                    className="flex items-center gap-2 text-white/70"
                  >
                    <span className="text-lg">
                      {STEP_STATUS_ICONS[step.status] || "○"}
                    </span>
                    <span className="flex-1">{step.tool_qualified_name}</span>
                    {step.duration_ms && (
                      <span className="text-xs text-white/45">
                        {(step.duration_ms / 1000).toFixed(2)}s
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
