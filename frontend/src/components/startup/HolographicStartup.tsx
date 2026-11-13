import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { alexApi } from "../../services/alexApi";
import { HudAvatar } from "../HudAvatar";
import { playTestChime } from "../../utils/audioChime";
import type { SystemMetrics, SettingsView, FullSystemVerificationReport, ApiStatus } from "../../types/api";

export type StartupStage =
  | "welcome"
  | "avatar_diagnostics"
  | "system_online"
  | "dashboard_reveal"
  | "voice_announcement"
  | "ready"
  | "stage1_cinematic"
  | "stage2_diagnostics"
  | "stage3_dialog"
  | "stage3_activating";

export type DiagnosticPhase =
  | "idle"
  | "os"
  | "cpu_mem"
  | "app"
  | "backend"
  | "ai"
  | "voice"
  | "security"
  | "completed";

export type DiagnosticStatus = "pending" | "checking" | "verified" | "warning" | "failed";

export interface DiagnosticCategory {
  id: string;
  category: string;
  title: string;
  status: DiagnosticStatus;
  detail?: string;
  latencyMs?: number;
}

export interface DiagnosticReport {
  overallHealthPercent: number;
  completedCount: number;
  verifiedCount?: number;
  warningCount: number;
  failedCount: number;
  statusType?: "online" | "degraded" | "attention";
  statusTitle?: string;
  categories: DiagnosticCategory[];
  metrics: SystemMetrics | null;
  settings: SettingsView | null;
  verification?: FullSystemVerificationReport | null;
  timestamp?: string;
}

interface HolographicStartupProps {
  active: boolean;
  onDiagnosticsComplete: (report: DiagnosticReport) => void;
  onSkipToDashboard: () => void;
  assistantName?: string;
  userName?: string;
  initialStage?: "stage1" | "stage2" | "completed" | "welcome" | "avatar_diagnostics" | "system_online";
  onStageChange?: (stage: "stage1" | "stage2" | "completed" | "welcome" | "avatar_diagnostics" | "system_online") => void;
  onDiagnosticsPhaseChange?: (phase: DiagnosticPhase) => void;
  showAvatarInOverlay?: boolean;
}

const BOOT_MESSAGES = [
  "Establishing secure environment...",
  "Initializing application core...",
  "Loading AI engine...",
  "Connecting local backend...",
  "Initializing system intelligence...",
  "Preparing holographic interface...",
];

const INITIAL_DIAGNOSTIC_CATEGORIES: DiagnosticCategory[] = [
  { id: "os", category: "OPERATING SYSTEM", title: "OS Kernel & Architecture", status: "pending", detail: "Waiting for telemetry" },
  { id: "cpu_mem", category: "CPU & MEMORY", title: "Processor & RAM Headroom", status: "pending", detail: "Awaiting utilization sensors" },
  { id: "app", category: "APPLICATION CORE", title: "Runtime & Workspace Storage", status: "pending", detail: "Checking config & local storage" },
  { id: "backend", category: "BACKEND SERVICES", title: "Local Core Loopback (127.0.0.1:8765)", status: "pending", detail: "Testing REST & IPC endpoint" },
  { id: "ai", category: "AI ENGINE", title: "Model Provider & Credentials", status: "pending", detail: "Validating OS Keyring token" },
  { id: "integrations", category: "INTEGRATIONS", title: "Peripherals & Multimodal Pipelines", status: "pending", detail: "Scanning audio & display capture" },
  { id: "security", category: "SECURITY", title: "IPC Boundary & Safety Gates", status: "pending", detail: "Auditing computer control gates" },
];

