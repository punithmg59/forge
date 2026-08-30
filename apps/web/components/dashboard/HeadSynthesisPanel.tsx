import type { HeadAgentRecommendation } from "@/lib/api";
import { RecommendationConfidence } from "@/components/dashboard/RecommendationConfidence";
import { RecommendationSources } from "@/components/dashboard/RecommendationSources";

type HeadSynthesisPanelProps = {
  recommendation: HeadAgentRecommendation;
};

export function HeadSynthesisPanel({ recommendation }: HeadSynthesisPanelProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3
          id="forge-synthesis-heading"
          className="text-xs font-medium uppercase tracking-wide text-violet-200/70"
        >
          Forge&apos;s recommendation
        </h3>
        <p className="mt-1 text-xs text-white/40">Final synthesis — a proposal, not company truth.</p>
      </div>
      <div className="rounded-xl border border-violet-400/20 bg-violet-500/5 p-4">
        <h3 className="text-lg font-semibold text-white">{recommendation.title}</h3>
        <p className="mt-2 text-sm text-white/75">{recommendation.recommendation}</p>
        <p className="mt-3 text-sm text-white/55">
          <span className="text-white/70">Rationale:</span> {recommendation.rationale}
        </p>
      </div>
      <RecommendationConfidence confidence={recommendation.confidence} />
      <RecommendationSources sources={recommendation.sources} />
    </div>
  );
}
