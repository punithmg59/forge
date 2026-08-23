export type Stage = "idea" | "mvp" | "growth" | "scale";

export type OnboardingPayload = {
  company: {
    name?: string;
    product_description?: string;
    stage?: Stage | string;
  };
  customer: {
    target_customer?: string;
    problem?: string;
    beliefs?: string[];
  };
  current_situation: {
    objective?: string;
    bottleneck?: string;
    deadline?: string;
    constraint?: string | {
      type?: string;
      name?: string;
      description?: string;
      value?: string;
      severity?: string;
    };
  };
  context: {
    mission?: string;
    non_goals?: string;
  };
  ai_suggestion?: Record<string, unknown> | null;
};

export type OnboardingDraft = {
  id: string;
  company_id: string;
  payload: OnboardingPayload;
  current_step: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export const STAGES: { value: Stage; label: string }[] = [
  { value: "idea", label: "Idea" },
  { value: "mvp", label: "MVP" },
  { value: "growth", label: "Growth" },
  { value: "scale", label: "Scale" },
];

export function emptyPayload(): OnboardingPayload {
  return {
    company: {},
    customer: {},
    current_situation: {},
    context: {},
    ai_suggestion: null,
  };
}

export function normalizePayload(raw: unknown): OnboardingPayload {
  const value = (raw ?? {}) as Partial<OnboardingPayload>;
  return {
    company: { ...(value.company ?? {}) },
    customer: { ...(value.customer ?? {}) },
    current_situation: { ...(value.current_situation ?? {}) },
    context: { ...(value.context ?? {}) },
    ai_suggestion: value.ai_suggestion ?? null,
  };
}

export function isDraftConfirmed(draft: OnboardingDraft | null | undefined): boolean {
  return draft?.status === "confirmed";
}

export function resolveOnboardingDestination(args: {
  authenticated: boolean;
  companyCount: number;
  draft: OnboardingDraft | null;
}): "/login" | "/onboarding" | "/dashboard" {
  if (!args.authenticated) {
    return "/login";
  }
  if (args.companyCount === 0) {
    return "/onboarding";
  }
  if (isDraftConfirmed(args.draft)) {
    return "/dashboard";
  }
  return "/onboarding";
}

export function validateStep(step: number, payload: OnboardingPayload): string | null {
  if (step === 1) {
    if (!payload.company.name?.trim()) {
      return "Company name is required.";
    }
    if (!payload.company.product_description?.trim()) {
      return "Product description is required.";
    }
    if (!payload.company.stage?.trim()) {
      return "Stage is required.";
    }
  }
  if (step === 2) {
    if (!payload.customer.target_customer?.trim()) {
      return "Target customer is required.";
    }
    if (!payload.customer.problem?.trim()) {
      return "Problem being solved is required.";
    }
  }
  if (step === 3) {
    if (!payload.current_situation.objective?.trim()) {
      return "Current objective is required.";
    }
    if (!payload.current_situation.bottleneck?.trim()) {
      return "Current bottleneck is required.";
    }
  }
  return null;
}

export function constraintText(payload: OnboardingPayload): string {
  const value = payload.current_situation.constraint;
  if (!value) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  return value.description || value.value || value.name || "";
}

export function reviewRows(payload: OnboardingPayload): Array<{
  label: string;
  value: string;
  source: "From you" | "Suggested from your input";
}> {
  const suggestion = (payload.ai_suggestion ?? {}) as {
    company?: Record<string, string | null>;
    customer?: Record<string, unknown>;
    current_situation?: Record<string, unknown>;
    context?: Record<string, string | null>;
  };

  const pick = (
    label: string,
    founderValue: string | undefined,
    suggestedValue: unknown,
  ) => {
    const founder = founderValue?.trim() || "";
    const suggested =
      typeof suggestedValue === "string" ? suggestedValue.trim() : "";
    if (founder) {
      return { label, value: founder, source: "From you" as const };
    }
    if (suggested) {
      return {
        label,
        value: suggested,
        source: "Suggested from your input" as const,
      };
    }
    return { label, value: "Not set", source: "From you" as const };
  };

  return [
    pick("Company", payload.company.name, suggestion.company?.name),
    pick(
      "Product",
      payload.company.product_description,
      suggestion.company?.product_description,
    ),
    pick("Stage", payload.company.stage, suggestion.company?.stage),
    pick(
      "Customer",
      payload.customer.target_customer,
      suggestion.customer?.target_customer,
    ),
    pick("Problem", payload.customer.problem, suggestion.customer?.problem),
    pick(
      "Objective",
      payload.current_situation.objective,
      suggestion.current_situation?.objective,
    ),
    pick(
      "Bottleneck",
      payload.current_situation.bottleneck,
      suggestion.current_situation?.bottleneck,
    ),
    pick("Constraint", constraintText(payload) || undefined, undefined),
    pick("Mission", payload.context.mission, suggestion.context?.mission),
    pick("Non-goals", payload.context.non_goals, suggestion.context?.non_goals),
  ];
}
