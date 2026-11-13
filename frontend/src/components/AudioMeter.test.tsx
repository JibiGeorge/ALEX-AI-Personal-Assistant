import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AudioMeter, dbToPercent, formatDb } from "./AudioMeter";

describe("AudioMeter Component", () => {
  afterEach(cleanup);

  it("calculates dbToPercent accurately across audio range", () => {
    expect(dbToPercent(-60)).toBe(0);
    expect(dbToPercent(-70)).toBe(0);
    expect(dbToPercent(0)).toBe(100);
    expect(dbToPercent(10)).toBe(100);
    expect(dbToPercent(-30)).toBe(50);
    expect(dbToPercent(-12)).toBe(80);
  });

  it("formats decibel readouts properly", () => {
    expect(formatDb(-60)).toBe("-∞ dB");
    expect(formatDb(-59.8)).toBe("-59.8 dB");
    expect(formatDb(-12.4)).toBe("-12.4 dB");
    expect(formatDb(0)).toBe("0.0 dB");
  });

  it("renders in standby mode when inactive", () => {
    render(
      <AudioMeter
        rmsDb={-60}
        peakDb={-60}
        active={false}
        label="Test Microphone"
      />,
    );

    expect(screen.getByText("STANDBY")).toBeInTheDocument();
    expect(screen.getAllByText(/RMS: -∞ dB/i).length).toBeGreaterThan(0);
    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "-60");
    expect(meter).toHaveAttribute("aria-valuetext", "Inactive");
    expect(screen.queryByTestId("audio-meter-peak")).toBeNull();
  });

  it("renders live levels and peak tick when active", () => {
    render(
      <AudioMeter
        rmsDb={-18.5}
        peakDb={-10.2}
        active={true}
        label="Test Microphone"
      />,
    );

    expect(screen.getByText("LIVE")).toBeInTheDocument();
    expect(screen.getByText(/RMS: -18.5 dB/i)).toBeInTheDocument();
    expect(screen.getByText(/Peak: -10.2 dB/i)).toBeInTheDocument();

    const fill = screen.getByTestId("audio-meter-fill");
    expect(fill).toHaveStyle({ width: `${dbToPercent(-18.5)}%` });

    const peak = screen.getByTestId("audio-meter-peak");
    expect(peak).toBeInTheDocument();
  });

  it("changes color to amber and red near clipping threshold", () => {
    const { rerender } = render(
      <AudioMeter rmsDb={-8} peakDb={-5} active={true} />,
    );
    let fill = screen.getByTestId("audio-meter-fill");
    expect(fill).toHaveStyle({ backgroundColor: "rgb(246, 173, 85)" }); // Amber

    rerender(<AudioMeter rmsDb={-1.5} peakDb={0} active={true} />);
    fill = screen.getByTestId("audio-meter-fill");
    expect(fill).toHaveStyle({ backgroundColor: "rgb(252, 129, 129)" }); // Red
  });

  it("calls onToggleActive when button is clicked", () => {
    const onToggle = vi.fn();
    render(
      <AudioMeter
        rmsDb={-60}
        peakDb={-60}
        active={false}
        onToggleActive={onToggle}
      />,
    );

    const button = screen.getByRole("button", { name: "Start live monitor" });
    fireEvent.click(button);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});

