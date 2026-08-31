import type { ObjectiveTaskDetail } from "@/lib/api";
import {
  EXECUTION_CONTEXT_MESSAGES,
  approvalContextLabel,
  recommendationPrimaryText,
  recommendationSecondaryText,
} from "@/lib/execution-context";
import { formatTaskTimestamp } from "@/lib/tasks";

export function TaskWhySection({ task }: { task: ObjectiveTaskDetail }) {
  return (
    <section className="glass-card p-6" aria-labelledby="why-this-task-heading">
      <p className="forge-label">Why this task exists</p>
      <h2 id="why-this-task-heading" className="text-base font-medium text-white">
        Execution context
      </h2>

      <dl className="mt-4 space-y-5 text-sm">
        <ContextItem
          label="Objective"
          value={task.objective?.title ?? EXECUTION_CONTEXT_MESSAGES.objectiveUnavailable}
          muted={task.objective === null}
        />

        <div>
          <dt className="text-white/45">Created from Forge recommendation</dt>
          {task.recommendation ? (
            <dd className="mt-1 space-y-2 text-white/80">
              <p className="whitespace-pre-wrap">{recommendationPrimaryText(task.recommendation)}</p>
              {recommendationSecondaryText(task.recommendation) ? (
                <p className="text-white/60 whitespace-pre-wrap">
                  {recommendationSecondaryText(task.recommendation)}
                </p>
              ) : null}
              {task.recommendation_question ? (
                <p className="text-xs text-white/45">
                  Forge question: {task.recommendation_question}
                </p>
              ) : null}
            </dd>
          ) : (
            <dd className="mt-1 text-white/50">
              {EXECUTION_CONTEXT_MESSAGES.recommendationUnavailable}
            </dd>
          )}
        </div>

        <div>
          <dt className="text-white/45">Founder approval</dt>
          {task.approval_context ? (
            <dd className="mt-1 space-y-1 text-white/80">
              <p>{approvalContextLabel(task.approval_context)}</p>
              <p className="text-white/60">{task.approval_context.description}</p>
              <p className="text-xs text-white/45">
                Requested {formatTaskTimestamp(task.approval_context.requested_at)}
              </p>
            </dd>
          ) : (
            <dd className="mt-1 text-white/50">
              {EXECUTION_CONTEXT_MESSAGES.approvalUnavailable}
            </dd>
          )}
        </div>
      </dl>
    </section>
  );
}

function ContextItem({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div>
      <dt className="text-white/45">{label}</dt>
      <dd className={muted ? "mt-1 text-white/50" : "mt-1 text-white/80"}>{value}</dd>
    </div>
  );
}
