"use client";

import type { Approval, HeadAgentRecommendResponse } from "@/lib/api";
import { ForgeAnalyzingState } from "@/components/dashboard/ForgeAnalyzingState";
import { HeadSynthesisPanel } from "@/components/dashboard/HeadSynthesisPanel";
import { ProposedActionCard } from "@/components/dashboard/ProposedActionCard";
import { SpecialistAnalysisPanel } from "@/components/dashboard/SpecialistAnalysisPanel";
import {
  formatOrchestrationMode,
  formatSpecialistAgentType,
  normalizeRecommendResponse,
  recommendationApprovalStatus,
} from "@/lib/specialist-intelligence";

const DEFAULT_QUESTION = "What should I focus on next?";

type ForgeRecommendationPanelProps = {
  recommendation: HeadAgentRecommendResponse | null;
  recommendationError: string | null;
  question: string;
  recommendationLoading: boolean;
  approvalRequestLoading: boolean;
  approvals: Approval[];
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
  approvals,
  canRequestApproval,
  onQuestionChange,
  onAskForge,
  onRequestApproval,
}: ForgeRecommendationPanelProps) {
  const normalized = normalizeRecommendResponse(recommendation);
  const approvalStatus = recommendationApprovalStatus(
    approvals,
    normalized?.agent_task_id ?? null,
    canRequestApproval,
  );

  if (recommendationError && !normalized) {
    return (
      <div className="space-y-4">
        <RecommendationErrorBanner
          message={recommendationError}
          onRetry={onAskForge}
          retryLoading={recommendationLoading}
          question={question}
        />
        <RecommendationQuestionForm
          question={question}
          onQuestionChange={onQuestionChange}
          onAskForge={onAskForge}
          loading={recommendationLoading}
        />
      </div>
    );
  }

  if (!normalized) {
    return (
      <div className="space-y-4">
        {recommendationLoading ? (
          <ForgeAnalyzingState />
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

  const orchestrationMode = normalized.orchestration_mode ?? "head_only";
  const specialistAgents = normalized.specialist_agents ?? [];
  const founderQuestion = normalized.founder_question?.trim() || question.trim();
  const showSpecialists = orchestrationMode !== "head_only";

  return (
    <div className="space-y-5">
      {recommendationLoading ? (
        <div className="space-y-2">
          <p className="text-xs text-violet-200/70" role="status" aria-live="polite">
            Preparing a new recommendation…
          </p>
          <ForgeAnalyzingState orchestrationHint={orchestrationMode} />
        </div>
      ) : null}

      {recommendationError ? (
        <RecommendationErrorBanner
          message={recommendationError}
          onRetry={onAskForge}
          retryLoading={recommendationLoading}
          question={question}
        />
      ) : null}

      <OrchestrationHeader
        founderQuestion={founderQuestion}
        orchestrationLabel={formatOrchestrationMode(orchestrationMode)}
        specialistAgents={specialistAgents}
        showSpecialists={showSpecialists}
      />

      <div
        className={`flex flex-col gap-5 ${recommendationLoading ? "opacity-75" : ""}`}
        aria-busy={recommendationLoading}
      >
        <section aria-labelledby="forge-synthesis-heading" className="order-1">
          <HeadSynthesisPanel recommendation={normalized.recommendation} />
        </section>

        <section aria-labelledby="forge-proposed-action-heading" className="order-2">
          <ProposedActionCard
            recommendation={normalized.recommendation}
            approvalStatus={approvalStatus}
            approvalRequestLoading={approvalRequestLoading}
            onRequestApproval={onRequestApproval}
          />
        </section>

        {showSpecialists ? (
          <section
            aria-labelledby="forge-specialist-heading"
            className="order-4 md:order-3"
          >
            <SpecialistAnalysisPanel
              analyses={normalized.specialist_analyses ?? []}
              orchestrationMode={orchestrationMode}
            />
          </section>
        ) : null}
      </div>

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

function OrchestrationHeader({
  founderQuestion,
  orchestrationLabel,
  specialistAgents,
  showSpecialists,
}: {
  founderQuestion: string;
  orchestrationLabel: string;
  specialistAgents: string[];
  showSpecialists: boolean;
}) {
  return (
    <header className="rounded-lg border border-white/8 bg-white/3 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-white/45">
        Forge recommendation
      </p>
      <h2 className="mt-1 text-sm font-medium text-white" id="forge-founder-question">
        {founderQuestion}
      </h2>
      <p className="mt-2 text-xs text-white/55">
        Mode: <span className="text-white/75">{orchestrationLabel}</span>
      </p>
      {showSpecialists && specialistAgents.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs text-white/45">Specialists consulted</p>
          <ul className="mt-1 flex flex-wrap gap-2">
            {specialistAgents.map((agentType) => (
              <li
                key={agentType}
                className="rounded-full border border-sky-400/25 bg-sky-500/10 px-2.5 py-1 text-xs text-sky-100/90"
              >
                {formatSpecialistAgentType(agentType)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </header>
  );
}

function RecommendationErrorBanner({
  message,
  onRetry,
  retryLoading,
  question,
}: {
  message: string;
  onRetry: () => void;
  retryLoading: boolean;
  question: string;
}) {
  return (
    <div
      className="rounded-xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-200/90"
      role="alert"
    >
      <p>{message}</p>
      <button
        className="forge-button mt-3 w-auto px-4"
        type="button"
        disabled={retryLoading || !question.trim()}
        onClick={onRetry}
        aria-label="Retry Forge recommendation"
      >
        {retryLoading ? "Retrying..." : "Try again"}
      </button>
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
        aria-label={loading ? "Forge is analyzing" : "Ask Forge for a recommendation"}
      >
        {loading ? "Analyzing…" : "Ask Forge"}
      </button>
    </div>
  );
}
