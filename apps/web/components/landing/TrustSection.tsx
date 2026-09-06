export function TrustSection() {
  return (
    <section className="py-24 md:py-32 px-6 bg-white/[0.01]">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Designed for controlled AI operations.
          </h2>
        </div>

        {/* Trust features */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <TrustFeature
            title="Tenant Isolation"
            description="Company-scoped data and authorization."
          />
          <TrustFeature
            title="Founder Control"
            description="Consequential execution requires explicit approval."
          />
          <TrustFeature
            title="Grounded Reasoning"
            description="Recommendations are tied to available company context."
          />
          <TrustFeature
            title="Auditability"
            description="Agent activity and execution are traceable."
          />
          <TrustFeature
            title="Safe Execution"
            description="Tools operate through centralized validation and authorization boundaries."
          />
          <TrustFeature
            title="No Autonomous Mutations"
            description="Forge never modifies your data without explicit founder authorization."
          />
        </div>
      </div>
    </section>
  );
}

function TrustFeature({ title, description }: { title: string; description: string }) {
  return (
    <div className="glass-card p-6 border-white/5 hover:border-white/10 transition-colors">
      <h3 className="text-base font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-white/60 leading-relaxed">{description}</p>
    </div>
  );
}
