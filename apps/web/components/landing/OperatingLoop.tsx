export function OperatingLoop() {
  return (
    <section id="how-it-works" className="py-24 md:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Your company gets smarter as it operates.
          </h2>
        </div>

        {/* Operating loop diagram */}
        <div className="glass-card p-8 md:p-12">
          <div className="flex flex-col gap-4">
            {/* Horizontal flow */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 overflow-x-auto pb-4 md:pb-0">
              <LoopStep number="01" label="CONTEXT" description="Your objectives, knowledge, decisions, evidence, and constraints." />
              <Arrow />
              <LoopStep number="02" label="REASONING" description="Forge analyzes the company's actual context." />
              <Arrow />
              <LoopStep number="03" label="RECOMMENDATION" description="AI proposes a grounded next action." />
            </div>

            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 overflow-x-auto pb-4 md:pb-0">
              <LoopStep number="04" label="APPROVAL" description="You decide what should happen." />
              <Arrow />
              <LoopStep number="05" label="EXECUTION" description="Approved plans run through controlled execution." />
              <Arrow />
              <LoopStep number="06" label="EVIDENCE" description="The outcome becomes observable evidence." />
            </div>

            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 overflow-x-auto">
              <LoopStep number="07" label="LEARNING" description="Useful knowledge feeds the Company Brain." />
              <Arrow />
              <div className="flex-1 flex items-center justify-center min-w-[100px]">
                <div className="text-xs text-violet-300 font-mono">
                  ← Loop closes →
                </div>
              </div>
              <Arrow />
              <LoopStep number="01" label="CONTEXT" description="Your objectives, knowledge, decisions, evidence, and constraints." />
            </div>
          </div>
        </div>

        {/* Key differentiator note */}
        <div className="mt-12 text-center">
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            This continuous learning loop is what makes Forge different from traditional AI assistants. Your company doesn't just respond to questions—it gets smarter with every decision and execution.
          </p>
        </div>
      </div>
    </section>
  );
}

function LoopStep({ number, label, description }: { number: string; label: string; description: string }) {
  return (
    <div className="flex-1 min-w-[160px] max-w-[200px]">
      <div className="border border-violet-500/20 bg-violet-500/5 rounded-lg p-4">
        <div className="text-xs font-mono text-violet-400 mb-2">{number}</div>
        <div className="text-sm font-semibold text-white mb-2">{label}</div>
        <div className="text-xs text-white/60 leading-relaxed">{description}</div>
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="hidden md:flex items-center justify-center text-violet-400/40 shrink-0">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
