"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { FounderTaskWorkspace } from "@/components/tasks/FounderTaskWorkspace";
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
import { OnboardingDraft, isDraftConfirmed } from "@/lib/onboarding";

export default function FounderTasksPage() {
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
        if (!isDraftConfirmed(existing as OnboardingDraft)) {
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
    try {
      const existing = await getOnboardingDraft(companyId);
      if (!isDraftConfirmed(existing as OnboardingDraft)) {
        router.replace("/onboarding");
        return;
      }
      setActiveCompanyId(companyId);
      router.push("/dashboard/tasks");
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
        <div className="space-y-3 w-full max-w-2xl px-6">
          <div className="task-workspace-skeleton h-10 w-48" />
          <div className="task-workspace-skeleton h-10" />
          <div className="task-workspace-skeleton h-28" />
        </div>
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
        <Link
          href="/dashboard"
          className="text-sm font-semibold tracking-widest uppercase text-white/80 transition hover:text-white"
        >
          FORGE
        </Link>
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
          <button
            className="text-sm text-white/60"
            onClick={() => void onLogout()}
            type="button"
          >
            Logout
          </button>
        </div>
      </nav>
      <main className="relative z-10 mx-auto max-w-4xl px-6 py-10">
        <Link
          href="/dashboard"
          className="text-sm text-white/55 transition hover:text-white/80"
        >
          ← Back to dashboard
        </Link>
        <h1 className="mt-4 text-2xl font-semibold text-white">Founder Tasks</h1>
        <p className="mt-2 text-sm text-white/55">
          Review blocked work, in-progress execution, and upcoming tasks.
        </p>
        <div className="mt-8">
          <FounderTaskWorkspace companyId={activeId} />
        </div>
      </main>
    </div>
  );
}
