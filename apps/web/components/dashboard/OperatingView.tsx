"use client";

import { FounderCommandCenter } from "@/components/dashboard/FounderCommandCenter";

type OperatingViewProps = {
  companyId: string;
};

export function OperatingView({ companyId }: OperatingViewProps) {
  return <FounderCommandCenter companyId={companyId} />;
}
