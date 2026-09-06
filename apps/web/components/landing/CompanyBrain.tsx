export function CompanyBrain() {
  return (
    <section id="company-brain" className="py-24 md:py-32 px-6 bg-white/[0.01]">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Your company should remember what it learns.
          </h2>
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            Every startup accumulates decisions, assumptions, evidence, experiments, and lessons. Forge gives that knowledge a place to persist and become useful again.
          </p>
        </div>

        {/* Brain flow diagram */}
        <div className="glass-card p-8 md:p-12">
          <div className="flex flex-col items-center gap-4">
            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 w-full">
              <BrainNode label="Decision" />
              <Arrow />
              <BrainNode label="Execution" />
              <Arrow />
              <BrainNode label="Evidence" />
            </div>

            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 w-full">
              <BrainNode label="Learning" />
              <Arrow />
              <BrainNode label="Company Brain" />
              <Arrow />
              <BrainNode label="Future Decision" />
            </div>
          </div>
        </div>

        {/* Note */}
        <div className="mt-12 text-center">
          <p className="text-sm text-white/40 max-w-xl mx-auto">
            The Company Brain is not perfect memory or automatic truth—it's a structured place for your company's accumulated knowledge to inform better decisions.
          </p>
        </div>
      </div>
    </section>
  );
}

function BrainNode({ label }: { label: string }) {
  return (
    <div className="flex-1 min-w-[120px] max-w-[160px]">
      <div className="border border-white/10 bg-white/[0.02] rounded-lg p-4 text-center">
        <div className="text-sm font-medium text-white/70">{label}</div>
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="hidden md:flex items-center justify-center text-white/20">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
