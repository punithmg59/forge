type ForgeAnalyzingStateProps = {
  orchestrationHint?: "head_only" | "single_specialist" | "multi_specialist" | null;
};

export function ForgeAnalyzingState({ orchestrationHint }: ForgeAnalyzingStateProps) {
  const mayUseSpecialists = orchestrationHint !== "head_only";

  return (
    <div
      className="rounded-xl border border-violet-400/25 bg-violet-500/10 p-4"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <p className="text-sm font-medium text-violet-100">Forge is analyzing</p>
      <ul className="mt-3 space-y-2 text-sm text-violet-100/85">
        <li className="flex items-start gap-2">
          <span className="text-emerald-300" aria-hidden="true">✓</span>
          <span>Understanding your question</span>
        </li>
        <li className="flex items-start gap-2">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-violet-300/30 border-t-violet-200" aria-hidden="true" />
          <span>Reviewing company context</span>
        </li>
        {mayUseSpecialists ? (
          <li className="flex items-start gap-2 text-violet-200/75">
            <span aria-hidden="true">⋯</span>
            <span>May run specialist analysis when relevant</span>
          </li>
        ) : null}
        <li className="flex items-start gap-2 text-violet-200/75">
          <span aria-hidden="true">⋯</span>
          <span>Preparing grounded recommendation</span>
        </li>
      </ul>
      <p className="mt-3 text-xs text-violet-200/60">
        This can take a moment while Forge reviews your objective and Company Brain.
      </p>
    </div>
  );
}
