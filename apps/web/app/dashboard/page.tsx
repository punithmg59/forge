"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { OperatingView } from "@/components/dashboard/OperatingView";
import {
  ApiError,
  Company,
  User,
  getCurrentUser,
  getOnboardingDraft,
  listCompanies,
  logout,
} from "@/lib/api";
import { getActiveCompanyId, setActiveCompanyId } from "@/lib/company-context";
import { OnboardingDraft, isDraftConfirmed, normalizePayload } from "@/lib/onboarding";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const currentUser = await getCurrentUser();
        const companyList = await listCompanies();
        if (cancelled) {
          return;
        }
        if (companyList.length === 0) {
          router.replace("/onboarding");
          return;
        }

        const selected =
          getActiveCompanyId(companyList.map((company) => company.id)) ??
          companyList[0].id;
        setActiveCompanyId(selected);

        const existing = await getOnboardingDraft(selected);
        const loadedDraft: OnboardingDraft = {
          ...(existing as OnboardingDraft),
          payload: normalizePayload(existing.payload),
        };

        if (!isDraftConfirmed(loadedDraft)) {
          router.replace("/onboarding");
          return;
        }

        if (cancelled) {
          return;
        }
        setUser(currentUser);
        setCompanies(companyList);
        setActiveId(selected);
        setReady(true);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        if (err instanceof ApiError && (err.status === 403 || err.status === 404)) {
          router.replace("/onboarding");
          return;
        }
        router.replace("/login");
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const active = companies.find((company) => company.id === activeId) ?? companies[0];

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  async function onSelectCompany(companyId: string) {
    setActiveCompanyId(companyId);
    try {
      const existing = await getOnboardingDraft(companyId);
      if (!isDraftConfirmed(existing as OnboardingDraft)) {
        router.replace("/onboarding");
        return;
      }
      setActiveId(companyId);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 404 || err.status === 403)) {
        router.replace("/onboarding");
        return;
      }
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
      }
    }
  }

  if (!ready || !user || !active || !activeId) {
    return (
      <div className="grid-bg flex min-h-screen items-center justify-center text-sm text-white/40">
        Loading...
      </div>
    );
  }

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden">
      <div
        className="orb orb-purple"
        style={{ width: 500, height: 500, top: "-120px", left: "-120px" }}
      />
      <nav className="nav-bar relative z-10 flex items-center justify-between px-6 py-3">
        <span className="text-sm font-semibold tracking-widest uppercase text-white/80">
          FORGE
        </span>
        <div className="flex items-center gap-3">
          {companies.length > 1 ? (
            <select
              className="forge-input w-auto py-2"
              value={active.id}
              aria-label="Select company"
              onChange={(event) => void onSelectCompany(event.target.value)}
            >
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          ) : null}
          <button className="text-sm text-white/60" onClick={() => void onLogout()} type="button">
            Logout
          </button>
        </div>
      </nav>
      <main className="relative z-10 mx-auto max-w-6xl px-6 py-10">
        <p className="mb-2 text-xs tracking-widest uppercase text-white/40">Founder Command Center</p>
        <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-white">{active.name}</h1>
            <p className="mt-2 text-sm text-white/50">
              Signed in as {user.name ?? user.email}. Review direction, attention items, execution,
              and Company Brain.
            </p>
          </div>
          <p className="text-xs text-white/40">Operating console</p>
        </div>
        <OperatingView companyId={activeId} />
      </main>
    </div>
  );
}
