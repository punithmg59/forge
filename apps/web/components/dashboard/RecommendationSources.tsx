import type { RecommendationSource } from "@/lib/api";
import { formatSourceLabel, groupSourceLabels } from "@/lib/specialist-intelligence";

type RecommendationSourcesProps = {
  sources: RecommendationSource[];
  title?: string;
};

export function RecommendationSources({
  sources,
  title = "Grounded in Company Brain",
}: RecommendationSourcesProps) {
  if (sources.length === 0) {
    return (
      <p className="text-sm text-white/50">
        No grounded Company Brain sources were cited for this proposal.
      </p>
    );
  }

  const groups = groupSourceLabels(sources);

  return (
    <div className="space-y-2">
      <p className="forge-label">{title}</p>
      <p className="text-xs text-white/45">
        Company Brain sources — not AI-generated analysis.
      </p>
      {groups.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {groups.map((label) => (
            <li
              key={label}
              className="rounded-full border border-white/12 bg-white/5 px-2.5 py-1 text-xs text-white/70"
            >
              {label}
            </li>
          ))}
        </ul>
      ) : null}
      <details className="text-xs text-white/55">
        <summary className="cursor-pointer text-white/60 hover:text-white/80">
          View source details
        </summary>
        <ul className="mt-2 space-y-1 pl-1">
          {sources.map((source, index) => (
            <li key={`${source.entity_id ?? "source"}-${index}`}>
              {formatSourceLabel(source)}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
