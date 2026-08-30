import type {
  HeadAgentRecommendation,
  ObjectiveTaskApprovalContext,
  ObjectiveTaskDetail,
} from "./api";
import { formatLearningStatus, formatTaskTimestamp, taskStatusLabel } from "./tasks";

export const EXECUTION_CONTEXT_MESSAGES = {
  objectiveUnavailable: "Objective information unavailable.",
  recommendationUnavailable: "No recommendation context recorded.",
  approvalUnavailable: "No approval record available.",
  evidenceEmpty: "No evidence recorded yet.",
  learningEmpty: "No learning recorded yet.",
} as const;

export type ProvenanceNodeKey =
  | "objective"
  | "recommendation"
  | "approval"
  | "task"
  | "evidence"
  | "learning";

export type ProvenanceNode = {
  key: ProvenanceNodeKey;
  label: string;
  title: string;
  detail?: string | null;
  available: boolean;
};

export function formatApprovalStatus(status: string): string {
  switch (status.toLowerCase()) {
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "pending":
      return "Pending";
    default:
      return status.replaceAll("_", " ");
  }
}

export function recommendationPrimaryText(
  recommendation: HeadAgentRecommendation,
): string {
  const recommendationText = recommendation.recommendation.trim();
  if (recommendationText) {
    return recommendationText;
  }
  const actionDescription = recommendation.proposed_action.description.trim();
  if (actionDescription) {
    return actionDescription;
  }
  return recommendation.title.trim();
}

export function recommendationSecondaryText(
  recommendation: HeadAgentRecommendation,
): string | null {
  const rationale = recommendation.rationale.trim();
  return rationale || null;
}

export function approvalContextLabel(
  approval: ObjectiveTaskApprovalContext,
): string {
  const status = formatApprovalStatus(approval.status);
  if (approval.resolved_at) {
    return `${status} ${formatTaskTimestamp(approval.resolved_at)}`;
  }
  return status;
}

export function buildProvenanceChain(task: ObjectiveTaskDetail): ProvenanceNode[] {
  const nodes: ProvenanceNode[] = [];

  nodes.push({
    key: "objective",
    label: "Objective",
    title: task.objective?.title ?? EXECUTION_CONTEXT_MESSAGES.objectiveUnavailable,
    available: task.objective !== null,
  });

  const hasRecommendation =
    task.recommendation !== null || task.provenance?.agent_task_id !== null;
  nodes.push({
    key: "recommendation",
    label: "Forge recommendation",
    title: task.recommendation
      ? recommendationPrimaryText(task.recommendation)
      : EXECUTION_CONTEXT_MESSAGES.recommendationUnavailable,
    detail: task.recommendation_question
      ? `Question: ${task.recommendation_question}`
      : null,
    available: hasRecommendation && task.recommendation !== null,
  });

  const hasApproval =
    task.approval_context !== null || task.provenance?.approval_id !== null;
  nodes.push({
    key: "approval",
    label: "Founder approval",
    title: task.approval_context
      ? approvalContextLabel(task.approval_context)
      : EXECUTION_CONTEXT_MESSAGES.approvalUnavailable,
    detail: task.approval_context?.description ?? null,
    available: hasApproval && task.approval_context !== null,
  });

  nodes.push({
    key: "task",
    label: "Founder task",
    title: task.title,
    detail: taskStatusLabel(task.status),
    available: true,
  });

  const evidenceItem = task.evidence[0];
  nodes.push({
    key: "evidence",
    label: "Evidence",
    title: evidenceItem?.title ?? EXECUTION_CONTEXT_MESSAGES.evidenceEmpty,
    detail: evidenceItem?.observed_at
      ? formatTaskTimestamp(evidenceItem.observed_at)
      : null,
    available: task.evidence.length > 0,
  });

  const learningItem = task.learnings[0];
  nodes.push({
    key: "learning",
    label: "Learning",
    title: learningItem?.statement ?? EXECUTION_CONTEXT_MESSAGES.learningEmpty,
    detail: learningItem ? formatLearningStatus(learningItem.status) : null,
    available: task.learnings.length > 0,
  });

  return nodes;
}

export function describeWorkflowNextStep(task: ObjectiveTaskDetail): string {
  if (task.status === "pending") {
    return "Start the task when you are ready to execute.";
  }
  if (task.status === "in_progress") {
    return "Continue execution, mark blocked if blocked, or complete when finished.";
  }
  if (task.status === "blocked") {
    return "Resolve the blocked reason, then resume or complete the task.";
  }
  if (task.status === "completed" && task.learnings.length === 0) {
    return "Task is complete. A learning proposal may be requested through the existing workflow.";
  }
  if (task.status === "completed" && task.learnings.some((l) => l.status === "proposed")) {
    return "A proposed learning awaits founder approval before becoming Company Brain knowledge.";
  }
  return "No further execution actions are required for this task.";
}

export function hasExecutionContextData(task: ObjectiveTaskDetail): boolean {
  return (
    task.objective !== null ||
    task.recommendation !== null ||
    task.approval_context !== null ||
    task.evidence.length > 0 ||
    task.learnings.length > 0
  );
}
