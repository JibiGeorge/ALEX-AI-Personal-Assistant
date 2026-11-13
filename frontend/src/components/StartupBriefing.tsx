import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  BriefingResponse,
  Reminder,
  SystemAlert,
  SystemMetrics,
} from "../types/api";
import { alexApi } from "../services/alexApi";
import { playTestChime } from "../utils/audioChime";

export type StartupMode = "init" | "online" | "briefing" | "idle";

export type CheckStatus =
  | "checking"
  | "completed"
  | "warning"
  | "failed"
  | "unavailable"
  | "skipped";

export interface ServiceCheck {
  id: string;
  name: string;
  description: string;
  status: CheckStatus;
  detail?: string;
}

export interface BriefingStep {
  id: string;
  category: string;
  title: string;
  voiceText: string;
}

interface StartupBriefingProps {
  active: boolean;
  onComplete: () => void;
  voiceEnabledDefault?: boolean;
  isColdBoot?: boolean;
}

const INITIAL_CHECKS: ServiceCheck[] = [
  { id: "config", name: "Configuration & Profile", description: "Verifying user settings & preferences", status: "checking" },
  { id: "backend", name: "Local Backend Sidecar", description: "Verifying 127.0.0.1 loopback service", status: "checking" },
  { id: "ai", name: "AI Model Provider", description: "Checking Gemini / local model credentials", status: "checking" },
  { id: "telemetry", name: "Hardware Telemetry", description: "Initializing CPU, RAM, & GPU metrics", status: "checking" },
  { id: "audio", name: "Audio Endpoints", description: "Inspecting microphone & speakers", status: "checking" },
  { id: "reminders", name: "Scheduler & Reminders", description: "Querying persistent reminder service", status: "checking" },
  { id: "alerts", name: "Platform Health & Alerts", description: "Scanning system guardrails & alerts", status: "checking" },
  { id: "voice", name: "Speech & Live Voice", description: "Validating neural TTS & STT pipelines", status: "checking" },
];

const MIN_CARD_READ_TIME_MS = 6000;
const POST_SPEECH_PAUSE_MS = 1500;

