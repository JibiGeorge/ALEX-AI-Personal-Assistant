import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CircularMetric } from "./CircularMetric";
import { NetworkActivityGraph } from "./NetworkActivityGraph";
import { SystemInfo } from "./SystemInfo";
import { HolographicAssistant } from "./HolographicAssistant";
import { ActivityLog } from "./ActivityLog";
import { FileUpload } from "./FileUpload";
import { CommandInput } from "./CommandInput";
import { ApplicationHeader } from "./ApplicationHeader";

describe("Futuristic Dashboard Components", () => {
  afterEach(() => {
    cleanup();
  });
  describe("CircularMetric", () => {
    it("renders metric label and formatted percentage value", () => {
      render(
        <CircularMetric
          label="CPU"
          value={42}
          unit="%"
          subText="42% LOAD"
        />
      );
      expect(screen.getByText("CPU")).toBeInTheDocument();
      expect(screen.getByText("42%")).toBeInTheDocument();
      expect(screen.getByText("42% LOAD")).toBeInTheDocument();
    });

    it("handles null value gracefully with N/A indicator", () => {
      render(
        <CircularMetric
          label="GPU"
          value={null}
          unit="%"
          subText="N/A"
        />
      );
      expect(screen.getByText("GPU")).toBeInTheDocument();
      expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
    });
  });

  describe("NetworkActivityGraph", () => {
    it("renders network transfer rate and link status", () => {
      render(<NetworkActivityGraph speedMbPerSec={2.4} />);
      expect(screen.getByText("NET")).toBeInTheDocument();
      expect(screen.getByText("2.4")).toBeInTheDocument();
      expect(screen.getByText("MB/s")).toBeInTheDocument();
      expect(screen.getByText("TX/RX LINK ACTIVE")).toBeInTheDocument();
    });

    it("displays OFFLINE when speed is null", () => {
      render(<NetworkActivityGraph speedMbPerSec={null} />);
      expect(screen.getByText("OFFLINE")).toBeInTheDocument();
    });
  });

  describe("SystemInfo", () => {
    it("renders telemetry cells and system health indicators", () => {
      render(
        <SystemInfo
          metrics={{
            cpu_percent: 15,
            memory_percent: 40,
            network_mb_per_sec: 1.0,
            operating_system: "Windows 11",
            uptime_seconds: 7200,
            process_count: 142,
            gpu_percent: null,
            temperature_c: null,
          }}
          status={{ status: "ready", name: "Alex" }}
          voiceActive={false}
          apiKeyConfigured={true}
          osShort="WIN"
          uptimeFormatted="02:00"
        />
      );
      expect(screen.getByText("UP")).toBeInTheDocument();
      expect(screen.getByText("02:00")).toBeInTheDocument();
      expect(screen.getByText("PROC")).toBeInTheDocument();
      expect(screen.getByText("142")).toBeInTheDocument();
      expect(screen.getByText("OS")).toBeInTheDocument();
      expect(screen.getByText("WIN")).toBeInTheDocument();
      expect(screen.getByText("LOCAL CORE")).toBeInTheDocument();
      expect(screen.getByText("GEMINI")).toBeInTheDocument();
      expect(screen.getAllByText("ONLINE").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("SECURE")).toBeInTheDocument();
      expect(screen.getByText("STANDBY")).toBeInTheDocument();
    });
  });

  describe("HolographicAssistant", () => {
    it("renders assistant header, 3D avatar stage, and dynamic status pill", () => {
      render(
        <HolographicAssistant
          assistantName="Alex"
          userName="Commander"
          mode="idle"
          hudStyle="face"
          booting={false}
          chatBusy={false}
          voiceActive={false}
          apiKeyConfigured={true}
          activeMedia={null}
          onCloseMedia={vi.fn()}
          onMuteMediaChange={vi.fn()}
          onPlayStateMediaChange={vi.fn()}
        />
      );
      expect(screen.getByText("WELCOME BACK, COMMANDER")).toBeInTheDocument();
      expect(screen.getAllByText("STANDING BY").length).toBeGreaterThan(0);
      expect(screen.getByText("VOICE & NEURAL MODEL READY")).toBeInTheDocument();
    });

    it("displays PROCESSING status when chat is active", () => {
      render(
        <HolographicAssistant
          assistantName="Alex"
          userName=""
          mode="thinking"
          hudStyle="face"
          booting={false}
          chatBusy={true}
          voiceActive={false}
          apiKeyConfigured={true}
          activeMedia={null}
          onCloseMedia={vi.fn()}
          onMuteMediaChange={vi.fn()}
          onPlayStateMediaChange={vi.fn()}
        />
      );
      expect(screen.getByText("AT YOUR SERVICE")).toBeInTheDocument();
      expect(screen.getAllByText("PROCESSING").length).toBeGreaterThan(0);
    });
  });

  describe("ActivityLog", () => {
    it("renders formatted log items with timestamps and kinds", () => {
      render(
        <ActivityLog
          activity={[
            { id: "1", kind: "SYS", text: "Local sidecar initialized", time: "12:00:01" },
            { id: "2", kind: "ALEX", text: "Neural synthesis online", time: "12:00:03" },
          ]}
        />
      );
      expect(screen.getByText("SYS:")).toBeInTheDocument();
      expect(screen.getByText("Local sidecar initialized")).toBeInTheDocument();
      expect(screen.getByText("ALEX:")).toBeInTheDocument();
      expect(screen.getByText("Neural synthesis online")).toBeInTheDocument();
    });
  });

  describe("FileUpload", () => {
    it("renders drag and drop prompt and screen capture trigger", () => {
      const handleCapture = vi.fn();
      render(
        <FileUpload
          selectedFile={null}
          fileBusy={false}
          screenBusy={false}
          apiKeyConfigured={true}
          metricsUnavailable={false}
          metricsError={null}
          onFileDrop={vi.fn()}
          onFileSelect={vi.fn()}
          onCaptureScreen={handleCapture}
          onRemoveFile={vi.fn()}
          formatBytes={(n) => `${n} B`}
        />
      );
      expect(screen.getByText("Drop file here or Click to Browse")).toBeInTheDocument();
      const capBtn = screen.getByRole("button", { name: "CAPTURE SCREEN" });
      fireEvent.click(capBtn);
      expect(handleCapture).toHaveBeenCalledTimes(1);
    });
  });

  describe("CommandInput", () => {
    it("submits commands and exposes mic toggle", () => {
      const handleSubmit = vi.fn((e) => e.preventDefault());
      const handleVoiceToggle = vi.fn();
      const handleChange = vi.fn();

      render(
        <CommandInput
          command="Analyze system status"
          onCommandChange={handleChange}
          onSubmit={handleSubmit}
          apiKeyConfigured={true}
          chatBusy={false}
          selectedFile={null}
          voiceActive={false}
          voiceStarting={false}
          onVoiceToggle={handleVoiceToggle}
          onVoiceInterrupt={vi.fn()}
          onOpenChat={vi.fn()}
        />
      );

      const input = screen.getByRole("textbox", { name: "Command or question" });
      expect(input).toHaveValue("Analyze system status");

      const sendBtn = screen.getByRole("button", { name: "Send command" });
      fireEvent.click(sendBtn);
      expect(handleSubmit).toHaveBeenCalledTimes(1);

      const micBtn = screen.getByRole("button", { name: "Start microphone" });
      fireEvent.click(micBtn);
      expect(handleVoiceToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe("ApplicationHeader", () => {
    it("renders branding, drawer triggers, and live clock", () => {
      const handleSetup = vi.fn();
      const handleControls = vi.fn();
      const clockDate = new Date("2026-11-06T12:00:00Z");

      render(
        <ApplicationHeader
          assistantName="Alex"
          setupMenuOpen={false}
          controlsMenuOpen={false}
          isSettingsActive={false}
          clock={clockDate}
          onOpenOverview={vi.fn()}
          onToggleSetup={handleSetup}
          onToggleControls={handleControls}
        />
      );

      expect(screen.getAllByText("ALEX").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole("button", { name: "Setup" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Controls" })).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Setup" }));
      expect(handleSetup).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByRole("button", { name: "Controls" }));
      expect(handleControls).toHaveBeenCalledTimes(1);
    });
  });
});
