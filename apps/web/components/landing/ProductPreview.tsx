export function ProductPreview() {
  return (
    <section className="py-24 md:py-32 px-6 bg-white/[0.01]">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            The Forge Founder Command Center
          </h2>
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            A unified interface for company context, AI recommendations, approvals, and execution.
          </p>
        </div>

        {/* Product UI Preview */}
        <div className="glass-card p-6 md:p-8 border-violet-500/10">
          {/* Header */}
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/8">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <span className="text-amber-400 text-sm">🔥</span>
              </div>
              <span className="text-sm font-semibold tracking-widest uppercase text-white/80">
                FORGE
              </span>
            </div>
            <div className="text-xs text-white/30 font-mono">
              PREVIEW
            </div>
          </div>

          {/* Main content grid */}
          <div className="grid md:grid-cols-3 gap-4">
            {/* Current Objective */}
            <div className="border border-white/8 bg-white/[0.02] rounded-lg p-4">
              <div className="text-xs font-semibold tracking-widest uppercase text-white/40 mb-3">
                Current Objective
              </div>
              <div className="text-sm font-medium text-white mb-2">
                Validate repeatable customer acquisition.
              </div>
              <div className="text-xs text-white/50">
                Priority: High
              </div>
            </div>

            {/* Needs Attention */}
            <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-4">
              <div className="text-xs font-semibold tracking-widest uppercase text-amber-300 mb-3">
                Needs Your Attention
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span className="text-xs text-white/70">2 Pending Approvals</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  <span className="text-xs text-white/70">1 Blocked Task</span>
                </div>
              </div>
            </div>

            {/* Forge Recommendation */}
            <div className="border border-violet-500/20 bg-violet-500/5 rounded-lg p-4">
              <div className="text-xs font-semibold tracking-widest uppercase text-violet-300 mb-3">
                Forge Recommendation
              </div>
              <div className="text-sm font-medium text-white mb-2">
                Prioritize founder-led customer interviews before increasing acquisition spend.
              </div>
            </div>
          </div>

          {/* Recommendation details */}
          <div className="mt-4 border border-white/8 bg-white/[0.02] rounded-lg p-4">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-white/40 mb-1">Why</div>
                <div className="text-xs text-white/60">
                  Current objective, customer evidence, recent decisions
                </div>
              </div>
              <div>
                <div className="text-xs text-white/40 mb-1">Confidence</div>
                <div className="text-xs text-amber-300 font-medium">MEDIUM</div>
              </div>
              <div>
                <div className="text-xs text-white/40 mb-1">Sources</div>
                <div className="text-xs text-white/60">3 company records</div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-white/8">
              <div className="text-xs text-white/40 mb-2">Proposed action</div>
              <div className="text-sm text-white/80 mb-3">
                Create customer discovery task
              </div>
              <button className="text-xs px-3 py-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-200 hover:bg-violet-500/20 transition-colors">
                Review recommendation
              </button>
            </div>
          </div>
        </div>

        {/* Note */}
        <div className="mt-8 text-center">
          <p className="text-sm text-white/30 max-w-xl mx-auto">
            This is an illustrative product preview. Actual interface may vary based on your company's context and objectives.
          </p>
        </div>
      </div>
    </section>
  );
}
