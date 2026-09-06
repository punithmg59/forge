import type { ExecutionReview } from "@/lib/api";
import { formatTimestamp } from "@/lib/operating";

type ExecutionReviewCardProps = {
  review: ExecutionReview;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onToggleDetails?: () => void;
  showDetails?: boolean;
};

export function ExecutionReviewCard({
  review,
  busy,
  onApprove,
  onReject,
  onToggleDetails,
  showDetails = false,
}: ExecutionReviewCardProps) {
  const riskColor = getRiskColor(review.risk_level);
  const stepCount = review.steps.length;

  return (
    <article className="rounded-xl border border-white/8 bg-white/3 p-4">
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-white/45">
              Execution Plan Review
            </p>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${riskColor}`}
            >
              Risk {review.risk_level.toUpperCase()}
            </span>
          </div>
          <h3 className="font-medium text-white">{review.goal}</h3>
          <p className="text-sm text-white/65">{review.rationale}</p>
        </div>

        {/* Summary */}
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
          <span>{stepCount} step{stepCount !== 1 ? "s" : ""}</span>
          <span>•</span>
          <span>{review.tool_summary.length} tool{review.tool_summary.length !== 1 ? "s" : ""}</span>
          <span>•</span>
          <span>Requested {formatTimestamp(review.requested_at)}</span>
          {review.expires_at && (
            <>
              <span>•</span>
              <span>Expires {formatTimestamp(review.expires_at)}</span>
            </>
          )}
        </div>

        {/* Tools Summary */}
        <div className="space-y-1">
          <p className="text-xs font-medium text-white/40">Tools</p>
          <div className="flex flex-wrap gap-2">
            {review.tool_summary.map((tool) => (
              <span
                key={tool}
                className="text-xs font-mono px-2 py-1 rounded bg-white/5 text-white/70 border border-white/10"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>

        {/* Expandable Details */}
        {showDetails && (
          <div className="space-y-3 pt-3 border-t border-white/8">
            <p className="text-xs font-medium text-white/40">Execution Steps</p>
            {review.steps.map((step) => (
              <div
                key={step.step_id}
                className="rounded-lg border border-white/8 bg-white/2 p-3 space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1 min-w-0">
                    <p className="text-sm font-medium text-white">
                      Step {step.sequence}: {step.purpose}
                    </p>
                    <p className="text-xs text-white/50 font-mono">
                      {step.tool_name}:{step.tool_version}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${getStepCategoryColor(
                      step.step_category
                    )}`}
                  >
                    {formatStepCategory(step.step_category)}
                  </span>
                </div>

                {step.input && Object.keys(step.input).length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-white/40">Input</p>
                    <pre className="text-xs text-white/60 bg-black/20 p-2 rounded overflow-x-auto">
                      {JSON.stringify(step.input, null, 2)}
                    </pre>
                  </div>
                )}

                {step.expected_output && (
                  <div className="space-y-1">
                    <p className="text-xs text-white/40">Expected Output</p>
                    <p className="text-sm text-white/60">{step.expected_output}</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/50">
                  <span>Risk: {step.risk_level.toUpperCase()}</span>
                  {step.timeout_ms && (
                    <>
                      <span>•</span>
                      <span>Timeout: {step.timeout_ms}ms</span>
                    </>
                  )}
                  {step.approval_required && (
                    <>
                      <span>•</span>
                      <span>Approval Required</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2">
          {onToggleDetails && (
            <button
              className="rounded-lg border border-white/12 bg-white/5 px-4 py-2 text-sm font-medium text-white/75 hover:bg-white/10 transition-colors"
              type="button"
              disabled={busy}
              onClick={onToggleDetails}
            >
              {showDetails ? "Hide Details" : "Review Details"}
            </button>
          )}
          <button
            className="rounded-lg border border-white/12 bg-white/5 px-4 py-2 text-sm font-medium text-white/75 hover:bg-white/10 transition-colors"
            type="button"
            disabled={busy}
            aria-label={`Reject execution plan: ${review.goal}`}
            onClick={onReject}
          >
            Reject
          </button>
          <button
            className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200 hover:bg-emerald-500/20 transition-colors"
            type="button"
            disabled={busy}
            aria-label={`Approve and execute: ${review.goal}`}
            onClick={onApprove}
          >
            {busy ? "Approving..." : "Approve & Execute"}
          </button>
        </div>
      </div>
    </article>
  );
}

function getRiskColor(risk: string): string {
  switch (risk.toLowerCase()) {
    case "low":
      return "bg-emerald-500/20 text-emerald-300";
    case "medium":
      return "bg-amber-500/20 text-amber-300";
    case "high":
      return "bg-orange-500/20 text-orange-300";
    case "critical":
      return "bg-red-500/20 text-red-300";
    default:
      return "bg-white/10 text-white/60";
  }
}

function getStepCategoryColor(category: string): string {
  switch (category) {
    case "read_only_low_risk":
      return "bg-emerald-500/20 text-emerald-300";
    case "read_only_high_cost":
      return "bg-amber-500/20 text-amber-300";
    case "write_low_risk":
      return "bg-orange-500/20 text-orange-300";
    case "write_high_risk":
      return "bg-red-500/20 text-red-300";
    case "external_side_effect":
      return "bg-purple-500/20 text-purple-300";
    case "financial_action":
      return "bg-red-500/20 text-red-300";
    case "communication_to_customer":
      return "bg-blue-500/20 text-blue-300";
    default:
      return "bg-white/10 text-white/60";
  }
}

function formatStepCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
