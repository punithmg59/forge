import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: string | null;
  empty?: ReactNode;
  children?: ReactNode;
};

export function SectionCard({
  title,
  subtitle,
  loading,
  error,
  empty,
  children,
}: SectionCardProps) {
  return (
    <section className="glass-card p-6">
      <div className="mb-4">
        <p className="forge-label">{title}</p>
        {subtitle ? <p className="text-sm text-white/50">{subtitle}</p> : null}
      </div>
      {loading ? (
        <p className="text-sm text-white/40">Loading...</p>
      ) : error ? (
        <p className="text-sm text-red-300/90">{error}</p>
      ) : empty ? (
        <div className="text-sm text-white/45">{empty}</div>
      ) : (
        children
      )}
    </section>
  );
}
