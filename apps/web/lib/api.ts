const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = {
  id: string;
  email: string;
  name: string | null;
};

export type Company = {
  id: string;
  name: string | null;
  slug: string | null;
  description: string | null;
  target_customer: string | null;
  stage: string | null;
  created_at: string;
};

export type OnboardingDraftResponse = {
  id: string;
  company_id: string;
  payload: Record<string, unknown>;
  current_step: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type StructureResponse = {
  draft: OnboardingDraftResponse;
  structured: boolean;
  error: string | null;
  suggestion: Record<string, unknown> | null;
};

export type ConfirmResponse = {
  draft: OnboardingDraftResponse;
  brain_initialized: boolean;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
      const first = detail[0] as { msg?: string };
      if (first.msg) {
        return first.msg;
      }
    }
  }
  return fallback;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(payload, "Something went wrong. Please try again."),
    );
  }
  return payload as T;
}

export function getCurrentUser() {
  return api<User>("/api/v1/auth/me");
}

export function register(body: { name: string; email: string; password: string }) {
  return api<{ user: User }>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function login(body: { email: string; password: string }) {
  return api<{ user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function logout() {
  return api<void>("/api/v1/auth/logout", { method: "POST" });
}

export function listCompanies() {
  return api<Company[]>("/api/v1/companies");
}

export function createCompany(body: {
  name: string;
  description?: string;
  target_customer?: string;
  stage?: string;
}) {
  return api<Company>("/api/v1/companies", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getCompany(companyId: string) {
  return api<Company>(`/api/v1/companies/${companyId}`);
}

export function getOnboardingDraft(companyId: string) {
  return api<OnboardingDraftResponse>(
    `/api/v1/companies/${companyId}/onboarding/draft`,
  );
}

export function patchOnboardingDraft(
  companyId: string,
  body: {
    payload?: Record<string, unknown>;
    current_step?: number;
    status?: string;
  },
) {
  return api<OnboardingDraftResponse>(
    `/api/v1/companies/${companyId}/onboarding/draft`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    },
  );
}

export function structureOnboarding(companyId: string) {
  return api<StructureResponse>(
    `/api/v1/companies/${companyId}/onboarding/structure`,
    { method: "POST" },
  );
}

export function confirmOnboarding(companyId: string) {
  return api<ConfirmResponse>(
    `/api/v1/companies/${companyId}/onboarding/confirm`,
    { method: "POST" },
  );
}

export type Objective = {
  id: string;
  company_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: number;
  target_value: string | null;
  target_unit: string | null;
  deadline: string | null;
  created_at: string;
  updated_at: string;
};

export type ObjectiveListResponse = {
  objectives: Objective[];
  current_objective: Objective | null;
};

export type ProposedAction = {
  type: "task" | "objective_change" | "none";
  title: string;
  description: string;
};

export type RecommendationSource = {
  entity_type: string | null;
  entity_id: string | null;
  source_type: string | null;
  source_reference: string | null;
  title: string | null;
};

export type HeadAgentRecommendation = {
  title: string;
  recommendation: string;
  rationale: string;
  proposed_action: ProposedAction;
  sources: RecommendationSource[];
  confidence: "low" | "medium" | "high";
};

export type HeadAgentRecommendResponse = {
  agent_task_id: string | null;
  recommendation: HeadAgentRecommendation;
  orchestration_mode?: "head_only" | "single_specialist" | "multi_specialist" | null;
  specialist_agents?: string[];
  specialist_analyses?: SpecialistAnalysisSummary[];
  founder_question?: string | null;
};

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

export type LearningProposal = {
  id: string;
  company_id: string;
  evidence_id: string | null;
  objective_id: string | null;
  statement: string;
  evidence_summary: string | null;
  confidence: number | null;
  status: string;
  source_evidence_ids: string[];
};

export type LearningProvenance = {
  evidence_id: string | null;
  evidence_title: string | null;
  evidence_content: string | null;
  evidence_observed_at: string | null;
  objective_task_id: string | null;
  objective_task_title: string | null;
  objective_id: string | null;
  objective_title: string | null;
};

export type CompanyLearning = {
  id: string;
  company_id: string;
  evidence_id: string | null;
  objective_id: string | null;
  statement: string;
  evidence_summary: string | null;
  confidence: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  corrected_by: string | null;
  corrected_at: string | null;
  correction_reason: string | null;
  provenance: LearningProvenance | null;
  approval_status: string | null;
};

export type LearningListResponse = {
  learnings: CompanyLearning[];
};

export type Approval = {
  id: string;
  company_id: string;
  agent_task_id: string | null;
  learning_id: string | null;
  action_type: string;
  description: string;
  risk_level: string;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  objective_task_id: string | null;
  recommendation: HeadAgentRecommendation | null;
  learning_proposal: LearningProposal | null;
};

export type ApprovalListResponse = {
  approvals: Approval[];
};

export type ExecutionStepReview = {
  step_id: string;
  sequence: number;
  tool_name: string;
  tool_version: string;
  purpose: string;
  input: Record<string, unknown>;
  expected_output: string | null;
  risk_level: "low" | "medium" | "high" | "critical";
  step_category: string;
  approval_required: boolean;
  timeout_ms: number | null;
};

export type ExecutionReview = {
  execution_id: string;
  approval_id: string;
  company_id: string;
  objective_id: string | null;
  objective_task_id: string | null;
  agent_type: string;
  goal: string;
  rationale: string;
  risk_level: "low" | "medium" | "high" | "critical";
  status: string;
  steps: ExecutionStepReview[];
  tool_summary: string[];
  approval_required: boolean;
  plan_fingerprint: string;
  expires_at: string | null;
  requested_at: string;
  trace_id: string;
};

export type FounderTask = {
  id: string;
  company_id: string;
  objective_id: string;
  title: string;
  description: string | null;
  capability: string;
  status: string;
  priority: string;
  requires_approval: boolean;
  started_at?: string | null;
  blocked_reason?: string | null;
  result_summary?: string | null;
  result_metrics?: Record<string, number> | null;
  result_notes?: string | null;
  completed_by?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type FounderTaskListResponse = {
  tasks: FounderTask[];
};

export type ObjectiveTaskStatus =
  | "pending"
  | "in_progress"
  | "blocked"
  | "completed";

export type ObjectiveTaskPriority = "low" | "medium" | "high";

export type ObjectiveTaskObjectiveSummary = {
  id: string;
  title: string;
  status: string;
};

export type ObjectiveTaskResult = {
  summary: string;
  metrics: Record<string, number> | null;
  notes: string | null;
  completed_by: string | null;
  completed_at: string | null;
};

export type ObjectiveTaskProvenance = {
  agent_task_id: string | null;
  agent_run_id: string | null;
  approval_id: string | null;
  objective_id: string | null;
};

export type ObjectiveTaskEvidence = {
  id: string;
  type: string;
  title: string;
  content: string;
  source_type: string;
  source_reference: string | null;
  observed_at: string | null;
  created_at: string;
};

export type ObjectiveTaskLearning = {
  id: string;
  statement: string;
  evidence_summary: string | null;
  confidence: number | null;
  status: string;
  evidence_id: string | null;
  objective_id: string | null;
};

export type ObjectiveTaskApprovalContext = {
  status: string;
  description: string;
  action_type: string;
  requested_at: string;
  resolved_at: string | null;
};

/** Full task detail from GET /objective-tasks/{id} */
export type ObjectiveTaskDetail = FounderTask & {
  objective: ObjectiveTaskObjectiveSummary | null;
  result: ObjectiveTaskResult | null;
  provenance: ObjectiveTaskProvenance | null;
  evidence: ObjectiveTaskEvidence[];
  learnings: ObjectiveTaskLearning[];
  recommendation: HeadAgentRecommendation | null;
  recommendation_question: string | null;
  approval_context: ObjectiveTaskApprovalContext | null;
};

/** Mutation responses from PATCH task / PATCH status / POST complete */
export type ObjectiveTaskPublic = FounderTask;

export type ObjectiveTaskUpdatePayload = {
  title?: string;
  description?: string | null;
  priority?: ObjectiveTaskPriority;
};

export type ObjectiveTaskStatusPayload = {
  status: ObjectiveTaskStatus;
  blocked_reason?: string;
  result_summary?: string;
  result_metrics?: Record<string, number>;
  result_notes?: string;
};

export type ObjectiveTaskCompletePayload = {
  result_summary: string;
  result_metrics?: Record<string, number>;
  result_notes?: string;
};

export function listObjectives(companyId: string) {
  return api<ObjectiveListResponse>(`/api/v1/companies/${companyId}/objectives`);
}

export function requestHeadAgentRecommendation(
  companyId: string,
  question?: string,
) {
  return api<HeadAgentRecommendResponse>(
    `/api/v1/companies/${companyId}/head-agent/recommend`,
    {
      method: "POST",
      body: JSON.stringify({ question: question || undefined }),
    },
  );
}

export function listApprovals(companyId: string) {
  return api<ApprovalListResponse>(`/api/v1/companies/${companyId}/approvals`);
}

export function createApproval(
  companyId: string,
  payload: { agent_task_id?: string; learning_id?: string },
) {
  return api<Approval>(`/api/v1/companies/${companyId}/approvals`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function approveApproval(companyId: string, approvalId: string) {
  return api<Approval>(
    `/api/v1/companies/${companyId}/approvals/${approvalId}/approve`,
    { method: "POST" },
  );
}

export function rejectApproval(companyId: string, approvalId: string) {
  return api<Approval>(
    `/api/v1/companies/${companyId}/approvals/${approvalId}/reject`,
    { method: "POST" },
  );
}

export function getExecutionReview(
  companyId: string,
  approvalId: string,
  executionId: string,
) {
  return api<ExecutionReview>(
    `/api/v1/companies/${companyId}/approvals/${approvalId}/execution-review?execution_id=${executionId}`,
  );
}

export function listFounderTasks(companyId: string) {
  return api<FounderTaskListResponse>(
    `/api/v1/companies/${companyId}/objective-tasks`,
  );
}

function objectiveTaskPath(companyId: string, taskId: string, suffix?: string) {
  const base = `/api/v1/companies/${companyId}/objective-tasks/${taskId}`;
  return suffix ? `${base}/${suffix}` : base;
}

export function getObjectiveTaskDetail(companyId: string, taskId: string) {
  return api<ObjectiveTaskDetail>(objectiveTaskPath(companyId, taskId));
}

export function updateObjectiveTask(
  companyId: string,
  taskId: string,
  payload: ObjectiveTaskUpdatePayload,
) {
  return api<ObjectiveTaskPublic>(objectiveTaskPath(companyId, taskId), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function transitionObjectiveTaskStatus(
  companyId: string,
  taskId: string,
  payload: ObjectiveTaskStatusPayload,
) {
  return api<ObjectiveTaskPublic>(objectiveTaskPath(companyId, taskId, "status"), {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function completeObjectiveTask(
  companyId: string,
  taskId: string,
  payload: ObjectiveTaskCompletePayload,
) {
  return api<ObjectiveTaskPublic>(objectiveTaskPath(companyId, taskId, "complete"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listLearnings(companyId: string) {
  return api<LearningListResponse>(`/api/v1/companies/${companyId}/learnings`);
}

export function correctLearning(
  companyId: string,
  learningId: string,
  reason: string,
) {
  return api<CompanyLearning>(
    `/api/v1/companies/${companyId}/learnings/${learningId}/correct`,
    {
      method: "PATCH",
      body: JSON.stringify({ reason }),
    },
  );
}

export function safeApiMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  return fallback;
}
