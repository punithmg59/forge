"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { TaskFilters } from "@/components/tasks/TaskFilters";
import { TaskListItem } from "@/components/tasks/TaskListItem";
import { listFounderTasks, listObjectives } from "@/lib/api";
import { mapTaskApiError } from "@/lib/tasks";
import {
  computeTaskCounts,
  derivePriorityOptions,
  enrichTasksWithObjectives,
  filterWorkspaceTasks,
  groupWorkspaceTasks,
  hasActiveFilters,
  sortWorkspaceTasks,
  type SortOption,
  type StatusFilterValue,
  type WorkspaceFilters,
} from "@/lib/task-workspace";

const DEFAULT_FILTERS: WorkspaceFilters = {
  search: "",
  status: "all",
  priority: "all",
  sort: "attention",
};

type FounderTaskWorkspaceProps = {
  companyId: string;
};

export function FounderTaskWorkspace({ companyId }: FounderTaskWorkspaceProps) {
  const [tasks, setTasks] = useState<Awaited<ReturnType<typeof enrichTasksWithObjectives>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<WorkspaceFilters>(DEFAULT_FILTERS);

  const loadWorkspace = useCallback(async () => {
    const requestedCompanyId = companyId;
    setLoading(true);
    setError(null);
    setTasks([]);
    setFilters(DEFAULT_FILTERS);
    try {
      const [taskResponse, objectiveResponse] = await Promise.all([
        listFounderTasks(requestedCompanyId),
        listObjectives(requestedCompanyId),
      ]);
      if (requestedCompanyId !== companyId) {
        return;
      }
      setTasks(
        enrichTasksWithObjectives(taskResponse.tasks, objectiveResponse.objectives),
      );
    } catch (err) {
      if (requestedCompanyId !== companyId) {
        return;
      }
      setError(mapTaskApiError(err, "Unable to load founder tasks."));
    } finally {
      if (requestedCompanyId === companyId) {
        setLoading(false);
      }
    }
  }, [companyId]);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  const counts = useMemo(() => computeTaskCounts(tasks), [tasks]);
  const priorityOptions = useMemo(() => derivePriorityOptions(tasks), [tasks]);

  const filteredTasks = useMemo(() => {
    const filtered = filterWorkspaceTasks(tasks, filters);
    return sortWorkspaceTasks(filtered, filters.sort);
  }, [tasks, filters]);

  const groups = useMemo(() => groupWorkspaceTasks(filteredTasks), [filteredTasks]);
  const filtersActive = hasActiveFilters(filters);
  const searchOnly = filters.search.trim() !== "" && filters.status === "all" && filters.priority === "all";

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading founder tasks">
        <div className="task-workspace-skeleton h-10 w-full max-w-md" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="task-workspace-skeleton h-10" />
          <div className="task-workspace-skeleton h-10" />
          <div className="task-workspace-skeleton h-10" />
        </div>
        <div className="space-y-3">
          <div className="task-workspace-skeleton h-28" />
          <div className="task-workspace-skeleton h-28" />
          <div className="task-workspace-skeleton h-28" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-400/20 bg-red-500/10 p-6">
        <p className="text-sm text-red-100">{error}</p>
        <button
          type="button"
          className="forge-button-secondary mt-4"
          onClick={() => void loadWorkspace()}
        >
          Retry
        </button>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="rounded-xl border border-white/8 bg-white/3 p-8 text-center">
        <p className="text-white/80">No founder tasks yet.</p>
        <p className="mt-2 text-sm text-white/50">
          Approved Forge recommendations can appear here as executable tasks.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <TaskFilters
        search={filters.search}
        status={filters.status}
        priority={filters.priority}
        sort={filters.sort}
        priorityOptions={priorityOptions}
        onSearchChange={(value) => setFilters((current) => ({ ...current, search: value }))}
        onStatusChange={(value) => setFilters((current) => ({ ...current, status: value }))}
        onPriorityChange={(value) => setFilters((current) => ({ ...current, priority: value }))}
        onSortChange={(value) => setFilters((current) => ({ ...current, sort: value }))}
        onClearFilters={clearFilters}
        hasActiveFilters={filtersActive}
      />

      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
        <span>Needs attention: {counts.needs_attention}</span>
        <span>In progress: {counts.in_progress}</span>
        <span>Upcoming: {counts.upcoming}</span>
        <span>Completed: {counts.completed}</span>
      </div>

      {filteredTasks.length === 0 ? (
        <div className="rounded-xl border border-white/8 bg-white/3 p-6 text-center">
          <p className="text-white/75">
            {searchOnly
              ? "No tasks match your search."
              : "No tasks match the current filters."}
          </p>
          <button
            type="button"
            className="forge-button-secondary mt-4"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => (
            <section key={group.key} aria-labelledby={`task-group-${group.key}`}>
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2
                  id={`task-group-${group.key}`}
                  className="text-sm font-medium uppercase tracking-wide text-white/50"
                >
                  {group.label}
                </h2>
                <span className="text-xs text-white/35">{group.tasks.length}</span>
              </div>
              <ul className="space-y-3">
                {group.tasks.map((task) => (
                  <li key={task.id}>
                    <TaskListItem task={task} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