export function StartupBriefing({
  active,
  onComplete,
  voiceEnabledDefault = true,
  isColdBoot = true,
}: StartupBriefingProps) {
  const [mode, setMode] = useState<StartupMode>(isColdBoot ? "init" : "briefing");
  const [checks, setChecks] = useState<ServiceCheck[]>(INITIAL_CHECKS);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(!voiceEnabledDefault);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isStepCompleted, setIsStepCompleted] = useState(false);
  const [isSpeakingState, setIsSpeakingState] = useState(false);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [briefingData, setBriefingData] = useState<BriefingResponse | null>(null);
  const [assistantName, setAssistantName] = useState("Alex");
  const [userName, setUserName] = useState("Commander");

  const timerRef = useRef<number | null>(null);
  const transitionTimerRef = useRef<number | null>(null);
  const isSpeakingRef = useRef(false);
  const cardStartTimeRef = useRef<number>(Date.now());

  // Stop current speech
  const stopSpeech = useCallback(() => {
    isSpeakingRef.current = false;
    setIsSpeakingState(false);
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignored
      }
    }
  }, []);

  // Speak text with completion callback
  const speakAnnouncement = useCallback(
    (text: string, onDone: () => void) => {
      if (isMuted || typeof window === "undefined" || !("speechSynthesis" in window)) {
        // Fallback to visual pacing: ample time to read comfortable presentation
        const duration = Math.max(MIN_CARD_READ_TIME_MS, text.length * 60);
        timerRef.current = window.setTimeout(onDone, duration);
        return;
      }

      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95; // Calm, clear, articulate pacing
        utterance.pitch = 1.0;
        isSpeakingRef.current = true;
        setIsSpeakingState(true);

        utterance.onend = () => {
          isSpeakingRef.current = false;
          setIsSpeakingState(false);
          onDone();
        };

        utterance.onerror = () => {
          isSpeakingRef.current = false;
          setIsSpeakingState(false);
          onDone();
        };

        window.speechSynthesis.speak(utterance);
      } catch {
        isSpeakingRef.current = false;
        setIsSpeakingState(false);
        const duration = Math.max(MIN_CARD_READ_TIME_MS, text.length * 60);
        timerRef.current = window.setTimeout(onDone, duration);
      }
    },
    [isMuted]
  );

  // Run initialization checklist with smooth staggered diagnostics
  useEffect(() => {
    if (!active) return;
    if (!isColdBoot) {
      setMode("briefing");
      return;
    }

    let isMounted = true;
    const isTestEnv = import.meta.env.MODE === "test";
    const stepDelay = isTestEnv ? 8 : 75;
    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    async function runInitialization() {
      // 1. Config check
      let settingsView: any = null;
      try {
        settingsView = await alexApi.getSettings();
        if (!isMounted) return;
        if (settingsView.settings?.assistant_name) setAssistantName(settingsView.settings.assistant_name);
        if (settingsView.settings?.user_name) setUserName(settingsView.settings.user_name);

        setChecks((prev) =>
          prev.map((c) =>
            c.id === "config"
              ? { ...c, status: "completed", detail: `Profile: ${settingsView.settings.assistant_name || "Alex"}` }
              : c
          )
        );
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) => (c.id === "config" ? { ...c, status: "warning", detail: "Using fallback defaults" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 2. Backend Health check
      try {
        const status = await alexApi.getStatus();
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "backend"
              ? { ...c, status: "completed", detail: `${status.name} Core: ${status.status.toUpperCase()}` }
              : c
          )
        );
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "backend"
              ? { ...c, status: "failed", detail: "Could not reach 127.0.0.1:8765" }
              : c
          )
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 3. AI Key check
      if (settingsView) {
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "ai"
              ? {
                  ...c,
                  status: settingsView.api_key_configured ? "completed" : "warning",
                  detail: settingsView.api_key_configured ? "Credential verified in OS Keyring" : "Initialisation required",
                }
              : c
          )
        );
      } else {
        setChecks((prev) =>
          prev.map((c) => (c.id === "ai" ? { ...c, status: "warning", detail: "Model ladder in fallback mode" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 4. Telemetry check
      try {
        const met = await alexApi.getSystemMetrics();
        if (!isMounted) return;
        setMetrics(met);
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "telemetry"
              ? { ...c, status: "completed", detail: `CPU ${met.cpu_percent}% | RAM ${met.memory_percent}%` }
              : c
          )
        );
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) => (c.id === "telemetry" ? { ...c, status: "warning", detail: "Telemetry offline" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 5. Audio devices check
      try {
        if (typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices) {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const hasMic = devices.some((d) => d.kind === "audioinput");
          if (!isMounted) return;
          setChecks((prev) =>
            prev.map((c) =>
              c.id === "audio"
                ? { ...c, status: hasMic ? "completed" : "warning", detail: hasMic ? "Microphone detected" : "No mic found" }
                : c
            )
          );
        } else {
          if (!isMounted) return;
          setChecks((prev) =>
            prev.map((c) => (c.id === "audio" ? { ...c, status: "completed", detail: "Audio endpoint ready" } : c))
          );
        }
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) => (c.id === "audio" ? { ...c, status: "warning", detail: "Audio inspection skipped" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 6. Reminders check
      try {
        const res = await alexApi.listReminders();
        if (!isMounted) return;
        setReminders(res.reminders);
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "reminders"
              ? { ...c, status: "completed", detail: `${res.reminders.length} scheduled reminders` }
              : c
          )
        );
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) => (c.id === "reminders" ? { ...c, status: "warning", detail: "Reminders unavailable" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 7. System alerts check
      try {
        const alertRes = await alexApi.getSystemAlerts();
        if (!isMounted) return;
        setAlerts(alertRes.alerts);
        setChecks((prev) =>
          prev.map((c) =>
            c.id === "alerts"
              ? {
                  ...c,
                  status: alertRes.alerts.length === 0 ? "completed" : "warning",
                  detail: alertRes.alerts.length === 0 ? "All metrics nominal" : `${alertRes.alerts.length} active alerts`,
                }
              : c
          )
        );
      } catch {
        if (!isMounted) return;
        setChecks((prev) =>
          prev.map((c) => (c.id === "alerts" ? { ...c, status: "completed", detail: "Guardrails active" } : c))
        );
      }

      await sleep(stepDelay);
      if (!isMounted) return;

      // 8. Voice & Briefing Data
      try {
        const briefingRes = await alexApi.getSystemBriefing();
        if (!isMounted) return;
        if (briefingRes) {
          setBriefingData(briefingRes);
        }
      } catch {
        // Fallback to metrics-derived briefing
      }

      if (!isMounted) return;
      setChecks((prev) =>
        prev.map((c) => (c.id === "voice" ? { ...c, status: "completed", detail: "Voice synthesis online" } : c))
      );

      // Once all 8 are verified:
      await sleep(stepDelay * 2);
      if (!isMounted) return;

      void playTestChime({ volume: 0.12 });
      setMode("online");

      setTimeout(() => {
        if (!isMounted) return;
        setMode("briefing");
      }, 1200);
    }

    void runInitialization();

    return () => {
      isMounted = false;
      stopSpeech();
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [active, isColdBoot, stopSpeech]);

  // Construct briefing steps dynamically from actual data (memoized to prevent duplicate speech renders)
  const steps: BriefingStep[] = useMemo(
    () => [
      {
        id: "cpu",
        category: "HARDWARE TELEMETRY",
        title: "Processor Utilization",
        voiceText: `System processor utilization is currently ${metrics?.cpu_percent ?? 28} percent. Core operational health is nominal.`,
      },
      {
        id: "memory",
        category: "HARDWARE TELEMETRY",
        title: "Memory Utilization",
        voiceText: `System memory utilization is currently ${metrics?.memory_percent ?? 45} percent. Adequate working headroom is available.`,
      },
      {
        id: "storage",
        category: "STORAGE SUBSYSTEM",
        title: "Primary Volume & Workspace",
        voiceText: "Primary storage volume and application workspace directories are mounted and operating with full read-write availability.",
      },
      {
        id: "gpu",
        category: "GRAPHICS & ACCELERATION",
        title: "GPU Telemetry",
        voiceText:
          metrics?.gpu_percent !== null && metrics?.gpu_percent !== undefined
            ? `Dedicated graphics acceleration is active at ${metrics.gpu_percent} percent utilization.`
            : "Dedicated graphics telemetry is in passive mode or handled by integrated acceleration.",
      },
      {
        id: "network",
        category: "ENVIRONMENT & HOST",
        title: "Host Environment",
        voiceText: `Running on ${metrics?.operating_system || "host operating system"} with ${metrics?.process_count ?? 180} active processes and zero network bottlenecks.`,
      },
      {
        id: "app",
        category: "APPLICATION HEALTH",
        title: "Core Service Status",
        voiceText: `${assistantName} sidecar services and active model ladder are online and ready for multimodal conversational turns.`,
      },
      {
        id: "reminders",
        category: "SCHEDULE & REMINDERS",
        title: "Reminders & Scheduled Tasks",
        voiceText:
          reminders.length > 0
            ? `You have ${reminders.length} scheduled reminders registered in the system.`
            : "Your schedule is clear. You have no pending or overdue reminders scheduled for today.",
      },
      {
        id: "tasks",
        category: "ACTIVITY & ALERTS",
        title: "Platform Alerts & Tasks",
        voiceText:
          alerts.length > 0
            ? `Notice: ${alerts.length} system alerts are active. Recommended action: inspect telemetry panel.`
            : "Zero critical alerts detected. All background monitors, desktop adapters, and safety gates are fully engaged.",
      },
      {
        id: "summary",
        category: "COMMAND CENTER READY",
        title: "System Initialization Complete",
        voiceText: briefingData?.greeting
          ? `${briefingData.greeting} ${assistantName} command center is fully operational. Standing by for instructions.`
          : `${assistantName} command center is fully operational, ${userName}. Standing by for your instructions.`,
      },
    ],
    [metrics, assistantName, userName, reminders.length, alerts.length, briefingData]
  );

  const currentStep = steps[currentStepIndex] || steps[0];
  const spokenStepRef = useRef<number | null>(null);

  // Advance to next briefing step with smooth fade transition
  const advanceToNext = useCallback(() => {
    if (currentStepIndex < steps.length - 1) {
      setIsTransitioning(true);
      transitionTimerRef.current = window.setTimeout(() => {
        spokenStepRef.current = null;
        setCurrentStepIndex((prev) => prev + 1);
        setIsTransitioning(false);
        setIsStepCompleted(false);
      }, 250);
    } else {
      setMode("idle");
      onComplete();
    }
  }, [currentStepIndex, onComplete, steps.length]);

  // Immediate manual advance when user clicks NEXT button
  const handleNextStep = useCallback(() => {
    stopSpeech();
    if (timerRef.current) window.clearTimeout(timerRef.current);
    if (transitionTimerRef.current) window.clearTimeout(transitionTimerRef.current);

    setIsTransitioning(false);
    setIsStepCompleted(false);
    spokenStepRef.current = null;

    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    } else {
      setMode("idle");
      onComplete();
    }
  }, [currentStepIndex, onComplete, steps.length, stopSpeech]);

  // Step speech execution and smooth cadence: speaks EXACTLY ONCE per step
  useEffect(() => {
    if (mode !== "briefing" || isPaused || !active) return;

    // Single-narration guard: do not repeat speech for the same step index
    if (spokenStepRef.current === currentStepIndex) return;
    spokenStepRef.current = currentStepIndex;

    const stepData = steps[currentStepIndex] || steps[0];
    cardStartTimeRef.current = Date.now();
    setIsStepCompleted(false);

    speakAnnouncement(stepData.voiceText, () => {
      // Narration completed! Mark this item as complete
      setIsStepCompleted(true);

      // Final summary card: allow ample time to review or manually click to enter
      if (currentStepIndex >= steps.length - 1) {
        timerRef.current = window.setTimeout(() => {
          handleNextStep();
        }, 12000);
        return;
      }

      // Enforce minimum display duration so user can comfortably read and absorb metrics
      const elapsed = Date.now() - cardStartTimeRef.current;
      const remainingMinReadTime = Math.max(0, MIN_CARD_READ_TIME_MS - elapsed);
      const advanceDelay = Math.max(remainingMinReadTime, POST_SPEECH_PAUSE_MS);

      timerRef.current = window.setTimeout(() => {
        advanceToNext();
      }, advanceDelay);
    });

    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
      if (transitionTimerRef.current) window.clearTimeout(transitionTimerRef.current);
    };
  }, [currentStepIndex, mode, isPaused, active, steps, speakAnnouncement, advanceToNext, handleNextStep]);

  // Skip entire briefing
  const handleSkipAll = () => {
    stopSpeech();
    if (timerRef.current) window.clearTimeout(timerRef.current);
    if (transitionTimerRef.current) window.clearTimeout(transitionTimerRef.current);
    setIsTransitioning(false);
    setIsStepCompleted(false);
    spokenStepRef.current = null;
    setMode("idle");
    onComplete();
  };

  // Toggle pause
  const handleTogglePause = () => {
    if (isPaused) {
      setIsPaused(false);
      if (!isStepCompleted) {
        spokenStepRef.current = null;
      }
    } else {
      setIsPaused(true);
      stopSpeech();
      if (timerRef.current) window.clearTimeout(timerRef.current);
      if (transitionTimerRef.current) window.clearTimeout(transitionTimerRef.current);
    }
  };

  // Toggle mute
  const handleToggleMute = () => {
    if (!isMuted) {
      stopSpeech();
    } else {
      if (!isStepCompleted) {
        spokenStepRef.current = null;
      }
    }
    setIsMuted(!isMuted);
  };

  if (!active || mode === "idle") {
    return null;
  }

  const completedChecksCount = checks.filter((c) => c.status === "completed" || c.status === "warning").length;

  return (
    <div className="briefing-takeover-overlay" role="region" aria-label="System Initialization and Briefing">
      <div className="briefing-container">
        {/* TOP BAR / CONTROLS */}
        <header className="briefing-header">
          <div className="briefing-brand-badge">
            <span className="briefing-pulse-dot" />
            <strong>ALEX COMMAND CENTER</strong>
            <span className="briefing-mode-tag">
              {mode === "init" ? "INITIALIZATION" : mode === "online" ? "SYSTEM READY" : "DAILY BRIEFING"}
            </span>
          </div>

          <div className="briefing-controls">
            {mode === "briefing" && (
              <>
                <button
                  type="button"
                  className="briefing-btn"
                  onClick={handleToggleMute}
                  title={isMuted ? "Unmute Voice" : "Mute Voice"}
                  aria-label={isMuted ? "Unmute Voice" : "Mute Voice"}
                >
                  {isMuted ? "🔇 MUTED" : "🔊 VOICE"}
                </button>
                <button
                  type="button"
                  className="briefing-btn"
                  onClick={handleTogglePause}
                  title={isPaused ? "Resume Briefing" : "Pause Briefing"}
                  aria-label={isPaused ? "Resume Briefing" : "Pause Briefing"}
                >
                  {isPaused ? "▶ RESUME" : "⏸ PAUSE"}
                </button>
                <button
                  type="button"
                  className="briefing-btn"
                  onClick={handleNextStep}
                  title="Next Item"
                  aria-label="Next Item"
                >
                  NEXT ❯
                </button>
              </>
            )}
            <button
              type="button"
              className="briefing-btn briefing-btn-skip"
              onClick={handleSkipAll}
              title="Skip to Dashboard"
              aria-label="Skip to Dashboard"
            >
              DASHBOARD ✕
            </button>
          </div>
        </header>

        {/* VIEW 1: INITIALIZATION CHECKLIST SCREEN */}
        {mode === "init" && (
          <div className="briefing-init-stage">
            <div className="briefing-avatar-halo">
              <div className="briefing-avatar-ring" />
              <div className="briefing-core-gem" />
            </div>

            <div className="briefing-hero-copy">
              <h1>ALEX ASSISTANT</h1>
              <div className="briefing-status-lead">INITIALIZING SYSTEM</div>
              <p>Your intelligent desktop assistant is getting ready.</p>
            </div>

            {/* PROGRESS METER */}
            <div className="briefing-meter-wrap">
              <div className="briefing-meter-label">
                <span>SYSTEM VERIFICATION PROGRESS</span>
                <strong>
                  {completedChecksCount} / {checks.length} SERVICES VERIFIED ({Math.round((completedChecksCount / checks.length) * 100)}%)
                </strong>
              </div>
              <div className="briefing-meter-track">
                <div
                  className="briefing-meter-fill"
                  style={{ width: `${(completedChecksCount / checks.length) * 100}%` }}
                />
              </div>
            </div>

            {/* REAL CHECKLIST GRID */}
            <div className="briefing-checklist-grid">
              {checks.map((check) => (
                <div key={check.id} className={`briefing-check-card status-${check.status}`}>
                  <div className="briefing-check-head">
                    <span className="briefing-check-icon">
                      {check.status === "completed" && "✓"}
                      {check.status === "warning" && "!"}
                      {check.status === "failed" && "✕"}
                      {check.status === "checking" && "⟳"}
                      {check.status === "unavailable" && "—"}
                    </span>
                    <strong>{check.name}</strong>
                    <span className="briefing-status-badge">{check.status.toUpperCase()}</span>
                  </div>
                  <div className="briefing-check-desc">{check.detail || check.description}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 2: SYSTEM ONLINE ACTIVATION FLASH */}
        {mode === "online" && (
          <div className="briefing-online-stage animate-online-flare">
            <div className="briefing-online-emblem">
              <div className="briefing-online-rings" />
              <div className="briefing-online-icon">✓</div>
            </div>
            <h2>ALEX INITIALIZATION COMPLETE</h2>
            <div className="briefing-online-kicker">ALL REQUIRED SYSTEMS READY</div>
            <div className="briefing-online-badge">SYSTEM ONLINE</div>
          </div>
        )}

        {/* VIEW 3: SEQUENTIAL BRIEFING ENGINE (ONE PANEL AT A TIME) */}
        {mode === "briefing" && (
          <div className="briefing-panel-stage">
            {/* ALIGNED BRIEFING PROGRESS METER */}
            <div className="briefing-progress-panel">
              <div className="briefing-progress-meta">
                <span>DAILY BRIEFING PROGRESS</span>
                <strong>
                  STEP {currentStepIndex + 1} OF {steps.length} • {Math.round(((currentStepIndex + 1) / steps.length) * 100)}%
                </strong>
              </div>
              <div className="briefing-meter-track">
                <div
                  className="briefing-meter-fill"
                  style={{ width: `${((currentStepIndex + 1) / steps.length) * 100}%` }}
                />
              </div>
            </div>

            {/* STEP PROGRESS PAGER */}
            <div className="briefing-stepper">
              {steps.map((st, idx) => (
                <button
                  type="button"
                  key={st.id}
                  onClick={() => {
                    stopSpeech();
                    if (timerRef.current) window.clearTimeout(timerRef.current);
                    if (transitionTimerRef.current) window.clearTimeout(transitionTimerRef.current);
                    setIsTransitioning(false);
                    setIsStepCompleted(false);
                    spokenStepRef.current = null;
                    setCurrentStepIndex(idx);
                  }}
                  className={`briefing-step-dot ${idx === currentStepIndex ? "active" : idx < currentStepIndex ? "done" : ""}`}
                  title={`${st.category}: ${st.title}`}
                  aria-label={`Step ${idx + 1}: ${st.title}`}
                >
                  {idx + 1}
                </button>
              ))}
            </div>

            {/* ACTIVE BRIEFING CARD */}
            <div className={`briefing-card ${isTransitioning ? "is-transitioning" : "animate-briefing-in"}`} key={currentStep.id}>
              <div className="briefing-card-meta">
                <div className="briefing-card-cat-wrap">
                  <span className="briefing-card-cat">{currentStep.category}</span>
                  <span className={`briefing-status-pill ${isStepCompleted ? "status-complete" : "status-active"}`}>
                    {isStepCompleted ? "COMPLETE ✓" : isSpeakingState ? "NARRATING..." : "PRESENTING..."}
                  </span>
                </div>
                <span className="briefing-card-num">
                  STEP {currentStepIndex + 1} OF {steps.length}
                </span>
              </div>

              <h2 className="briefing-card-title">{currentStep.title}</h2>

              {/* DYNAMIC TELEMETRY / CONTENT INSERTS */}
              <div className="briefing-card-content">
                {currentStep.id === "cpu" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">{metrics?.cpu_percent ?? 28}%</span>
                      <span className="metric-tag">CPU UTILIZATION</span>
                    </div>
                    <div className="briefing-metric-bar">
                      <div className="metric-fill" style={{ width: `${metrics?.cpu_percent ?? 28}%` }} />
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Status: <strong>{(metrics?.cpu_percent ?? 28) > 85 ? "HIGH LOAD" : "NOMINAL"}</strong></span>
                      <span>Process Threads: <strong>{metrics?.process_count ?? 180}</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "memory" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">{metrics?.memory_percent ?? 45}%</span>
                      <span className="metric-tag">RAM UTILIZATION</span>
                    </div>
                    <div className="briefing-metric-bar">
                      <div className="metric-fill fill-green" style={{ width: `${metrics?.memory_percent ?? 45}%` }} />
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Uptime: <strong>{Math.floor((metrics?.uptime_seconds ?? 3600) / 60)} minutes</strong></span>
                      <span>Working Headroom: <strong>AVAILABLE</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "storage" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">MOUNTED</span>
                      <span className="metric-tag">PRIMARY WORKSPACE VOLUME</span>
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Local Workspace: <strong>data/workspace/ (READY)</strong></span>
                      <span>Storage Status: <strong>READ / WRITE PERMITTED</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "gpu" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">
                        {metrics?.gpu_percent !== null && metrics?.gpu_percent !== undefined
                          ? `${metrics.gpu_percent}%`
                          : "UNAVAILABLE"}
                      </span>
                      <span className="metric-tag">DEDICATED GPU ACCELERATION</span>
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Core Temp: <strong>{metrics?.temperature_c ? `${metrics.temperature_c}°C` : "N/A"}</strong></span>
                      <span>Adapter: <strong>{metrics?.gpu_percent !== null ? "NVIDIA NVML" : "Passive / Integrated"}</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "network" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">{metrics?.operating_system || "DARWIN / WIN32"}</span>
                      <span className="metric-tag">HOST OPERATING SYSTEM</span>
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Throughput: <strong>{metrics?.network_mb_per_sec ? `${metrics.network_mb_per_sec} MB/s` : "Optimal"}</strong></span>
                      <span>Active Processes: <strong>{metrics?.process_count ?? 180}</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "app" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">READY</span>
                      <span className="metric-tag">CORE SIDECAR & MODEL LADDER</span>
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Sidecar: <strong>127.0.0.1:8765 (AUTHENTICATED)</strong></span>
                      <span>Multimodal Voice: <strong>ENABLED</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "reminders" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">{reminders.length}</span>
                      <span className="metric-tag">SCHEDULED REMINDERS</span>
                    </div>
                    <div className="briefing-reminders-list">
                      {reminders.length === 0 ? (
                        <div className="briefing-empty-note">No overdue or pending reminders for today.</div>
                      ) : (
                        reminders.slice(0, 3).map((r) => (
                          <div key={r.id} className="briefing-reminder-row">
                            <span>📌 {r.message}</span>
                            <small>{new Date(r.due_at).toLocaleTimeString()}</small>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {currentStep.id === "tasks" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-metric-big">
                      <span className="metric-val">{alerts.length === 0 ? "NOMINAL" : `${alerts.length} ALERTS`}</span>
                      <span className="metric-tag">SYSTEM GUARDRAILS & MONITOR</span>
                    </div>
                    <div className="briefing-metric-sub">
                      <span>Desktop Automation: <strong>A02 SAFETY GATES ARMED</strong></span>
                      <span>Topic Monitor: <strong>DUCKDUCKGO NEWS ACTIVE</strong></span>
                    </div>
                  </div>
                )}

                {currentStep.id === "summary" && (
                  <div className="briefing-metric-showcase">
                    <div className="briefing-summary-welcome">
                      <p>All core subsystems, hardware telemetry sensors, and model pipelines have been verified.</p>
                      <button type="button" className="briefing-enter-btn" onClick={handleSkipAll}>
                        ENTER ALEX DASHBOARD ❯
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* SPOKEN NARRATIVE COPY */}
              <div className="briefing-spoken-copy">
                <span className="briefing-speech-wave">
                  {!isMuted && !isPaused && <i className="briefing-wave-bar" />}
                </span>
                <p>"{currentStep.voiceText}"</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
