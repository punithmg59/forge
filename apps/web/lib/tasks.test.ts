import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import {
  canBlockTask,
  canCompleteTask,
  canResumeTask,
  canStartTask,
  isTerminalTaskStatus,
  mapTaskApiError,
  parseEvidenceContent,
  taskStatusLabel,
  validateBlockedReason,
  validateCompletionForm,
} from "./tasks";

describe("task helpers", () => {
  it("maps status labels", () => {
    expect(taskStatusLabel("in_progress")).toBe("In progress");
    expect(taskStatusLabel("completed")).toBe("Completed");
  });

  it("determines execution actions by status", () => {
    expect(canStartTask("pending")).toBe(true);
    expect(canBlockTask("in_progress")).toBe(true);
    expect(canResumeTask("blocked")).toBe(true);
    expect(canCompleteTask("blocked")).toBe(true);
    expect(isTerminalTaskStatus("completed")).toBe(true);
    expect(canStartTask("completed")).toBe(false);
  });

  it("validates completion form", () => {
    expect(validateCompletionForm({
      result_summary: "",
      result_metrics: {},
      result_notes: "",
    })).toEqual({ result_summary: "Result summary is required." });

    expect(validateCompletionForm({
      result_summary: "Customers interviewed.",
      result_metrics: { count: 12 },
      result_notes: "",
    })).toEqual({});
  });

  it("validates blocked reason", () => {
    expect(validateBlockedReason("")).toBe("Blocked reason is required.");
    expect(validateBlockedReason("Waiting for access.")).toBeNull();
  });

  it("parses evidence JSON content", () => {
    const parsed = parseEvidenceContent(
      JSON.stringify({ result_summary: "Done.", result_metrics: { n: 1 } }),
    );
    expect(parsed?.result_summary).toBe("Done.");
  });

  it("maps API errors safely", () => {
    expect(mapTaskApiError(new ApiError(404, "Task not found"), "fallback")).toBe(
      "Task not found.",
    );
    expect(mapTaskApiError(new ApiError(403, "Forbidden"), "fallback")).toBe(
      "You don't have access to this task.",
    );
  });
});
