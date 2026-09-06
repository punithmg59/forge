export function Differentiation() {
  return (
    <section className="py-24 md:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Not another AI chat window.
          </h2>
        </div>

        {/* Comparison */}
        <div className="grid md:grid-cols-2 gap-8">
          {/* Traditional AI */}
          <div className="glass-card p-8 border-white/5">
            <div className="text-xs font-semibold tracking-widest uppercase text-white/40 mb-6">
              Traditional AI Assistant
            </div>
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-white/20" />
                <span className="text-sm text-white/60">Question</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-white/20" />
                <span className="text-sm text-white/60">Answer</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-white/20" />
                <span className="text-sm text-white/60">Conversation ends</span>
              </div>
            </div>
          </div>

          {/* Forge */}
          <div className="glass-card p-8 border-violet-500/20 bg-violet-500/5">
            <div className="text-xs font-semibold tracking-widest uppercase text-violet-300 mb-6">
              Forge
            </div>
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Company Context</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Reasoning</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Recommendation</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Founder Approval</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Execution</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Evidence</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Learning</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-white/80">Company Brain</span>
              </div>
            </div>
          </div>
        </div>

        {/* Key message */}
        <div className="mt-12 text-center">
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            Forge is an operating system that turns your company's context into decisions, controlled execution, evidence, and learning—not just a chat interface.
          </p>
        </div>
      </div>
    </section>
  );
}
