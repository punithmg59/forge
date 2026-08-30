import Link from "next/link";

import { SectionCard } from "@/components/dashboard/SectionCard";
import type { CompanyLearning } from "@/lib/api";
import { FOUNDER_DASHBOARD_EMPTY } from "@/lib/founder-dashboard";

type BrainSummaryPanelProps = {
  activeLearnings: CompanyLearning[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

export function BrainSummaryPanel({
  activeLearnings,
  loading,
  error,
  onRetry,
}: BrainSummaryPanelProps) {
  return (
    <SectionCard
      title="Company Brain"
      subtitle="Approved knowledge currently active in the operating loop."
      loading={loading}
      error={error}
      onRetry={onRetry}
      empty={
        activeLearnings.length === 0 ? <p>{FOUNDER_DASHBOARD_EMPTY.brain}</p> : undefined
      }
    >
      {activeLearnings.length > 0 ? (
        <div className="space-y-4">
          <p className="text-sm text-white/55">
            {activeLearnings.length} active learning{activeLearnings.length === 1 ? "" : "s"}
          </p>
          <ul className="space-y-3">
            {activeLearnings.slice(0, 5).map((learning) => (
              <li
                key={learning.id}
                className="rounded-xl border border-emerald-400/20 bg-emerald-500/5 px-4 py-3 text-sm text-white/80"
              >
                {learning.statement}
              </li>
            ))}
          </ul>
          <Link
            href="#company-brain"
            className="text-sm text-violet-200/80 transition hover:text-violet-100"
          >
            View Company Brain →
          </Link>
        </div>
      ) : null}
    </SectionCard>
  );
}
