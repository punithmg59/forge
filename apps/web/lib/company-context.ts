"use client";

const STORAGE_KEY = "forge_active_company_id";

export function getActiveCompanyId(companyIds: string[]): string | null {
  if (typeof window === "undefined" || companyIds.length === 0) {
    return null;
  }
  const stored = sessionStorage.getItem(STORAGE_KEY);
  if (stored && companyIds.includes(stored)) {
    return stored;
  }
  return companyIds[0];
}

export function setActiveCompanyId(companyId: string) {
  sessionStorage.setItem(STORAGE_KEY, companyId);
}
