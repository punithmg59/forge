import type { ObjectiveTaskDetail } from "@/lib/api";
import { formatTaskTimestamp } from "@/lib/tasks";

export function TaskExecutionResultSection({ task }: { task: ObjectiveTaskDetail }) {
  const result = task.result;
  if (!result) {
    return null;
  }

  return (
    <section className="glass-card p-6" aria-labelledby="execution-result-heading">
      <p className="forge-label">Execution result</p>
      <h2 id="execution-result-heading" className="text-base font-medium text-white">
        Result
      </h2>
      <div className="mt-3 space-y-4 text-sm">
        <div>
          <p className="text-white/45">Summary</p>
          <p className="mt-1 text-white/80 whitespace-pre-wrap">{result.summary}</p>
        </div>
        {result.metrics && Object.keys(result.metrics).length > 0 ? (
          <div>
            <p className="text-white/45">Metrics</p>
            <table className="mt-2 w-full text-left text-sm">
              <thead>
                <tr className="text-white/45">
                  <th className="pb-2 pr-4">Metric</th>
                  <th className="pb-2">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.metrics).map(([key, value]) => (
                  <tr key={key} className="border-t border-white/6">
                    <td className="py-2 pr-4 text-white/70">{key}</td>
                    <td className="py-2 text-white/80">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {result.notes ? (
          <div>
            <p className="text-white/45">Notes</p>
            <p className="mt-1 text-white/80 whitespace-pre-wrap">{result.notes}</p>
          </div>
        ) : null}
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-white/45">Completed at</p>
            <p className="mt-1 text-white/75">{formatTaskTimestamp(result.completed_at)}</p>
          </div>
          {result.completed_by ? (
            <div>
              <p className="text-white/45">Completed by</p>
              <p className="mt-1 text-white/75">Founder user</p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
