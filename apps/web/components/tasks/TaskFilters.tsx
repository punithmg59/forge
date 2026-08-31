"use client";

import {
  SORT_OPTIONS,
  STATUS_FILTER_OPTIONS,
  type SortOption,
  type StatusFilterValue,
} from "@/lib/task-workspace";

type TaskFiltersProps = {
  search: string;
  status: StatusFilterValue;
  priority: string;
  sort: SortOption;
  priorityOptions: string[];
  onSearchChange: (value: string) => void;
  onStatusChange: (value: StatusFilterValue) => void;
  onPriorityChange: (value: string) => void;
  onSortChange: (value: SortOption) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
};

export function TaskFilters({
  search,
  status,
  priority,
  sort,
  priorityOptions,
  onSearchChange,
  onStatusChange,
  onPriorityChange,
  onSortChange,
  onClearFilters,
  hasActiveFilters,
}: TaskFiltersProps) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <label className="forge-label" htmlFor="task-search">Search tasks</label>
          <input
            id="task-search"
            className="forge-input mt-1"
            type="search"
            value={search}
            placeholder="Search by title, description, or objective"
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
        <div>
          <label className="forge-label" htmlFor="task-status-filter">Status</label>
          <select
            id="task-status-filter"
            className="forge-input mt-1"
            value={status}
            onChange={(event) => onStatusChange(event.target.value as StatusFilterValue)}
          >
            {STATUS_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="forge-label" htmlFor="task-priority-filter">Priority</label>
          <select
            id="task-priority-filter"
            className="forge-input mt-1"
            value={priority}
            onChange={(event) => onPriorityChange(event.target.value)}
          >
            <option value="all">All priorities</option>
            {priorityOptions.map((option) => (
              <option key={option} value={option}>
                {option.charAt(0).toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <label className="forge-label" htmlFor="task-sort">Sort</label>
          <select
            id="task-sort"
            className="forge-input mt-1 w-auto min-w-[140px]"
            value={sort}
            onChange={(event) => onSortChange(event.target.value as SortOption)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {hasActiveFilters ? (
          <button
            type="button"
            className="forge-button-secondary mt-5"
            onClick={onClearFilters}
          >
            Clear filters
          </button>
        ) : null}
      </div>
    </div>
  );
}
