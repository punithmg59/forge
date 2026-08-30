import type { OperatingLoopStage } from "@/lib/founder-dashboard";

export function OperatingLoopPanel({ stages }: { stages: OperatingLoopStage[] }) {
  return (
    <section className="glass-card p-6" aria-labelledby="operating-loop-heading">
      <p className="forge-label">Operating loop</p>
      <h2 id="operating-loop-heading" className="text-base font-medium text-white">
        How Forge work flows through the company
      </h2>
      <ol className="mt-4 flex flex-col gap-0 sm:flex-row sm:flex-wrap sm:items-center sm:gap-2">
        {stages.map((stage, index) => (
          <li key={stage.key} className="flex items-center gap-2">
            <span
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                stage.active
                  ? "border-violet-400/30 bg-violet-500/10 text-violet-100"
                  : "border-white/8 bg-white/3 text-white/45"
              }`}
            >
              {stage.label}
            </span>
            {index < stages.length - 1 ? (
              <span className="hidden text-white/30 sm:inline" aria-hidden="true">→</span>
            ) : null}
            {index < stages.length - 1 ? (
              <span className="py-1 text-white/30 sm:hidden" aria-hidden="true">↓</span>
            ) : null}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-white/40">
        Stages reflect records present in Forge — not every company has every stage at once.
      </p>
    </section>
  );
}
