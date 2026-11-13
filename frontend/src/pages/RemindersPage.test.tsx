import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RemindersPage } from "./RemindersPage";
import { alexApi } from "../services/alexApi";
import type { Reminder } from "../types/api";

vi.mock("../services/alexApi", () => ({
  alexApi: {
    listReminders: vi.fn(),
  },
}));

describe("RemindersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates and cancels persisted reminders", async () => {
    const pending: Reminder = {
      id: "2f1e9e84-ea66-4014-a029-690c5fb6c229",
      message: "Call back",
      due_at: "2030-01-01T10:00:00Z",
      status: "pending",
    };
    vi.mocked(alexApi.listReminders)
      .mockResolvedValueOnce({ reminders: [] })
      .mockResolvedValueOnce({ reminders: [pending] })
      .mockResolvedValueOnce({ reminders: [] });
    const onCreate = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn().mockResolvedValue(undefined);
    render(<RemindersPage onCreate={onCreate} onCancel={onCancel} onError={vi.fn()} />);

    await screen.findByText("No reminders yet");
    fireEvent.change(screen.getByLabelText("Reminder"), {
      target: { value: "Call back" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Set reminder" }).closest("form")!);
    await waitFor(() => expect(onCreate).toHaveBeenCalledWith(
      "Call back",
      expect.stringMatching(/Z$/),
    ));
    await screen.findByText("Call back");

    fireEvent.click(screen.getByRole("button", { name: "Cancel reminder Call back" }));
    await waitFor(() => expect(onCancel).toHaveBeenCalledWith(pending.id));
    await screen.findByText("No reminders yet");
  });
});
