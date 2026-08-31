import type { ProvenanceNode } from "@/lib/execution-context";

export function TaskProvenance({ nodes }: { nodes: ProvenanceNode[] }) {
  return (
    <section className="glass-card p-6" aria-labelledby="provenance-heading">
      <p className="forge-label">Provenance</p>
      <h2 id="provenance-heading" className="text-base font-medium text-white">
        Operating chain
      </h2>
      <ol className="mt-4 space-y-0">
        {nodes.map((node, index) => (
          <li key={node.key} className="relative">
            <div
              className={`rounded-xl border p-4 ${
                node.available
                  ? "border-white/10 bg-white/3"
                  : "border-white/6 bg-white/[0.02]"
              }`}
            >
              <p className="text-xs font-medium uppercase tracking-wide text-white/45">
                {node.label}
              </p>
              <p
                className={`mt-1 text-sm ${
                  node.available ? "text-white/85" : "text-white/50"
                }`}
              >
                {node.title}
              </p>
              {node.detail ? (
                <p className="mt-1 text-xs text-white/45">{node.detail}</p>
              ) : null}
            </div>
            {index < nodes.length - 1 ? (
              <div className="flex justify-center py-2 text-white/30" aria-hidden="true">
                ↓
              </div>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
