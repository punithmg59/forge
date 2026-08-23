import { describe, expect, it } from "vitest";

import {
  emptyPayload,
  isDraftConfirmed,
  resolveOnboardingDestination,
  reviewRows,
  validateStep,
} from "./onboarding";

describe("onboarding routing gate", () => {
  it("sends unauthenticated users to login", () => {
    expect(
      resolveOnboardingDestination({
        authenticated: false,
        companyCount: 1,
        draft: null,
      }),
    ).toBe("/login");
  });

  it("sends users without a company to onboarding", () => {
    expect(
      resolveOnboardingDestination({
        authenticated: true,
        companyCount: 0,
        draft: null,
      }),
    ).toBe("/onboarding");
  });

  it("keeps unconfirmed companies in onboarding", () => {
    expect(
      resolveOnboardingDestination({
        authenticated: true,
        companyCount: 1,
        draft: {
          id: "1",
          company_id: "c1",
          payload: emptyPayload(),
          current_step: 2,
          status: "draft",
          created_at: "",
          updated_at: "",
        },
      }),
    ).toBe("/onboarding");
  });

  it("sends confirmed companies to dashboard", () => {
    const draft = {
      id: "1",
      company_id: "c1",
      payload: emptyPayload(),
      current_step: 5,
      status: "confirmed",
      created_at: "",
      updated_at: "",
    };
    expect(isDraftConfirmed(draft)).toBe(true);
    expect(
      resolveOnboardingDestination({
        authenticated: true,
        companyCount: 1,
        draft,
      }),
    ).toBe("/dashboard");
  });
});

describe("onboarding validation and review", () => {
  it("requires screen 1 fields", () => {
    expect(validateStep(1, emptyPayload())).toMatch(/Company name/);
  });

  it("marks founder values as From you", () => {
    const payload = emptyPayload();
    payload.company.name = "Forge";
    payload.customer.problem = "We believe onboarding is confusing";
    const rows = reviewRows(payload);
    expect(rows.find((row) => row.label === "Company")?.source).toBe("From you");
    expect(rows.find((row) => row.label === "Problem")?.value).toContain("believe");
  });
});
