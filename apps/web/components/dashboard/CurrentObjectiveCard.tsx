import { SectionCard } from "@/components/dashboard/SectionCard";
import type { Objective } from "@/lib/api";
import { FOUNDER_DASHBOARD_EMPTY } from "@/lib/founder-dashboard";
import { formatObjectiveMetric } from "@/lib/operating";

type CurrentObjectiveCardProps = {
  objective: Objective | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

export function CurrentObjectiveCard({
  objective,
  loading,
  error,
  onRetry,
}: CurrentObjectiveCardProps) {
  const metric = objective ? formatObjectiveMetric(objective) : null;

  return (
    <SectionCard
      title="Current objective"
      subtitle="What the company is trying to achieve right now."
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={
        !objective ? (
          <div>
            <p>{FOUNDER_DASHBOARD_EMPTY.objective}</p>
            <p className="mt-2 text-white/40">{FOUNDER_DASHBOARD_EMPTY.objectiveHint}</p>
          </div>
        ) : undefined
      }
    >
      {objective ? (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-white">{objective.title}</h2>
          {objective.description ? (
            <p className="text-sm leading-relaxed text-white/65">{objective.description}</p>
          ) : null}
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
            <span>Status: {objective.status}</span>
            <span>Priority: {objective.priority}</span>
            {metric ? <span>Target: {metric}</span> : null}
            {objective.deadline ? <span>Deadline: {objective.deadline}</span> : null}
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
