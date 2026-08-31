import type { Approval, HeadAgentRecommendation, Objective } from "./api";

export function filterPendingApprovals(approvals: Approval[]): Approval[] {
  return approvals.filter((approval) => approval.status === "pending");
}

export function hasPendingApprovalForAgentTask(
  approvals: Approval[],
  agentTaskId: string | null,
): boolean {
  if (!agentTaskId) {
    return false;
  }
  return approvals.some(
    (approval) =>
      approval.agent_task_id === agentTaskId && approval.status === "pending",
  );
}

export function isActionableRecommendation(
  recommendation: HeadAgentRecommendation,
): boolean {
  return recommendation.proposed_action.type !== "none";
}

export function formatObjectiveMetric(objective: Objective): string | null {
  if (objective.target_value && objective.target_unit) {
    return `${objective.target_value} ${objective.target_unit}`;
  }
  if (objective.target_value) {
    return objective.target_value;
  }
  return null;
}

export function formatActionType(actionType: string): string {
  return actionType.replaceAll("_", " ");
}

export function formatLearningStatus(status: string): string {
  return status.toUpperCase();
}

export function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function objectiveTitleById(
  objectives: Objective[],
  objectiveId: string,
): string | null {
  return objectives.find((objective) => objective.id === objectiveId)?.title ?? null;
}

export const OPERATING_ERRORS = {
  objective: "Unable to load the current objective.",
  recommendation: "Forge could not generate a recommendation. Please try again.",
  recommendationBrainContext:
    "Forge could not load full Company Brain context. Structured data was used where available.",
  recommendationProvider:
    "Forge's AI provider is unavailable or misconfigured. Check API settings and try again.",
  recommendationTimeout: "Forge took too long to respond. Please try again.",
  approvals: "Unable to load pending approvals.",
  tasks: "Unable to load founder tasks.",
  approvalAction: "Approval could not be completed.",
  brain: "Unable to load Company Brain knowledge.",
} as const;

export function mapRecommendationApiError(message: string, status: number): string {
  if (message.includes("Brain context retrieval failed")) {
    return OPERATING_ERRORS.recommendationBrainContext;
  }
  if (
    message.includes("LLM provider") ||
    message.includes("provider unavailable") ||
    message.includes("not configured")
  ) {
    return OPERATING_ERRORS.recommendationProvider;
  }
  if (message.includes("timed out") || status === 504) {
    return "Forge is taking longer than expected. Please try again.";
  }
  if (message.includes("rate limit") || status === 429) {
    return "Forge is temporarily busy. Please try again shortly.";
  }
  if (status >= 500) {
    return OPERATING_ERRORS.recommendation;
  }
  return message || OPERATING_ERRORS.recommendation;
}
