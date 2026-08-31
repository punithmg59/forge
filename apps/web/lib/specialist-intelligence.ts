import type {
  Approval,
  HeadAgentRecommendResponse,
  RecommendationSource,
} from "./api";

export type OrchestrationMode = "head_only" | "single_specialist" | "multi_specialist";

export type SpecialistAnalysisSummary = {
  agent_type: string;
  domain: string;
  display_name: string;
  agent_task_id: string | null;
  title: string;
  recommendation: string;
  rationale: string;
  confidence: "low" | "medium" | "high";
  sources: RecommendationSource[];
};

export type RecommendationApprovalStatus =
  | "none"
  | "can_request"
  | "pending"
  | "approved"
  | "rejected";

const SPECIALIST_DISPLAY_NAMES: Record<string, string> = {
  customer_growth: "Customer & Growth",
  product: "Product",
};

export function formatSpecialistAgentType(agentType: string): string {
  return SPECIALIST_DISPLAY_NAMES[agentType] ?? "Specialist analysis";
}

export function formatOrchestrationMode(mode: OrchestrationMode | null | undefined): string {
  switch (mode) {
    case "head_only":
      return "Forge analysis";
    case "single_specialist":
      return "Specialist analysis";
    case "multi_specialist":
      return "Multi-specialist analysis";
    default:
      return "Forge analysis";
  }
}

export function confidenceLabel(confidence: "low" | "medium" | "high"): string {
  return `${confidence.toUpperCase()} CONFIDENCE`;
}

export function confidenceExplanation(confidence: "low" | "medium" | "high"): string {
  switch (confidence) {
    case "low":
      return "Limited grounded evidence.";
    case "medium":
      return "Some relevant grounded evidence.";
    case "high":
      return "Strongly grounded in available company evidence.";
  }
}

export function hasSpecialistAnalyses(
  response: HeadAgentRecommendResponse | null,
): boolean {
  return Boolean(response?.specialist_analyses?.length);
}

export function shouldShowMultiSpecialistPerspectives(
  response: HeadAgentRecommendResponse | null,
): boolean {
  return response?.orchestration_mode === "multi_specialist" &&
    (response.specialist_analyses?.length ?? 0) >= 2;
}

export function normalizeRecommendResponse(
  response: HeadAgentRecommendResponse | null,
): HeadAgentRecommendResponse | null {
  if (!response) {
    return null;
  }
  return {
    ...response,
    orchestration_mode: response.orchestration_mode ?? "head_only",
    specialist_agents: response.specialist_agents ?? [],
    specialist_analyses: response.specialist_analyses ?? [],
  };
}

export function recommendationApprovalStatus(
  approvals: Approval[],
  agentTaskId: string | null,
  canRequestApproval: boolean,
): RecommendationApprovalStatus {
  if (!agentTaskId) {
    return "none";
  }
  const related = approvals.filter((approval) => approval.agent_task_id === agentTaskId);
  if (related.some((approval) => approval.status === "pending")) {
    return "pending";
  }
  if (related.some((approval) => approval.status === "approved")) {
    return "approved";
  }
  if (related.some((approval) => approval.status === "rejected")) {
    return "rejected";
  }
  if (canRequestApproval) {
    return "can_request";
  }
  return "none";
}

export function formatSourceLabel(source: RecommendationSource): string {
  const parts = [source.entity_type, source.source_type, source.title].filter(Boolean);
  return parts.join(" · ") || "Company Brain source";
}

export function groupSourceLabels(sources: RecommendationSource[]): string[] {
  const labels = new Set<string>();
  for (const source of sources) {
    if (source.entity_type) {
      labels.add(source.entity_type.replaceAll("_", " "));
    }
  }
  return Array.from(labels);
}
