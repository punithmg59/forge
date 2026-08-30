import type { SpecialistAnalysisSummary } from "@/lib/api";
import { RecommendationConfidence } from "@/components/dashboard/RecommendationConfidence";
import { RecommendationSources } from "@/components/dashboard/RecommendationSources";

type SpecialistAnalysisPanelProps = {
  analyses: SpecialistAnalysisSummary[];
  orchestrationMode: string | null | undefined;
};

export function SpecialistAnalysisPanel({
  analyses,
  orchestrationMode,
}: SpecialistAnalysisPanelProps) {
  if (analyses.length === 0) {
    if (orchestrationMode === "head_only") {
      return null;
    }
    return (
      <p className="text-sm text-white/50">
        No specialist analysis was used for this recommendation.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3
          id="forge-specialist-heading"
          className="text-xs font-medium uppercase tracking-wide text-white/45"
        >
          Specialist analysis
        </h3>
        <p className="mt-1 text-xs text-white/40">
          Domain expert input — analysis, not Company Brain truth.
        </p>
      </div>
      {analyses.map((analysis) => (
        <article
          key={`${analysis.agent_type}-${analysis.agent_task_id ?? analysis.title}`}
          className="rounded-lg border border-white/10 bg-white/3 p-4"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-sky-200/80">
            {analysis.display_name}
          </p>
          <h4 className="mt-1 text-sm font-medium text-white">{analysis.title}</h4>
          <p className="mt-2 text-sm text-white/75">{analysis.recommendation}</p>
          <p className="mt-2 text-xs text-white/55">
            <span className="text-white/65">Rationale:</span> {analysis.rationale}
          </p>
          <div className="mt-3">
            <RecommendationConfidence confidence={analysis.confidence} />
          </div>
          {analysis.sources.length > 0 ? (
            <div className="mt-3">
              <RecommendationSources
                sources={analysis.sources}
                title="Specialist grounding references"
              />
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