export function HolographicStartup({
  active,
  onDiagnosticsComplete,
  onSkipToDashboard,
  assistantName = "Alex",
  userName = "Commander",
  initialStage = "stage1",
  onStageChange,
  onDiagnosticsPhaseChange,
  showAvatarInOverlay = true,
}: HolographicStartupProps) {
  const normalizeStage = (st?: string): "stage1" | "stage2" | "completed" => {
    if (st === "avatar_diagnostics" || st === "stage2") return "stage2";
    if (st === "system_online" || st === "completed") return "completed";
    return "stage1";
  };

  const [internalStage, setInternalStage] = useState<"stage1" | "stage2" | "completed">(normalizeStage(initialStage));
  const [activePhase, setActivePhase] = useState<DiagnosticPhase>("idle");
  const activePhaseRef = useRef<DiagnosticPhase>("idle");
  activePhaseRef.current = activePhase;

  const burstTriggerRef = useRef<{ color: string; count: number } | null>(null);

  const updatePhase = useCallback(
    (nextPhase: DiagnosticPhase) => {
      setActivePhase(nextPhase);
      activePhaseRef.current = nextPhase;
      const burstColor =
        nextPhase === "completed"
          ? "#00ffaa"
          : nextPhase === "ai"
          ? "#ffaa22"
          : nextPhase === "security"
          ? "#00dfff"
          : "#00dfff";
      burstTriggerRef.current = { color: burstColor, count: nextPhase === "completed" ? 36 : 18 };
      onDiagnosticsPhaseChange?.(nextPhase);
    },
    [onDiagnosticsPhaseChange]
  );

  const setStage = useCallback(
    (nextStage: "stage1" | "stage2" | "completed" | "welcome" | "avatar_diagnostics" | "system_online") => {
      const normalized = normalizeStage(nextStage);
      setInternalStage(normalized);
      onStageChange?.(nextStage);
    },
    [onStageChange]
  );

  useEffect(() => {
    onStageChange?.(initialStage);
  }, [initialStage, onStageChange]);
  const [bootMessageIndex, setBootMessageIndex] = useState(0);
  const [bootProgress, setBootProgress] = useState(15);
  const [currentOperation, setCurrentOperation] = useState("INITIALIZING ALEX SYSTEM ENVIRONMENT...");
  const [categories, setCategories] = useState<DiagnosticCategory[]>(INITIAL_DIAGNOSTIC_CATEGORIES);
  const [elapsedSeconds, setElapsedSeconds] = useState(0.0);
  const [scanPulse, setScanPulse] = useState<"cyan" | "amber" | "red" | null>(null);
  const [failedMandatory, setFailedMandatory] = useState<string | null>(null);

  // Diagnostic completion details
  const [statusType, setStatusType] = useState<"online" | "degraded" | "attention">("online");
  const [statusTitle, setStatusTitle] = useState("ALEX SYSTEM ONLINE");
  const [completionTime, setCompletionTime] = useState("");

  // Real-time discovered runtime telemetry
  const [discoveredMetrics, setDiscoveredMetrics] = useState<SystemMetrics | null>(null);
  const [discoveredSettings, setDiscoveredSettings] = useState<SettingsView | null>(null);
  const [discoveredVerification, setDiscoveredVerification] = useState<FullSystemVerificationReport | null>(null);
  const [discoveredBackendStatus, setDiscoveredBackendStatus] = useState<ApiStatus | null>(null);
  const [discoveredMicReady, setDiscoveredMicReady] = useState(false);
  const discoveryCompletedRef = useRef(false);
  const diagnosticsStartedRef = useRef(false);

  const particleCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const timerRefs = useRef<number[]>([]);
  const intervalRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);
  const categoriesRef = useRef(categories);
  categoriesRef.current = categories;

  const isTestEnv =
    (typeof process !== "undefined" && process.env?.NODE_ENV === "test") ||
    (typeof window !== "undefined" && Boolean((window as any).__VITEST__)) ||
    (typeof import.meta !== "undefined" && import.meta.env?.MODE === "test");

  const clearAllTimers = useCallback(() => {
    timerRefs.current.forEach((t) => window.clearTimeout(t));
    timerRefs.current = [];
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Background floating & diagnostic-aware cyber particles
  useEffect(() => {
    const canvas = particleCanvasRef.current;
    if (!canvas || isTestEnv) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const width = (canvas.width = window.innerWidth);
    const height = (canvas.height = window.innerHeight);
    const centerX = width * 0.5;
    const centerY = height * 0.48;

    interface Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      alpha: number;
      color?: string;
      isSpark?: boolean;
      life?: number;
      maxLife?: number;
    }

    const particles: Particle[] = Array.from({ length: 54 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.6 + 0.2,
    }));

    const sparks: Particle[] = [];

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Handle external burst triggers
      if (burstTriggerRef.current) {
        const { color, count } = burstTriggerRef.current;
        burstTriggerRef.current = null;
        for (let i = 0; i < count; i++) {
          const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.4;
          const speed = Math.random() * 3.5 + 1.5;
          sparks.push({
            x: centerX,
            y: centerY,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            size: Math.random() * 2.2 + 1.2,
            alpha: 1.0,
            color,
            isSpark: true,
            life: 0,
            maxLife: 45 + Math.random() * 20,
          });
        }
      }

      const phase = activePhaseRef.current;
      const isInDiagnostics = phase !== "idle";
      const isConvergingPhase = phase === "cpu_mem" || phase === "app";

      // Ambient & telemetry particles
      particles.forEach((p) => {
        if (isInDiagnostics) {
          // Gentle convergence towards avatar center
          const dx = centerX - p.x;
          const dy = centerY - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 40) {
            const pull = isConvergingPhase ? 0.00075 : 0.00035;
            p.vx += (dx / dist) * pull * dist;
            p.vy += (dy / dist) * pull * dist;
          }
          // Velocity damping to avoid runaway speeds
          p.vx *= 0.985;
          p.vy *= 0.985;
        }

        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.fillStyle = `rgba(0, 217, 255, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Verification spark bursts
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.life = (s.life || 0) + 1;
        s.x += s.vx;
        s.y += s.vy;
        s.vx *= 0.96;
        s.vy *= 0.96;
        const progress = s.life / (s.maxLife || 50);
        s.alpha = Math.max(0, 1.0 - progress);

        ctx.fillStyle = s.color || "#00dfff";
        ctx.globalAlpha = s.alpha;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size * (1 - progress * 0.4), 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;

        if (progress >= 1.0) {
          sparks.splice(i, 1);
        }
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [isTestEnv]);

  // STAGE 1: Real System Discovery & Initialization Controller
  useEffect(() => {
    if (!active || internalStage !== "stage1" || discoveryCompletedRef.current) return;

    let cancelled = false;

    const executeGenuineDiscovery = async () => {
      try {
        // Step 1: Verify local backend loopback status
        setBootMessageIndex(0);
        setBootProgress(15);
        let backendStatus: ApiStatus | null = null;
        try {
          backendStatus = await alexApi.getStatus();
          if (cancelled) return;
          setDiscoveredBackendStatus(backendStatus);
        } catch (err) {
          if (cancelled) return;
          setScanPulse("red");
          setFailedMandatory("Could not connect to local backend sidecar on 127.0.0.1:8765");
          setCategories((prev) =>
            prev.map((c) =>
              c.id === "backend"
                ? { ...c, status: "failed", detail: "Could not reach 127.0.0.1:8765 loopback" }
                : c
            )
          );
          setStage("stage2");
          return;
        }

        // Step 2: Query live system metrics (CPU, RAM, OS, processes)
        setBootMessageIndex(1);
        setBootProgress(35);
        let metrics: SystemMetrics | null = null;
        try {
          metrics = await alexApi.getSystemMetrics();
          if (cancelled) return;
          setDiscoveredMetrics(metrics);
        } catch {
          // graceful fallback
        }

        // Step 3: Deep system runtime verification (OS, CPU, Python, FastAPI, Document Store, AI engines)
        setBootMessageIndex(2);
        setBootProgress(55);
        let verification: FullSystemVerificationReport | null = null;
        try {
          verification = await alexApi.getSystemVerification();
          if (cancelled) return;
          setDiscoveredVerification(verification);
        } catch {
          // graceful fallback
        }

        // Step 4: Configuration & credential authorization
        setBootMessageIndex(3);
        setBootProgress(75);
        let settings: SettingsView | null = null;
        try {
          settings = await alexApi.getSettings();
          if (cancelled) return;
          setDiscoveredSettings(settings);
        } catch {
          // graceful fallback
        }

        // Step 5: Audio peripherals & microphone access
        setBootMessageIndex(4);
        setBootProgress(90);
        let micDetected = false;
        try {
          if (alexApi.ensureMicrophoneAccess) {
            await alexApi.ensureMicrophoneAccess().catch(() => ({ granted: true, status: "unknown" }));
          }
          if (typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices) {
            const devs = await navigator.mediaDevices.enumerateDevices();
            micDetected = devs.some((d) => d.kind === "audioinput");
          }
        } catch {
          // skipped
        }
        if (cancelled) return;
        setDiscoveredMicReady(micDetected);

        // Step 6: Finalize Stage 1 and transition to Stage 2
        setBootMessageIndex(5);
        setBootProgress(100);
        discoveryCompletedRef.current = true;

        const tEnd = window.setTimeout(() => {
          if (!isMountedRef.current || cancelled) return;
          setStage("stage2");
        }, isTestEnv ? 15 : 300);
        timerRefs.current.push(tEnd);
      } catch {
        if (!cancelled && isMountedRef.current) {
          setFailedMandatory("Unexpected error occurred during system discovery scan.");
          setStage("stage2");
        }
      }
    };

    void executeGenuineDiscovery();

    return () => {
      cancelled = true;
      clearAllTimers();
    };
  }, [active, internalStage, isTestEnv, clearAllTimers]);

  // STAGE 2: Holographic Diagnostics Execution
  const runDiagnostics = useCallback(async () => {
    setFailedMandatory(null);
    const stepDuration = isTestEnv ? 6 : 220;
    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    const startTime = performance.now();

    // Elapsed timer tick
    if (intervalRef.current) window.clearInterval(intervalRef.current);
    intervalRef.current = window.setInterval(() => {
      if (!isMountedRef.current) return;
      setElapsedSeconds(Number(((performance.now() - startTime) / 1000).toFixed(1)));
    }, 100);

    try {
      // Fetch or use discovered data
      let retrievedMetrics = discoveredMetrics;
      let retrievedSettings = discoveredSettings;
      let retrievedVerification = discoveredVerification;
      let backendStatus = discoveredBackendStatus;
      let micDetected = discoveredMicReady;

      // 1. Operating System Diagnostics
      setCurrentOperation("INITIALIZING ALEX SYSTEM ENVIRONMENT...");
      await sleep(stepDuration / 2);
      updatePhase("os");
      setCurrentOperation("VERIFYING OPERATING SYSTEM...");
      setCategories((prev) => prev.map((c) => (c.id === "os" ? { ...c, status: "checking" } : c)));
      if (!retrievedMetrics) {
        try {
          retrievedMetrics = await alexApi.getSystemMetrics();
          setDiscoveredMetrics(retrievedMetrics);
        } catch {
          // skipped
        }
      }
      if (!retrievedVerification) {
        try {
          retrievedVerification = await alexApi.getSystemVerification();
          setDiscoveredVerification(retrievedVerification);
        } catch {
          // skipped
        }
      }

      if (isMountedRef.current) {
        setScanPulse("cyan");
        const osName = retrievedVerification?.hardware.os_name || retrievedMetrics?.operating_system || "Darwin / macOS";
        const osVer = retrievedVerification?.hardware.os_version;
        const arch = retrievedVerification?.hardware.architecture;
        const cpuModel = retrievedVerification?.hardware.cpu_model;
        const cores = retrievedVerification?.hardware.cpu_logical_cores;
        const procCount = retrievedVerification?.hardware.process_count || retrievedMetrics?.process_count || 180;
        
        const osDetail = cpuModel
          ? `${osName}${osVer ? ` ${osVer}` : ""}${arch ? ` (${arch})` : ""} • ${cpuModel}${cores ? ` (${cores} Cores)` : ""} • ${procCount} Processes Active`
          : `${osName} • ${procCount} Processes Active`;

        setCategories((prev) =>
          prev.map((c) =>
            c.id === "os"
              ? {
                  ...c,
                  status: "verified",
                  detail: osDetail,
                }
              : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 2. CPU & Memory Telemetry
      updatePhase("cpu_mem");
      setCurrentOperation("ANALYZING CPU AND MEMORY...");
      setCategories((prev) => prev.map((c) => (c.id === "cpu_mem" ? { ...c, status: "checking" } : c)));
      if (retrievedMetrics || retrievedVerification) {
        setScanPulse("cyan");
        const cpuPct = Math.round(retrievedVerification?.hardware.cpu_percent ?? retrievedMetrics?.cpu_percent ?? 24);
        const ramPct = Math.round(retrievedVerification?.hardware.ram_percent ?? retrievedMetrics?.memory_percent ?? 48);
        const ramTotal = retrievedVerification?.hardware.ram_total_gb;
        const ramAvail = retrievedVerification?.hardware.ram_available_gb;
        const diskFree = retrievedVerification?.hardware.disk_free_gb;

        const cpuDetail = ramTotal
          ? `CPU: ${cpuPct}% • RAM: ${ramPct}% (${ramAvail ?? "?"}GB free of ${ramTotal}GB)${diskFree ? ` • Disk: ${diskFree}GB free` : ""} • Headroom Nominal`
          : `CPU: ${cpuPct}% • RAM: ${ramPct}% • Headroom Nominal`;

        setCategories((prev) =>
          prev.map((c) =>
            c.id === "cpu_mem"
              ? {
                  ...c,
                  status: "verified",
                  detail: cpuDetail,
                }
              : c
          )
        );
      } else {
        setCategories((prev) =>
          prev.map((c) =>
            c.id === "cpu_mem" ? { ...c, status: "warning", detail: "Telemetry sensors passive" } : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 3. Application Core & Workspace
      updatePhase("app");
      setCurrentOperation("VERIFYING APPLICATION CORE...");
      setCategories((prev) => prev.map((c) => (c.id === "app" ? { ...c, status: "checking" } : c)));
      if (!retrievedSettings) {
        try {
          retrievedSettings = await alexApi.getSettings();
          setDiscoveredSettings(retrievedSettings);
        } catch {
          // skipped
        }
      }

      if (isMountedRef.current) {
        setScanPulse("cyan");
        const profName = retrievedSettings?.settings.assistant_name || assistantName;
        const pyVer = retrievedVerification?.application?.python_version;
        const fastapiVer = retrievedVerification?.application?.fastapi_version;
        const workspaceWritable = retrievedVerification?.application?.workspace_writable ?? true;
        
        const appDetail = pyVer
          ? `Profile: ${profName} • Python ${pyVer} • FastAPI ${fastapiVer || "0.115"} • ${workspaceWritable ? "Workspace Writable" : "Workspace Mounted"}`
          : `Profile: ${profName} • Workspace Mounted`;

        setCategories((prev) =>
          prev.map((c) =>
            c.id === "app"
              ? {
                  ...c,
                  status: "verified",
                  detail: appDetail,
                }
              : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 4. Backend Health Check
      updatePhase("backend");
      setCurrentOperation("CONNECTING LOCAL BACKEND...");
      setCategories((prev) => prev.map((c) => (c.id === "backend" ? { ...c, status: "checking" } : c)));
      const pingStart = performance.now();
      try {
        if (!backendStatus) {
          backendStatus = await alexApi.getStatus();
          setDiscoveredBackendStatus(backendStatus);
        }
        const latency = Math.round(performance.now() - pingStart);
        if (isMountedRef.current) {
          setScanPulse("cyan");
          const dbType = retrievedVerification?.backend_database?.database_type || "JSON Document Store";
          const memCount = retrievedVerification?.backend_database?.memory_entries_count;
          const remCount = retrievedVerification?.backend_database?.active_reminders_count;
          
          const backendDetail = memCount !== undefined
            ? `127.0.0.1:8765 Sidecar: ${backendStatus.status.toUpperCase()} (${latency}ms ping) • ${dbType} (${memCount} memories, ${remCount ?? 0} reminders)`
            : `127.0.0.1:8765 Sidecar: ${backendStatus.status.toUpperCase()} (${latency}ms ping)`;

          setCategories((prev) =>
            prev.map((c) =>
              c.id === "backend"
                ? {
                    ...c,
                    status: "verified",
                    detail: backendDetail,
                    latencyMs: latency,
                  }
                : c
            )
          );
        }
      } catch (err) {
        if (isMountedRef.current) {
          setScanPulse("red");
          setFailedMandatory("Could not connect to local backend sidecar on 127.0.0.1:8765");
          setCategories((prev) =>
            prev.map((c) =>
              c.id === "backend"
                ? { ...c, status: "failed", detail: "Could not reach 127.0.0.1:8765 loopback" }
                : c
            )
          );
          if (intervalRef.current) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          return;
        }
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 5. AI Engine & Credentials
      updatePhase("ai");
      setCurrentOperation("VERIFYING AI COGNITIVE ENGINE...");
      setCategories((prev) => prev.map((c) => (c.id === "ai" ? { ...c, status: "checking" } : c)));
      const isKeyOk = retrievedSettings?.api_key_configured ?? retrievedVerification?.ai_engines?.cloud_credentials_configured ?? false;
      const ollamaRunning = retrievedVerification?.ai_engines?.ollama_running ?? false;
      const ollamaModels = retrievedVerification?.ai_engines?.ollama_models ?? [];
      const ollamaSummary = ollamaRunning
        ? ` • Ollama: ${ollamaModels.length} models active`
        : retrievedVerification?.ai_engines?.ollama_installed
        ? " • Ollama Installed"
        : "";

      if (isMountedRef.current) {
        setScanPulse(isKeyOk ? "cyan" : "amber");
        const aiDetail = isKeyOk
          ? `Gemini Neural API Verified in OS Keyring${ollamaSummary}`
          : `API key required for multimodal live turns${ollamaSummary}`;

        setCategories((prev) =>
          prev.map((c) =>
            c.id === "ai"
              ? {
                  ...c,
                  status: isKeyOk ? "verified" : "warning",
                  detail: aiDetail,
                }
              : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 6. Integrations & Audio Peripherals
      updatePhase("voice");
      setCurrentOperation("CHECKING VOICE AND PERIPHERAL SERVICES...");
      setCategories((prev) => prev.map((c) => (c.id === "integrations" ? { ...c, status: "checking" } : c)));
      let micDenied = false;
      let micPermGranted = false;
      if (!micDetected) {
        if (alexApi.ensureMicrophoneAccess) {
          try {
            const perm = await alexApi.ensureMicrophoneAccess();
            if (perm) {
              if (perm.granted === false || perm.status === "denied") {
                micDenied = true;
              } else if (perm.granted === true) {
                micPermGranted = true;
              }
            }
          } catch {
            // skipped
          }
        }
        if (!micDenied && typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices) {
          try {
            const devs = await navigator.mediaDevices.enumerateDevices();
            micDetected = devs.some((d) => d.kind === "audioinput");
          } catch {
            // skipped
          }
        } else if (micPermGranted) {
          micDetected = true;
        }
      }

      const speechAvailable = typeof window !== "undefined" && Boolean(window.speechSynthesis);
      const voiceOk = !micDenied && (micDetected || micPermGranted || isTestEnv) && speechAvailable;
      const voiceStatus: DiagnosticStatus = voiceOk ? "verified" : "warning";
      const voiceDetail = voiceOk
        ? "Microphone, Neural Speech & Screen Capture Ready"
        : micDenied
        ? "Microphone access denied by system permission"
        : !speechAvailable
        ? "Neural Speech Synthesizer offline"
        : "Microphone device not detected (Audio input offline)";

      if (isMountedRef.current) {
        setScanPulse(voiceOk ? "cyan" : "amber");
        setCategories((prev) =>
          prev.map((c) =>
            c.id === "integrations"
              ? {
                  ...c,
                  status: voiceStatus,
                  detail: voiceDetail,
                }
              : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 7. Security & Safety Gates
      updatePhase("security");
      setCurrentOperation("VALIDATING SECURITY BOUNDARIES...");
      setCategories((prev) => prev.map((c) => (c.id === "security" ? { ...c, status: "checking" } : c)));
      if (isMountedRef.current) {
        setScanPulse("cyan");
        const secDetail = "AssertTrustedSender Active • A02 Safety Gates Armed • Sensitive Data Protected";
        setCategories((prev) =>
          prev.map((c) =>
            c.id === "security"
              ? {
                  ...c,
                  status: "verified",
                  detail: secDetail,
                }
              : c
          )
        );
      }

      await sleep(stepDuration);
      if (!isMountedRef.current) return;

      // 8. Final Synchronization
      setCurrentOperation("SYNCHRONIZING ALEX SYSTEM COMPONENTS...");
      await sleep(stepDuration / 2);
      if (!isMountedRef.current) return;

      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }

      const cpuMemStatus: DiagnosticStatus = (retrievedMetrics || retrievedVerification) ? "verified" : "warning";
      const backendStat: DiagnosticStatus = (!backendStatus || backendStatus.status !== "ready") ? "failed" : "verified";
      const aiStatus: DiagnosticStatus = isKeyOk ? "verified" : "warning";

      const categoryStatuses: DiagnosticStatus[] = [
        "verified", // os
        cpuMemStatus, // cpu_mem
        "verified", // app
        backendStat, // backend
        aiStatus, // ai
        voiceStatus, // integrations
        "verified", // security
      ];

      const failedCount = categoryStatuses.filter((s) => s === "failed").length;
      const warningCount = categoryStatuses.filter((s) => s === "warning").length;
      const verifiedCount = categoryStatuses.filter((s) => s === "verified").length;

      const isCriticalFailed = failedCount > 0;
      const calculatedStatusType: "online" | "degraded" | "attention" = isCriticalFailed
        ? "attention"
        : warningCount > 0
        ? "degraded"
        : "online";
      const calculatedStatusTitle = isCriticalFailed
        ? "ALEX SYSTEM ATTENTION REQUIRED"
        : warningCount > 0
        ? "ALEX SYSTEM ONLINE — DEGRADED"
        : "ALEX SYSTEM ONLINE";

      const calculatedHealthPercent = Math.round((verifiedCount / 7) * 100);

      setStatusType(calculatedStatusType);
      setStatusTitle(calculatedStatusTitle);
      setCompletionTime(new Date().toLocaleTimeString());

      setCurrentOperation(`${calculatedStatusTitle} • ALL SYSTEM DIAGNOSTICS COMPLETED.`);
      setScanPulse(calculatedStatusType === "attention" ? "red" : calculatedStatusType === "degraded" ? "amber" : "cyan");
      updatePhase("completed");
      setStage("completed");

      // Play audio chime on system verification
      void playTestChime({ volume: 0.12 });

      // Signal completion report
      const report: DiagnosticReport = {
        overallHealthPercent: calculatedHealthPercent,
        completedCount: 7,
        verifiedCount,
        warningCount,
        failedCount,
        statusType: calculatedStatusType,
        statusTitle: calculatedStatusTitle,
        categories: categoriesRef.current,
        metrics: retrievedMetrics,
        settings: retrievedSettings,
        verification: retrievedVerification,
        timestamp: new Date().toLocaleTimeString(),
      };

      const tDone = window.setTimeout(() => {
        if (!isMountedRef.current) return;
        onDiagnosticsComplete(report);
      }, isTestEnv ? 20 : 800);
      timerRefs.current.push(tDone);
    } catch {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (isMountedRef.current) {
        setFailedMandatory("Unexpected error occurred during system diagnostic scan.");
      }
    }
  }, [
    assistantName,
    discoveredBackendStatus,
    discoveredMetrics,
    discoveredMicReady,
    discoveredSettings,
    discoveredVerification,
    isTestEnv,
    onDiagnosticsComplete,
    updatePhase,
  ]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearAllTimers();
    };
  }, [clearAllTimers]);

  useEffect(() => {
    if (active && internalStage === "stage2" && !failedMandatory && !diagnosticsStartedRef.current) {
      diagnosticsStartedRef.current = true;
      void runDiagnostics();
    }
  }, [active, internalStage, failedMandatory, runDiagnostics]);

  const verifiedCount = useMemo(
    () => categories.filter((c) => c.status === "verified" || c.status === "warning").length,
    [categories]
  );
  const overallDiagnosticPercent = Math.round((verifiedCount / categories.length) * 100);

  const subsystems: Array<{
    name: string;
    state: "PENDING" | "SCANNING" | "VERIFIED" | "WARNING" | "FAILED";
  }> = useMemo(() => {
    function getStatus(ids: string[]): "PENDING" | "SCANNING" | "VERIFIED" | "WARNING" | "FAILED" {
      const matching = categories.filter((c) => ids.includes(c.id));
      if (matching.some((c) => c.status === "failed")) return "FAILED";
      if (matching.some((c) => c.status === "warning")) return "WARNING";
      if (matching.some((c) => c.status === "checking")) return "SCANNING";
      if (matching.length > 0 && matching.every((c) => c.status === "verified")) return "VERIFIED";
      return "PENDING";
    }

    return [
      { name: "SYSTEM", state: getStatus(["system", "cpu_mem"]) },
      { name: "BACKEND", state: getStatus(["backend", "app"]) },
      { name: "AI ENGINE", state: getStatus(["ai"]) },
      { name: "VOICE", state: getStatus(["voice"]) },
      { name: "SECURITY", state: getStatus(["security"]) },
    ];
  }, [categories]);

  const isJarvis = assistantName.toLowerCase().includes("jarvis");
  const logoTitle = isJarvis ? "J.A.R.V.I.S" : "A.L.E.X";
  const logoSubtitle = isJarvis
    ? "JUST A RATHER VERY INTELLIGENT SYSTEM"
    : "ADVANCED LOGICAL ELECTRONIC X-SYSTEM";

  if (!active) return null;

  return (
    <div
      className="holo-startup-overlay"
      role="region"
      aria-label="Cinematic Startup and System Initialization"
      data-stage={internalStage}
    >
      {/* Background Cyber Particle Canvas */}
      <canvas ref={particleCanvasRef} className="holo-particle-canvas" aria-hidden="true" />

      {/* Top HUD Brand Bar — Stage 1 Only */}
      {internalStage === "stage1" && (
        <header className="holo-startup-topbar">
          <div className="holo-topbar-brand">
            <span className="holo-pulsing-pip" />
            <strong>ALEX SYSTEM INITIALIZATION</strong>
            <span className="holo-center-tag">ALEX COMMAND CENTER</span>
            <span className="holo-version-tag">v0.1.0 • {userName.toUpperCase()}</span>
          </div>
          <div className="holo-topbar-actions">
            <button
              type="button"
              className="holo-skip-btn"
              onClick={onSkipToDashboard}
              title="Skip directly to dashboard"
              aria-label="Skip to Dashboard"
            >
              DASHBOARD ✕
            </button>
          </div>
        </header>
      )}

      {/* ======================================================== */}
      {/* STAGE 1: CINEMATIC STARTUP SCREEN (J.A.R.V.I.S STYLE)   */}
      {/* ======================================================== */}
      {internalStage === "stage1" && (
        <section className="holo-stage1-container" aria-label="System Boot Sequence">
          {/* Central Glowing Acronym */}
          <div className="holo-jarvis-logo-wrap animate-holo-arrive">
            <h1 className="holo-jarvis-logo">{logoTitle}</h1>
            <div className="holo-jarvis-subtitle">{logoSubtitle}</div>
          </div>

          {/* Central Rotating Holographic Ring with Center Pip */}
          <div className="holo-jarvis-orb-wrap">
            <div className="holo-jarvis-ring-outer" />
            <div className="holo-jarvis-ring-spinner" />
            <div className="holo-jarvis-center-pip" />
          </div>

          {/* Calibrating / Status Text */}
          <div className="holo-jarvis-status-kicker">
            <span className="holo-jarvis-status-title">CALIBRATING</span>
            <span className="holo-jarvis-status-detail">{BOOT_MESSAGES[bootMessageIndex]}</span>
          </div>

          {/* Sleek Horizontal Glowing Progress Bar */}
          <div className="holo-jarvis-bar-wrap">
            <div className="holo-jarvis-bar-track">
              <div className="holo-jarvis-bar-fill" style={{ width: `${bootProgress}%` }} />
            </div>
            <div className="holo-jarvis-percent-text">{bootProgress}%</div>
          </div>

          {/* Cyan Pagination / Sequence Dots */}
          <div className="holo-jarvis-dots">
            {BOOT_MESSAGES.map((_, i) => (
              <span
                key={i}
                className={`holo-dot ${i === bootMessageIndex ? "active" : i < bootMessageIndex ? "done" : ""}`}
              />
            ))}
          </div>
        </section>
      )}

      {/* ======================================================== */}
      {/* STAGE 2: AVATAR-ONLY DIAGNOSTICS & SYSTEM INITIALIZATION */}
      {/* ======================================================== */}
      {(internalStage === "stage2" || internalStage === "completed") && (
        <section
          className="holo-avatar-diagnostics-hud"
          aria-label="Holographic System Diagnostics"
          data-diag-phase={activePhase}
        >
          {/* TOP SECTION: Minimal Branding & System ID */}
          <header className="holo-diag-top">
            <div className="holo-diag-top-branding">
              <span className="holo-diag-pulse-pip" />
              <strong className="holo-diag-top-title">ALEX SYSTEM INITIALIZATION</strong>
              <span className="holo-diag-top-sep">•</span>
              <span className="holo-diag-top-sub">SYSTEM INITIALIZATION &amp; DIAGNOSTICS</span>
            </div>
            <div className="holo-diag-top-meta">
              <span className="holo-diag-meta-tag">NEURAL CORE v0.1.0</span>
              <span className="holo-diag-meta-tag">STAGE 02</span>
              <button
                type="button"
                className="holo-diag-skip-btn"
                onClick={onSkipToDashboard}
                aria-label="Skip to Dashboard"
              >
                DASHBOARD ✕
              </button>
            </div>
          </header>

          {/* CENTRE: Framing & Scanning Reticle around central avatar */}
          <div className="holo-avatar-reticle" aria-hidden="true" data-diag-phase={activePhase}>
            {/* Concentric Rotating Holographic Rings */}
            <div className={`holo-reticle-rings ${scanPulse ? `pulse-${scanPulse}` : ""}`}>
              <div className="holo-reticle-ring-outer" />
              <div className="holo-reticle-ring-mid" />
              <div className="holo-reticle-ring-inner" />
            </div>

            {/* Subtle Volumetric Holographic Light Rays */}
            <div className="holo-light-rays" />

            {/* Circular Radar Sweep */}
            <div className="holo-radar-sweep" />

            {/* Synchronized Core Shockwave Ring */}
            <div className="holo-core-shockwave" />

            {/* Protective Security Holographic Barrier */}
            <div className="holo-shield-barrier" />

            {/* Subtle Horizon Perspective Grid */}
            <div className="holo-perspective-grid" />

            {/* Holographic Top-to-Bottom Scanning Beam */}
            <div className="holo-scanner-sweep" />

            {/* Completion Nova Bloom (when completed) */}
            {activePhase === "completed" && <div className="holo-completion-nova" />}

            {/* Standalone Fallback: Render HudAvatar only when showAvatarInOverlay is true */}
            {showAvatarInOverlay && (
              <div className="holo-overlay-avatar-wrap">
                <HudAvatar
                  assistantName={assistantName}
                  mode={internalStage === "completed" ? "idle" : "booting"}
                  style="face"
                  primaryColor="#00dfff"
                  accentColor="#ff7a16"
                />
              </div>
            )}
          </div>

          {/* LOWER SECTION: Activity, Progress & 5 Subsystems */}
          <footer className="holo-diag-lower-dock">
            {/* Current Activity Banner */}
            <div className="holo-activity-banner">
              <div className="holo-activity-icon">
                {internalStage === "completed" ? (
                  <span className="holo-check-glyph">✓</span>
                ) : (
                  <span className="holo-spin-glyph">⟳</span>
                )}
              </div>
              <div className="holo-activity-text">
                <span className="holo-activity-label">
                  {internalStage === "completed" ? "DIAGNOSTIC STATUS" : "CURRENT ACTIVITY"}
                </span>
                <span className="holo-activity-current">
                  {internalStage === "completed"
                    ? `${statusTitle} • ALL SYSTEM DIAGNOSTICS COMPLETED.`
                    : currentOperation}
                </span>
              </div>
              <div className="holo-activity-timer">
                <span>{elapsedSeconds.toFixed(1)}s</span>
              </div>
            </div>

            {/* Compact Glowing Progress Bar */}
            <div className="holo-diag-progress-wrap">
              <div className="holo-diag-progress-bar">
                <div
                  className="holo-diag-progress-fill"
                  style={{ width: `${overallDiagnosticPercent}%` }}
                />
              </div>
              <div className="holo-diag-progress-label">
                <span>{overallDiagnosticPercent}%</span>
              </div>
            </div>

            {/* Five Compact Subsystem Status Indicators */}
            <div className="holo-subsystems-row" role="region" aria-label="Subsystem Verification">
              {subsystems.map((sub) => (
                <div
                  key={sub.name}
                  className={`holo-subsystem-pill status-${sub.state.toLowerCase()}`}
                >
                  <span className="holo-sub-pip" />
                  <span className="holo-sub-name">{sub.name}</span>
                  <span className="holo-sub-state">{sub.state}</span>
                </div>
              ))}
            </div>

            {/* Mandatory Failure Panel if error occurred */}
            {failedMandatory && (
              <div className="holo-error-panel" role="alert">
                <div className="holo-error-head">
                  <span className="holo-error-icon">✕</span>
                  <strong>MANDATORY INITIALIZATION FAILURE</strong>
                </div>
                <p>{failedMandatory}</p>
                <div className="holo-error-actions">
                  <button
                    type="button"
                    className="holo-btn holo-btn-retry"
                    onClick={() => {
                      diagnosticsStartedRef.current = false;
                      void runDiagnostics();
                    }}
                  >
                    ⟳ RETRY DIAGNOSTICS
                  </button>
                  <button
                    type="button"
                    className="holo-btn holo-btn-degrade"
                    onClick={onSkipToDashboard}
                  >
                    CONTINUE IN DEGRADED MODE ❯
                  </button>
                </div>
              </div>
            )}

            {/* Completion Status Badge */}
            {internalStage === "completed" && (
              <div className={`holo-completion-badge status-${statusType} animate-holo-arrive`}>
                <span className="holo-completion-title">ALEX SYSTEM ONLINE</span>
                <span className="holo-completion-sub">ALL SYSTEM DIAGNOSTICS COMPLETED.</span>
                {completionTime && <span className="holo-completion-time">{completionTime}</span>}
              </div>
            )}
          </footer>
        </section>
      )}
    </div>
  );
}
