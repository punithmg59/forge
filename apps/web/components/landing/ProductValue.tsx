export function ProductValue() {
  return (
    <section id="product" className="py-24 md:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            From scattered context to coordinated execution.
          </h2>
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            Founders typically have information spread across conversations, decisions, customer feedback, tasks, documents, assumptions, experiments, and AI conversations. Forge turns that context into an operating loop.
          </p>
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <ValueCard
            number="01"
            title="Understand"
            description="Forge builds a structured view of what your company knows."
          />
          <ValueCard
            number="02"
            title="Decide"
            description="AI analyzes your context and proposes grounded next actions."
          />
          <ValueCard
            number="03"
            title="Execute"
            description="Approved plans can move through controlled execution with explicit founder authorization."
          />
          <ValueCard
            number="04"
            title="Learn"
            description="Results become evidence and learning that improve future decisions."
          />
        </div>
      </div>
    </section>
  );
}

function ValueCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="glass-card p-6 hover:border-violet-500/20 transition-colors">
      <div className="text-xs font-mono text-violet-400 mb-3">{number}</div>
      <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>
      <p className="text-sm text-white/60 leading-relaxed">{description}</p>
    </div>
  );
}
