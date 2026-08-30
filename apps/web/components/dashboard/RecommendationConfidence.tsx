import type { HeadAgentRecommendation } from "@/lib/api";
import {
  confidenceExplanation,
  confidenceLabel,
} from "@/lib/specialist-intelligence";

type RecommendationConfidenceProps = {
  confidence: HeadAgentRecommendation["confidence"];
};

export function RecommendationConfidence({ confidence }: RecommendationConfidenceProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/3 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-white/50">
        {confidenceLabel(confidence)}
      </p>
      <p className="mt-1 text-sm text-white/65">{confidenceExplanation(confidence)}</p>
    </div>
  );
}
