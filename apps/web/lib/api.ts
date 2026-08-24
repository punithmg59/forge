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
};

export type Approval = {
  id: string;
  company_id: string;
  agent_task_id: string | null;
  action_type: string;
  description: string;
  risk_level: string;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  objective_task_id: string | null;
  recommendation: HeadAgentRecommendation | null;
};

export type ApprovalListResponse = {
  approvals: Approval[];
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
  created_at: string;
  updated_at: string;
};

export type FounderTaskListResponse = {
  tasks: FounderTask[];
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

export function createApproval(companyId: string, agentTaskId: string) {
  return api<Approval>(`/api/v1/companies/${companyId}/approvals`, {
    method: "POST",
    body: JSON.stringify({ agent_task_id: agentTaskId }),
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

export function listFounderTasks(companyId: string) {
  return api<FounderTaskListResponse>(
    `/api/v1/companies/${companyId}/objective-tasks`,
  );
}

export function safeApiMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  return fallback;
}
