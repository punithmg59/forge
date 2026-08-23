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
