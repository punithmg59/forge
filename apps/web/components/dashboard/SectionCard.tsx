import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: string | null;
  empty?: ReactNode;
  children?: ReactNode;
  id?: string;
  onRetry?: () => void;
};

export function SectionCard({
  title,
  subtitle,
  loading,
  error,
  empty,
  children,
  id,
  onRetry,
}: SectionCardProps) {
  return (
    <section id={id} className="glass-card p-6" aria-labelledby={id ? `${id}-title` : undefined}>
      <div className="mb-4">
        <p id={id ? `${id}-title` : undefined} className="forge-label">{title}</p>
        {subtitle ? <p className="text-sm text-white/50">{subtitle}</p> : null}
      </div>
      {loading ? (
        <div className="space-y-3" aria-busy="true" aria-label={`Loading ${title}`}>
          <div className="dashboard-skeleton h-5 w-40" />
          <div className="dashboard-skeleton h-16" />
          <div className="dashboard-skeleton h-16" />
        </div>
      ) : error ? (
        <div className="text-sm text-red-300/90">
          <p>{error}</p>
          {onRetry ? (
            <button type="button" className="forge-button-secondary mt-3" onClick={onRetry}>
              Retry
            </button>
          ) : null}
        </div>
      ) : empty ? (
        <div className="text-sm text-white/45">{empty}</div>
      ) : (
        children
      )}
    </section>
  );
}
