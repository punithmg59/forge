"use client";

import type { HeadAgentRecommendResponse } from "@/lib/api";
import { formatActionType } from "@/lib/operating";

const DEFAULT_QUESTION = "What should I focus on next?";

type ForgeRecommendationPanelProps = {
  recommendation: HeadAgentRecommendResponse | null;
  recommendationError: string | null;
  question: string;
  recommendationLoading: boolean;
  approvalRequestLoading: boolean;
  canRequestApproval: boolean;
  onQuestionChange: (value: string) => void;
  onAskForge: () => void;
  onRequestApproval: () => void;
};

export function ForgeRecommendationPanel({
  recommendation,
  recommendationError,
  question,
  recommendationLoading,
  approvalRequestLoading,
  canRequestApproval,
  onQuestionChange,
  onAskForge,
  onRequestApproval,
}: ForgeRecommendationPanelProps) {
  if (recommendationError && !recommendation) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-200/90">
          <p>{recommendationError}</p>
          <button
            className="forge-button mt-3 w-auto px-4"
            type="button"
            disabled={recommendationLoading || !question.trim()}
            onClick={onAskForge}
          >
            {recommendationLoading ? "Retrying..." : "Try again"}
          </button>
        </div>
        <RecommendationQuestionForm
          question={question}
          onQuestionChange={onQuestionChange}
          onAskForge={onAskForge}
          loading={recommendationLoading}
        />
      </div>
    );
  }

  if (!recommendation) {
    return (
      <div className="space-y-4">
        {recommendationLoading ? (
          <HeadAgentLoadingState />
        ) : (
          <p className="text-sm text-white/50">
            Ask Forge for a proposal grounded in company context.
          </p>
        )}
        <RecommendationQuestionForm
          question={question}
          onQuestionChange={onQuestionChange}
          onAskForge={onAskForge}
          loading={recommendationLoading}
        />
      </div>
    );
  }

  const rec = recommendation.recommendation;
  return (
    <div className="space-y-4">
      {recommendationLoading ? <HeadAgentLoadingState /> : null}
      <div
        className={`rounded-xl border border-violet-400/20 bg-violet-500/5 p-4 ${
          recommendationLoading ? "opacity-60" : ""
        }`}
      >
        <p className="mb-1 text-xs uppercase tracking-widest text-violet-200/70">Forge proposal</p>
        <h3 className="text-lg font-semibold text-white">{rec.title}</h3>
        <p className="mt-2 text-sm text-white/75">{rec.recommendation}</p>
        <p className="mt-3 text-sm text-white/55">
          <span className="text-white/70">Rationale:</span> {rec.rationale}
        </p>
      </div>
      <div className="grid gap-3 text-sm sm:grid-cols-2">
        <Meta label="Proposed action" value={formatActionType(rec.proposed_action.type)} />
        <Meta label="Confidence" value={rec.confidence} />
      </div>
      {rec.sources.length > 0 ? (
        <div>
          <p className="forge-label">Sources</p>
          <ul className="mt-2 space-y-1 text-xs text-white/55">
            {rec.sources.map((source, index) => (
              <li key={`${source.entity_type}-${index}`}>
                {source.entity_type ?? "source"}
                {source.source_type ? ` · ${source.source_type}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {canRequestApproval && !recommendationLoading ? (
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={approvalRequestLoading}
          onClick={onRequestApproval}
        >
          {approvalRequestLoading ? "Submitting..." : "Request approval"}
        </button>
      ) : null}
      <div className="border-t border-white/8 pt-4">
        <RecommendationQuestionForm
          question={question}
          onQuestionChange={onQuestionChange}
          onAskForge={onAskForge}
          loading={recommendationLoading}
          label="Ask Forge again"
          inputId="forge-question-followup"
        />
      </div>
    </div>
  );
}

function HeadAgentLoadingState() {
  return (
    <div
      className="rounded-xl border border-violet-400/25 bg-violet-500/10 p-4"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 inline-block h-4 w-4 animate-spin rounded-full border-2 border-violet-300/30 border-t-violet-200"
          aria-hidden="true"
        />
        <div>
          <p className="text-sm font-medium text-violet-100">
            Forge is analyzing your company context…
          </p>
          <p className="mt-1 text-xs text-violet-200/70">
            This can take a moment while Forge reviews your objective and Company Brain.
          </p>
        </div>
      </div>
    </div>
  );
}

function RecommendationQuestionForm({
  question,
  onQuestionChange,
  onAskForge,
  loading,
  label = "Ask Forge",
  inputId = "forge-question",
}: {
  question: string;
  onQuestionChange: (value: string) => void;
  onAskForge: () => void;
  loading: boolean;
  label?: string;
  inputId?: string;
}) {
  return (
    <div className="space-y-3">
      <label className="forge-label" htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        className="forge-input"
        value={question}
        disabled={loading}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder={DEFAULT_QUESTION}
      />
      <button
        className="forge-button w-auto px-5"
        type="button"
        disabled={loading || !question.trim()}
        onClick={onAskForge}
      >
        {loading ? "Analyzing…" : "Ask Forge"}
      </button>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-white/45">{label}</p>
      <p className="text-white/75">{value}</p>
    </div>
  );
}
