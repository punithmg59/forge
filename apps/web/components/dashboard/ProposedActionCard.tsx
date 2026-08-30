import type { HeadAgentRecommendation } from "@/lib/api";
import { formatActionType } from "@/lib/operating";
import type { RecommendationApprovalStatus } from "@/lib/specialist-intelligence";

type ProposedActionCardProps = {
  recommendation: HeadAgentRecommendation;
  approvalStatus: RecommendationApprovalStatus;
  approvalRequestLoading: boolean;
  onRequestApproval: () => void;
};

export function ProposedActionCard({
  recommendation,
  approvalStatus,
  approvalRequestLoading,
  onRequestApproval,
}: ProposedActionCardProps) {
  const action = recommendation.proposed_action;
  if (action.type === "none") {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-amber-400/20 bg-amber-500/5 p-4"
      aria-labelledby="forge-proposed-action-heading"
    >
      <h3
        id="forge-proposed-action-heading"
        className="text-xs font-medium uppercase tracking-wide text-amber-200/70"
      >
        Proposed action
      </h3>
      <p className="mt-1 text-sm font-medium text-white">{action.title || "Untitled action"}</p>
      {action.description ? (
        <p className="mt-1 text-sm text-white/65">{action.description}</p>
      ) : null}
      <p className="mt-2 text-xs text-white/50">
        Type: {formatActionType(action.type)}. This is a proposal — it will not change company
        state until approved.
      </p>
      {approvalStatus === "pending" ? (
        <p className="mt-3 text-sm text-amber-100/90" role="status">Pending approval</p>
      ) : null}
      {approvalStatus === "approved" ? (
        <p className="mt-3 text-sm text-emerald-200/90" role="status">Approved</p>
      ) : null}
      {approvalStatus === "rejected" ? (
        <p className="mt-3 text-sm text-white/60" role="status">Rejected</p>
      ) : null}
      {approvalStatus === "can_request" ? (
        <button
          className="forge-button mt-3 w-auto px-5"
          type="button"
          disabled={approvalRequestLoading}
          onClick={onRequestApproval}
        >
          {approvalRequestLoading ? "Submitting..." : "Request approval"}
        </button>
      ) : null}
    </div>
  );
}
