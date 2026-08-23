"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/AuthShell";
import { OnboardingWizard } from "@/components/onboarding/Wizard";
import {
  ApiError,
  createCompany,
  getCurrentUser,
  getOnboardingDraft,
  listCompanies,
  patchOnboardingDraft,
} from "@/lib/api";
import { setActiveCompanyId } from "@/lib/company-context";
import {
  OnboardingDraft,
  STAGES,
  emptyPayload,
  isDraftConfirmed,
  normalizePayload,
} from "@/lib/onboarding";

export default function OnboardingPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"loading" | "create" | "wizard">("loading");
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [draft, setDraft] = useState<OnboardingDraft | null>(null);
  const [name, setName] = useState("");
  const [stage, setStage] = useState("mvp");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        await getCurrentUser();
        const companies = await listCompanies();
        if (cancelled) {
          return;
        }
        if (companies.length === 0) {
          setMode("create");
          return;
        }

        const active = companies[0];
        setActiveCompanyId(active.id);
        setCompanyId(active.id);

        try {
          const existing = await getOnboardingDraft(active.id);
          if (cancelled) {
            return;
          }
          if (isDraftConfirmed(existing as OnboardingDraft)) {
            router.replace("/dashboard");
            return;
          }
          setDraft({
            ...(existing as OnboardingDraft),
            payload: normalizePayload(existing.payload),
          });
          setMode("wizard");
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            const created = await patchOnboardingDraft(active.id, {
              current_step: 1,
              payload: {
                ...emptyPayload(),
                company: {
                  name: active.name ?? "",
                  product_description: active.description ?? "",
                  stage: active.stage ?? "mvp",
                },
                customer: {
                  target_customer: active.target_customer ?? "",
                },
              },
            });
            if (cancelled) {
              return;
            }
            setDraft({
              ...(created as OnboardingDraft),
              payload: normalizePayload(created.payload),
            });
            setMode("wizard");
            return;
          }
          throw err;
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        if (!cancelled) {
          setError("Unable to load onboarding. Please refresh.");
          setMode("create");
        }
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onCreateCompany(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Company name is required.");
      return;
    }
    setPending(true);
    try {
      const company = await createCompany({
        name: name.trim(),
        stage,
      });
      setActiveCompanyId(company.id);
      const created = await patchOnboardingDraft(company.id, {
        current_step: 1,
        payload: {
          ...emptyPayload(),
          company: {
            name: company.name ?? name.trim(),
            stage,
          },
        },
      });
      setCompanyId(company.id);
      setDraft({
        ...(created as OnboardingDraft),
        payload: normalizePayload(created.payload),
      });
      setMode("wizard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to create your company. Please try again.",
      );
    } finally {
      setPending(false);
    }
  }

  if (mode === "loading") {
    return (
      <div className="grid-bg flex min-h-screen items-center justify-center text-sm text-white/40">
        Loading...
      </div>
    );
  }

  if (mode === "wizard" && companyId && draft) {
    return <OnboardingWizard companyId={companyId} initialDraft={draft} />;
  }

  return (
    <AuthShell
      title="Create your company"
      subtitle="This becomes the tenant boundary for your Company Brain."
    >
      <form onSubmit={onCreateCompany} className="space-y-4">
        <div>
          <label className="forge-label" htmlFor="companyName">
            Company name <span className="text-violet-300">Required</span>
          </label>
          <input
            id="companyName"
            className="forge-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <p className="mt-1 text-xs text-white/30">Example: Forge</p>
        </div>
        <div>
          <label className="forge-label" htmlFor="stage">
            Stage
          </label>
          <select
            id="stage"
            className="forge-input"
            value={stage}
            onChange={(event) => setStage(event.target.value)}
          >
            {STAGES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <button className="forge-button" type="submit" disabled={pending}>
          {pending ? "Creating..." : "Start onboarding"}
        </button>
      </form>
    </AuthShell>
  );
}
