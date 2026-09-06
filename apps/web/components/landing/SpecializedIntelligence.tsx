export function SpecializedIntelligence() {
  return (
    <section id="intelligence" className="py-24 md:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            One company context. Specialized intelligence.
          </h2>
        </div>

        {/* Two premium cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <SpecialistCard
            title="Customer & Growth"
            description="Understand customers, acquisition, retention, pricing, discovery, and growth opportunities using your company's own context."
            icon="🎯"
          />
          <SpecialistCard
            title="Product"
            description="Reason about roadmap, features, prioritization, UX, quality, and product strategy using the same company context."
            icon="📦"
          />
        </div>

        {/* Key message */}
        <div className="text-center">
          <div className="inline-flex items-center gap-3 px-6 py-4 rounded-xl border border-violet-500/20 bg-violet-500/5">
            <span className="text-2xl">🧠</span>
            <span className="text-lg font-medium text-white">
              Same Brain. Different expertise.
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SpecialistCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="glass-card p-8 hover:border-violet-500/30 transition-colors">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-2xl font-semibold text-white mb-4">{title}</h3>
      <p className="text-base text-white/60 leading-relaxed">{description}</p>
    </div>
  );
}
