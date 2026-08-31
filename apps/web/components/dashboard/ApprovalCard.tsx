import type { Approval } from "@/lib/api";
import { formatActionType, formatTimestamp } from "@/lib/operating";

type ApprovalCardProps = {
  approval: Approval;
  objectiveTitle: string | null;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
};

export function ApprovalCard({
  approval,
  objectiveTitle,
  busy,
  onApprove,
  onReject,
}: ApprovalCardProps) {
  const title =
    approval.recommendation?.title ??
    approval.learning_proposal?.statement ??
    approval.description;

  return (
    <article className="rounded-xl border border-white/8 bg-white/3 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-white/45">
            Pending approval
          </p>
          <h3 className="font-medium text-white">{title}</h3>
          {approval.recommendation ? (
            <p className="text-sm text-white/65">{approval.recommendation.recommendation}</p>
          ) : null}
          {approval.learning_proposal ? (
            <p className="text-sm text-white/65">{approval.learning_proposal.statement}</p>
          ) : null}
          <p className="text-sm text-white/55">
            {formatActionType(approval.action_type)} · Risk {approval.risk_level}
          </p>
          <p className="text-xs text-white/40">
            Requested {formatTimestamp(approval.requested_at)}
          </p>
          {objectiveTitle ? (
            <p className="text-sm text-white/50">Objective: {objectiveTitle}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200"
            type="button"
            disabled={busy}
            aria-label={`Approve ${title}`}
            onClick={onApprove}
          >
            {busy ? "Working..." : "Approve"}
          </button>
          <button
            className="rounded-lg border border-white/12 bg-white/5 px-4 py-2 text-sm font-medium text-white/75"
            type="button"
            disabled={busy}
            aria-label={`Reject ${title}`}
            onClick={onReject}
          >
            Reject
          </button>
        </div>
      </div>
    </article>
  );
}
