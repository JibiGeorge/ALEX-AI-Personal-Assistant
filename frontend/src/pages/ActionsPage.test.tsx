import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { alexApi } from "../services/alexApi";
import { ActionsPage } from "./ActionsPage";

vi.mock("../services/alexApi", () => ({
  alexApi: {
    listActions: vi.fn(),
    getActionHistory: vi.fn(),
    setActionEnabled: vi.fn(),
    executeAction: vi.fn(),
  },
}));

describe("ActionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(alexApi.listActions).mockResolvedValue({
      actions: [{
        action_id: "system.get_metrics",
        name: "Get system metrics",
        description: "Read live host metrics.",
        category: "system",
        parameters: { type: "object", properties: {} },
        enabled: true,
        missing_dependencies: [],
        timeout_seconds: 5,
        requires_confirmation: false,
      }],
    });
    vi.mocked(alexApi.getActionHistory).mockResolvedValue({ executions: [] });
    vi.mocked(alexApi.executeAction).mockResolvedValue({
      action_id: "system.get_metrics",
      status: "success",
      data: { cpu_percent: 5 },
      message: "Action executed successfully.",
      error: null,
      execution_time: 0.01,
    });
  });

  it("renders registered backend actions and displays actual execution results", async () => {
    render(<ActionsPage onError={vi.fn()} />);
    await screen.findByRole("heading", { name: "Get system metrics" });
    fireEvent.click(screen.getByRole("button", { name: "Execute action" }));
    await waitFor(() => expect(alexApi.executeAction).toHaveBeenCalledWith(
      "system.get_metrics",
      {},
      false,
    ));
    expect(await screen.findByText(/SUCCESS/)).toBeInTheDocument();
    expect(screen.getByText(/cpu_percent/)).toBeInTheDocument();
  });
});
