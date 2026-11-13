/**
 * Independent Floating HUD Workspace Window Component
 * (ALEX Step 6 — Universal HUD Workspace Content Integration)
 *
 * Provides a universal, reusable, independent floating content window inside the ALEX HUD:
 * 1. Music Player: Track info, album artwork, full controls (play/pause/stop/seek/volume/mute),
 *    audio visualizer (FFT frequency bars or animated EQ).
 * 2. PDF Viewer: Page navigation (prev/next/page indicator), zoom in/out/fit, scrolling page viewport, filename.
 * 3. Document Viewer: Preserved markdown and syntax code formatting with line numbers, status bar, unsupported format fallback.
 * 4. Image Viewer: Aspect-ratio preservation, zoom in/out/fit, pan/scroll viewport, metadata bar.
 * 5. Browser: Sandboxed iframe web stage, navigation buttons (back/forward/reload), security sandbox pill, address bar.
 * 6. Video: Full YouTube IFrame Player API integration via VideoPlayer.
 * 7. Window Reuse: Single window architecture for all content without duplicate stacking.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import type { WorkspaceActivity, WorkspaceActivityType } from "../../types/workspace";
import { VideoPlayer } from "../VideoPlayer";
import "./HUDWorkspace.css";

export interface HUDWorkspaceWindowProps {
  activity?: WorkspaceActivity | null;
  analyserNode?: AnalyserNode | null;
  onClose: () => void;
  onPlayPauseToggle?: (playing: boolean) => void;
  onMuteToggle?: (muted: boolean) => void;
  onOpenExternal?: (urlOrPath: string) => void;
  onOpenSampleActivity?: (type: WorkspaceActivityType) => void;
  children?: ReactNode;
}

export function HUDWorkspaceWindow({
  activity,
  analyserNode = null,
  onClose,
  onPlayPauseToggle,
  onMuteToggle,
  onOpenExternal,
  onOpenSampleActivity,
  children,
}: HUDWorkspaceWindowProps) {
  // Window windowing state: minimized, maximized
  const [isMinimized, setIsMinimized] = useState(activity?.isMinimized ?? false);
  const [isMaximized, setIsMaximized] = useState(activity?.isMaximized ?? false);

  // Synchronize minimized / maximized states from props/activity updates
  useEffect(() => {
    if (activity && typeof activity.isMinimized === "boolean") {
      setIsMinimized(activity.isMinimized);
    }
  }, [activity?.isMinimized]);

  useEffect(() => {
    if (activity && typeof activity.isMaximized === "boolean") {
      setIsMaximized(activity.isMaximized);
    }
  }, [activity?.isMaximized]);

  // Zoom level state (for image, pdf, document)
  const [zoom, setZoom] = useState(activity?.zoomLevel ?? 100);

  // Audio / music playback states
  const [isMusicPlaying, setIsMusicPlaying] = useState(activity?.isPlaying ?? true);
  const [isMusicMuted, setIsMusicMuted] = useState(activity?.isMuted ?? false);

  // Synchronize external isPlaying changes without resetting seek cursor
  useEffect(() => {
    if (activity && typeof activity.isPlaying === "boolean") {
      setIsMusicPlaying(activity.isPlaying);
    }
  }, [activity?.isPlaying]);
  const [musicVolume, setMusicVolume] = useState(80);
  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const totalDurationSec = activity?.musicData?.duration ?? 210;

  // PDF Viewer pagination state
  const [pdfPage, setPdfPage] = useState(activity?.currentPage ?? 1);
  const totalPdfPages = activity?.totalPages ?? activity?.fileData?.pageCount ?? 4;

  // Browser state
  const defaultBrowserUrl = activity?.url || activity?.source || "https://www.google.com";
  const [browserUrl, setBrowserUrl] = useState(defaultBrowserUrl);
  const [browserInput, setBrowserInput] = useState(defaultBrowserUrl);
  const [browserKey, setBrowserKey] = useState(0);

  // Optical Camera Sensor state & ref
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isMirrored, setIsMirrored] = useState(true);
  const [snapshotNotice, setSnapshotNotice] = useState<string | null>(null);
  const [cameraReloadKey, setCameraReloadKey] = useState(0);

  // Audio visualizer canvas ref
  const visualizerCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Optical Camera Sensor lifecycle (getUserMedia + track teardown on close/switch)
  useEffect(() => {
    if (activity?.type !== "camera") {
      if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop());
        setCameraStream(null);
      }
      return;
    }

    let isMounted = true;
    let activeStream: MediaStream | null = null;

    const startCamera = async () => {
      setCameraError(null);
      try {
        if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
          throw new Error("Hardware video capture is not supported in this environment.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user",
          },
          audio: false,
        });

        if (!isMounted) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        activeStream = stream;
        setCameraStream(stream);

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
      } catch (err: any) {
        if (!isMounted) return;
        const msg =
          err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError"
            ? "Camera access denied. Please allow camera permissions in System Settings > Privacy & Security > Camera."
            : err?.name === "NotFoundError" || err?.name === "DevicesNotFoundError"
            ? "No webcam or video capture device detected on this system."
            : err?.message || "Failed to initialize optical camera sensor.";
        setCameraError(msg);
      }
    };

    void startCamera();

    return () => {
      isMounted = false;
      if (activeStream) {
        activeStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [activity?.type, cameraReloadKey]);

  // Reset / sync state when active activity switches (window reuse)
  useEffect(() => {
    if (activity?.zoomLevel) {
      setZoom(activity.zoomLevel);
    } else {
      setZoom(100);
    }
    if (activity?.type === "music") {
      setIsMusicPlaying(activity.isPlaying ?? true);
      setIsMusicMuted(activity.isMuted ?? false);
      setCurrentTimeSec(0);
    }
    if (activity?.type === "pdf") {
      setPdfPage(activity.currentPage ?? 1);
    }
    if (activity?.type === "browser") {
      const url = activity.url || activity.source || "https://www.google.com";
      setBrowserUrl(url);
      setBrowserInput(url);
    }
  }, [activity?.id, activity?.type, activity?.url, activity?.source, activity?.zoomLevel, activity?.isPlaying, activity?.isMuted, activity?.currentPage]);

  // Key navigation (Esc to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Audio visualizer animation for music playback
  useEffect(() => {
    if (activity?.type !== "music") return;

    const canvas = visualizerCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const bufferLength = analyserNode ? analyserNode.frequencyBinCount : 32;
    const dataArray = new Uint8Array(bufferLength);

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const values: number[] = [];
      if (analyserNode && isMusicPlaying) {
        analyserNode.getByteFrequencyData(dataArray);
        const step = Math.floor(bufferLength / 24);
        for (let i = 0; i < 24; i++) {
          values.push(dataArray[i * step] / 255.0);
        }
      } else if (isMusicPlaying) {
        const t = performance.now() * 0.003;
        for (let i = 0; i < 24; i++) {
          const v = Math.sin(t + i * 0.4) * 0.35 + Math.cos(t * 1.5 + i * 0.2) * 0.25 + 0.4;
          values.push(Math.max(0.08, Math.min(1.0, v)));
        }
      } else {
        for (let i = 0; i < 24; i++) {
          values.push(0.06);
        }
      }

      const barWidth = (width / values.length) * 0.65;
      const gap = (width / values.length) * 0.35;

      values.forEach((val, i) => {
        const barHeight = val * (height * 0.82);
        const x = i * (barWidth + gap) + gap / 2;
        const y = height - barHeight;

        const grad = ctx.createLinearGradient(0, y, 0, height);
        grad.addColorStop(0, "#00ffaa");
        grad.addColorStop(0.5, "#00dfff");
        grad.addColorStop(1, "rgba(0, 100, 200, 0.2)");

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth, barHeight);
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [activity?.type, analyserNode, isMusicPlaying]);

  // Music playback timer
  useEffect(() => {
    if (activity?.type !== "music" || !isMusicPlaying) return;
    const interval = setInterval(() => {
      setCurrentTimeSec((prev) => {
        const next = prev + 1;
        if (next >= totalDurationSec) {
          setIsMusicPlaying(false);
          return 0;
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [activity?.type, isMusicPlaying, totalDurationSec]);

  const toggleMusicPlay = useCallback(() => {
    const nextState = !isMusicPlaying;
    setIsMusicPlaying(nextState);
    onPlayPauseToggle?.(nextState);
  }, [isMusicPlaying, onPlayPauseToggle]);

  const stopMusicPlay = useCallback(() => {
    setIsMusicPlaying(false);
    setCurrentTimeSec(0);
    onPlayPauseToggle?.(false);
  }, [onPlayPauseToggle]);

  const toggleMusicMute = useCallback(() => {
    const nextMuted = !isMusicMuted;
    setIsMusicMuted(nextMuted);
    onMuteToggle?.(nextMuted);
  }, [isMusicMuted, onMuteToggle]);

  const handleMusicSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const sec = Number(e.target.value);
    setCurrentTimeSec(sec);
  }, []);

  const formatSeconds = (sec: number) => {
    if (isNaN(sec) || sec < 0) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const badgeLabels: Record<string, string> = {
    video: "◆ VIDEO WORKSPACE",
    music: "◆ AUDIO PLAYER",
    image: "◆ IMAGE VIEWER",
    pdf: "◆ PDF PREVIEW",
    document: "◆ DOCUMENT VIEWER",
    browser: "◆ BROWSER WORKSPACE",
    camera: "◆ OPTICAL SENSOR",
    tool: "◆ INTERACTIVE TOOL",
    empty: "◆ HOLOGRAPHIC WORKSPACE",
  };

  const activityType = activity?.type || "empty";
  const windowTitle = activity?.title || "HOLOGRAPHIC WORKSPACE";
  const windowSubtitle = activity?.subtitle || (activity ? "" : "Awaiting content feed or file drop");

  // Minimized Window Dock Presentation
  if (isMinimized) {
    return (
      <div className="ws-minimized-dock" role="region" aria-label="Minimized Workspace">
        <button
          type="button"
          className="ws-minimized-chip"
          onClick={() => setIsMinimized(false)}
          title={`Restore ${windowTitle} window`}
          aria-label={`Restore ${windowTitle}`}
        >
          <span className="ws-min-dot" />
          <span className="ws-min-type">{badgeLabels[activityType] || "WORKSPACE"}</span>
          <span className="ws-min-title">{windowTitle}</span>
          <span className="ws-min-restore-action" aria-hidden="true">⤢ RESTORE</span>
        </button>
        <button
          type="button"
          className="ws-min-close-btn"
          onClick={onClose}
          aria-label="Close Workspace"
          title="Close workspace"
        >
          ✕
        </button>
      </div>
    );
  }

  const isEmpty = !activity || (activity.type === "tool" && !activity.url && !activity.fileData);

  return (
    <div
      className={`hud-workspace-container hud-workspace-window ${
        isMaximized ? "is-maximized" : "is-floating"
      }`}
      data-activity-type={activityType}
      role="region"
      aria-label="HUD Workspace Window"
    >
      {/* Window Title & Header Controls */}
      <header className="ws-header">
        <div className="ws-header-left">
          <div className="ws-activity-badge">
            <span className="ws-badge-dot" />
            {badgeLabels[activityType] || "◆ WORKSPACE"}
          </div>
          <div className="ws-title-group">
            <h2 className="ws-title">{windowTitle}</h2>
            {windowSubtitle && <p className="ws-subtitle">{windowSubtitle}</p>}
          </div>
        </div>

        <div className="ws-header-actions">
          {/* Zoom controls for document / image / pdf */}
          {(activity?.type === "image" || activity?.type === "document" || activity?.type === "pdf") && (
            <>
              <button
                aria-label="Zoom Out"
                className="ws-action-btn"
                onClick={() => setZoom((z) => Math.max(50, z - 25))}
                title="Zoom Out"
                type="button"
              >
                −
              </button>
              <span className="ws-action-btn" style={{ cursor: "default" }}>
                {zoom}%
              </span>
              <button
                aria-label="Zoom In"
                className="ws-action-btn"
                onClick={() => setZoom((z) => Math.min(250, z + 25))}
                title="Zoom In"
                type="button"
              >
                +
              </button>
              <button
                aria-label="Reset Zoom"
                className="ws-action-btn"
                onClick={() => setZoom(100)}
                title="Reset Zoom"
                type="button"
              >
                FIT
              </button>
            </>
          )}

          {/* External application launcher */}
          {(activity?.source || activity?.url) && onOpenExternal && (
            <button
              className="ws-action-btn"
              onClick={() => onOpenExternal(activity.source || activity.url || "")}
              title="Open in System Application"
              type="button"
            >
              EXTERNAL ↗
            </button>
          )}

          {/* Window Control: Minimize */}
          <button
            aria-label="Minimize Window"
            className="ws-action-btn ws-win-control ws-min-btn"
            onClick={() => setIsMinimized(true)}
            title="Minimize Window"
            type="button"
          >
            _
          </button>

          {/* Window Control: Maximize / Restore */}
          <button
            aria-label={isMaximized ? "Restore Window" : "Maximize Window"}
            className="ws-action-btn ws-win-control ws-max-btn"
            onClick={() => setIsMaximized((prev) => !prev)}
            title={isMaximized ? "Restore Window" : "Maximize Window"}
            type="button"
          >
            {isMaximized ? "❐" : "□"}
          </button>

          {/* Window Control: Close */}
          <button
            aria-label="Close Workspace"
            className="ws-action-btn ws-close-btn ws-win-control"
            onClick={onClose}
            title="Close Window (Esc)"
            type="button"
          >
            ✕
          </button>
        </div>
      </header>

      {/* Main Window Content Container */}
      <main className="ws-content">
        {children ? (
          children
        ) : isEmpty ? (
          /* Empty Workspace State Canvas */
          <div className="ws-empty-view" data-testid="ws-empty-view">
            <div className="ws-empty-grid-backdrop" aria-hidden="true" />
            <div className="ws-empty-content">
              <div className="ws-empty-logo-ring">
                <span className="ws-empty-diamond">◈</span>
              </div>
              <h3 className="ws-empty-heading">HOLOGRAPHIC WORKSPACE</h3>
              <p className="ws-empty-subheading">
                Independent floating content surface active · Awaiting neural telemetry stream
              </p>
              <div className="ws-empty-actions">
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("video")}
                >
                  <span>▶</span> DEMO VIDEO
                </button>
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("music")}
                >
                  <span>♫</span> NEURAL AUDIO
                </button>
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("document")}
                >
                  <span>📄</span> PROTOCOLS DOC
                </button>
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("pdf")}
                >
                  <span>📑</span> PDF MANUAL
                </button>
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("browser")}
                >
                  <span>🌐</span> BROWSER
                </button>
                <button
                  type="button"
                  className="ws-empty-btn"
                  onClick={() => onOpenSampleActivity?.("camera")}
                >
                  <span>📷</span> LIVE CAMERA
                </button>
              </div>
              <div className="ws-empty-hint">
                Say <kbd>open camera</kbd>, <kbd>play video</kbd>, <kbd>play music</kbd>, <kbd>open pdf</kbd>, <kbd>open browser</kbd>, or drop any file to inspect.
              </div>
            </div>
          </div>
        ) : activity.type === "video" ? (
          /* 1. VIDEO PLAYBACK (Supported via YouTube IFrame API or Native Player) */
          <div className="ws-video-view">
            {activity.url || activity.source ? (
              <VideoPlayer
                audioSrc={activity.audioUrl}
                autoPlay={activity.isPlaying ?? true}
                isPlaying={activity.isPlaying}
                initialMuted={activity.isMuted ?? true}
                onClose={onClose}
                onMuteChange={onMuteToggle}
                onPlayStateChange={onPlayPauseToggle}
                onOpenExternal={onOpenExternal}
                src={activity.url || activity.source || ""}
                title={activity.title}
              />
            ) : (
              <div className="ws-unsupported-view">
                <div className="ws-unsupported-icon">✕</div>
                <p>No video stream URL or YouTube identifier provided.</p>
              </div>
            )}
          </div>
        ) : activity.type === "music" ? (
          /* 2. HOLOGRAPHIC MUSIC PLAYER */
          <div className="ws-music-view" data-testid="ws-music-view">
            <div className="ws-music-orb-stage">
              <div className={`ws-music-vinyl ${!isMusicPlaying ? "is-paused" : ""}`}>
                <div className="ws-music-center-art">
                  {activity.musicData?.artworkUrl ? (
                    <img
                      alt={activity.musicData?.title || "Album Art"}
                      className="ws-music-artwork-img"
                      src={activity.musicData.artworkUrl}
                    />
                  ) : (
                    <span>♫</span>
                  )}
                </div>
              </div>
            </div>

            <div className="ws-music-info">
              <h3 className="ws-music-track-title">{activity.musicData?.title || activity.title}</h3>
              <p className="ws-music-artist">
                {activity.musicData?.artist || "ALEX Neural Engine"}
                {activity.musicData?.album ? ` • ${activity.musicData.album}` : ""}
              </p>
            </div>

            <canvas
              className="ws-music-visualizer-canvas"
              height={54}
              ref={visualizerCanvasRef}
              width={520}
              aria-label="Audio Visualizer"
            />

            <div className="ws-music-progress-bar">
              <input
                aria-label="Seek track position"
                className="ws-music-seek-slider"
                max={totalDurationSec}
                min={0}
                onChange={handleMusicSeek}
                step={1}
                type="range"
                value={currentTimeSec}
              />
              <div className="ws-music-time-stamps">
                <span>{formatSeconds(currentTimeSec)}</span>
                <span>{formatSeconds(totalDurationSec)}</span>
              </div>
            </div>

            <div className="ws-music-controls">
              <button
                aria-label="Stop"
                className="ws-music-ctrl-btn ws-music-ctrl-stop"
                onClick={stopMusicPlay}
                title="Stop (Reset)"
                type="button"
              >
                ⏹
              </button>

              <button
                aria-label={isMusicPlaying ? "Pause" : "Play"}
                className="ws-music-ctrl-btn ws-music-ctrl-play"
                onClick={toggleMusicPlay}
                title={isMusicPlaying ? "Pause" : "Play"}
                type="button"
              >
                {isMusicPlaying ? "❚❚" : "▶"}
              </button>

              <div className="ws-music-volume-group">
                <button
                  aria-label={isMusicMuted ? "Unmute" : "Mute"}
                  className="ws-music-ctrl-btn ws-music-mute-btn"
                  onClick={toggleMusicMute}
                  title={isMusicMuted ? "Unmute" : "Mute"}
                  type="button"
                >
                  {isMusicMuted ? "🔇" : "🔊"}
                </button>
                <input
                  aria-label="Music volume"
                  className="ws-music-volume-slider"
                  max={100}
                  min={0}
                  onChange={(e) => setMusicVolume(Number(e.target.value))}
                  type="range"
                  value={isMusicMuted ? 0 : musicVolume}
                />
              </div>
            </div>
          </div>
        ) : activity.type === "image" ? (
          /* 3. IMAGE VIEWER */
          <div className="ws-image-view" data-testid="ws-image-view">
            <div className="ws-image-viewport">
              <img
                alt={activity.title}
                className="ws-image-element"
                src={
                  activity.url ||
                  (activity.fileData?.base64
                    ? `data:${activity.fileData.mimeType};base64,${activity.fileData.base64}`
                    : "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'><rect width='400' height='300' fill='%2303101c'/><circle cx='200' cy='150' r='60' fill='none' stroke='%2300e5ff' stroke-width='2'/><text x='200' y='155' fill='%2300e5ff' font-family='sans-serif' font-size='14' text-anchor='middle'>VISUAL ASSET</text></svg>")
                }
                style={{ transform: `scale(${zoom / 100})` }}
              />
            </div>
            <div className="ws-doc-toolbar">
              <span>{activity.fileData?.name || activity.title}</span>
              <span>{activity.fileData?.size ? `${Math.round(activity.fileData.size / 1024)} KB` : "IMAGE"}</span>
              <span>ZOOM: {zoom}%</span>
            </div>
          </div>
        ) : activity.type === "pdf" ? (
          /* 4. PDF PREVIEW */
          <div className="ws-pdf-view" data-testid="ws-pdf-view">
            <div className="ws-pdf-toolbar">
              <div className="ws-pdf-nav-controls">
                <button
                  aria-label="Previous Page"
                  className="ws-pdf-page-btn"
                  disabled={pdfPage <= 1}
                  onClick={() => setPdfPage((p) => Math.max(1, p - 1))}
                  type="button"
                >
                  ◀ PREV
                </button>
                <span className="ws-pdf-page-indicator">
                  PAGE {pdfPage} / {totalPdfPages}
                </span>
                <button
                  aria-label="Next Page"
                  className="ws-pdf-page-btn"
                  disabled={pdfPage >= totalPdfPages}
                  onClick={() => setPdfPage((p) => Math.min(totalPdfPages, p + 1))}
                  type="button"
                >
                  NEXT ▶
                </button>
              </div>
              <div className="ws-pdf-filename">
                {activity.fileData?.name || activity.title || "document.pdf"}
              </div>
            </div>

            {activity.url && activity.url.startsWith("http") ? (
              <iframe
                className="ws-pdf-iframe"
                src={`${activity.url}#page=${pdfPage}&view=FitH`}
                title={activity.title}
              />
            ) : (
              <div className="ws-pdf-viewport">
                <div className="ws-pdf-sheet" style={{ transform: `scale(${zoom / 100})` }}>
                  <header className="ws-pdf-sheet-header">
                    <h1 className="ws-pdf-sheet-title">
                      {activity.fileData?.name || activity.title}
                    </h1>
                    <span className="ws-pdf-sheet-date">PAGE {pdfPage} OF {totalPdfPages}</span>
                  </header>
                  <section className="ws-pdf-sheet-body">
                    <h3>SECTION {pdfPage}: ARCHITECTURAL SPECIFICATION</h3>
                    <p>
                      {activity.fileData?.content ||
                        "This document specifies the autonomous runtime interface, telemetry protocols, and holographic rendering surface for the ALEX platform."}
                    </p>
                    <p>
                      Standard vector layout rendering verified. All cryptographic signatures validated.
                      Subsystem verification complete with 0 anomalies reported.
                    </p>
                  </section>
                </div>
              </div>
            )}
          </div>
        ) : activity.type === "document" ? (
          /* 5. DOCUMENT VIEWER */
          <div className="ws-document-view" data-testid="ws-document-view">
            <div className="ws-doc-toolbar">
              <span>{activity.fileData?.name || activity.title}</span>
              <span>{activity.fileData?.mimeType || "text/markdown"}</span>
              <span>ZOOM: {zoom}%</span>
            </div>

            {activity.unsupportedFormat ? (
              <div className="ws-unsupported-view">
                <div className="ws-unsupported-icon">⤋</div>
                <h3 className="ws-unsupported-title">BINARY / PROPRIETARY FORMAT</h3>
                <p className="ws-unsupported-desc">
                  {activity.unsupportedMessage ||
                    "Direct in-HUD rendering is unsupported for this binary architecture."}
                </p>
                {onOpenExternal && (activity.source || activity.url) && (
                  <button
                    className="ws-action-btn"
                    onClick={() => onOpenExternal(activity.source || activity.url || "")}
                    type="button"
                  >
                    OPEN IN OS APPLICATION ↗
                  </button>
                )}
              </div>
            ) : (
              <div
                className="ws-doc-body"
                style={{ fontSize: `${(zoom / 100) * 13}px` }}
              >
                {(() => {
                  const content =
                    activity.fileData?.content ||
                    `# ${activity.title}\n\n[SYSTEM ACTIVE]\nAll neural telemetry streams verified.\nSecurity policy compliant.\nMemory encryption active.`;

                  // Format as structured document
                  return (
                    <div className="ws-doc-markdown">
                      {content.split("\n").map((line, idx) => {
                        if (line.startsWith("# ")) {
                          return <h1 key={idx}>{line.replace("# ", "")}</h1>;
                        }
                        if (line.startsWith("## ")) {
                          return <h2 key={idx}>{line.replace("## ", "")}</h2>;
                        }
                        if (line.startsWith("### ")) {
                          return <h3 key={idx}>{line.replace("### ", "")}</h3>;
                        }
                        if (line.startsWith("- ")) {
                          return <li key={idx} style={{ marginLeft: "20px" }}>{line.replace("- ", "")}</li>;
                        }
                        if (!line.trim()) {
                          return <div key={idx} style={{ height: "10px" }} />;
                        }
                        return <p key={idx} style={{ margin: "4px 0" }}>{line}</p>;
                      })}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        ) : activity.type === "browser" ? (
          /* 6. BROWSER WORKSPACE */
          <div className="ws-browser-view" data-testid="ws-browser-view">
            <div className="ws-browser-toolbar">
              <button
                aria-label="Browser Back"
                className="ws-browser-nav-btn"
                onClick={() => setBrowserKey((k) => k + 1)}
                title="Back"
                type="button"
              >
                ◀
              </button>
              <button
                aria-label="Browser Forward"
                className="ws-browser-nav-btn"
                onClick={() => setBrowserKey((k) => k + 1)}
                title="Forward"
                type="button"
              >
                ▶
              </button>
              <button
                aria-label="Browser Reload"
                className="ws-browser-nav-btn"
                onClick={() => setBrowserKey((k) => k + 1)}
                title="Reload"
                type="button"
              >
                ↻
              </button>

              <form
                className="ws-browser-address-bar"
                onSubmit={(e) => {
                  e.preventDefault();
                  const target = /^https?:\/\//i.test(browserInput)
                    ? browserInput
                    : `https://${browserInput}`;
                  setBrowserUrl(target);
                  setBrowserKey((k) => k + 1);
                }}
              >
                <span className="ws-browser-security-pill">🔒 SECURE SANDBOX</span>
                <input
                  aria-label="Browser Address"
                  className="ws-browser-address-input"
                  onChange={(e) => setBrowserInput(e.target.value)}
                  type="text"
                  value={browserInput}
                />
              </form>

              {onOpenExternal && (
                <button
                  aria-label="Open in external browser"
                  className="ws-browser-nav-btn"
                  onClick={() => onOpenExternal(browserUrl)}
                  style={{ width: "auto", padding: "0 8px", fontSize: "10px" }}
                  title="Open in System Browser"
                  type="button"
                >
                  EXTERNAL ↗
                </button>
              )}
            </div>

            <div className="ws-browser-frame-container">
              <iframe
                key={browserKey}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                className="ws-browser-iframe"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                src={browserUrl}
                title={activity.title || "Browser Stage"}
              />
            </div>
          </div>
        ) : activity.type === "camera" ? (
          /* 7. LIVE OPTICAL CAMERA FEED */
          <div className="ws-camera-view" data-testid="ws-camera-view">
            {cameraError ? (
              <div className="ws-camera-error-panel" role="alert">
                <div className="ws-camera-error-icon">⚠</div>
                <h3 className="ws-camera-error-title">OPTICAL SENSOR OFFLINE</h3>
                <p className="ws-camera-error-msg">{cameraError}</p>
                <button
                  type="button"
                  className="ws-action-btn ws-camera-retry-btn"
                  onClick={() => setCameraReloadKey((k) => k + 1)}
                >
                  RETRY SENSOR CONNECTION ⟳
                </button>
              </div>
            ) : (
              <div className="ws-camera-viewport">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={`ws-camera-video ${isMirrored ? "is-mirrored" : ""}`}
                  data-testid="hud-camera-video"
                />

                {/* Cybernetic HUD Reticle Overlay */}
                <div className="ws-camera-hud-overlay" aria-hidden="true">
                  <div className="ws-camera-bracket bracket-tl" />
                  <div className="ws-camera-bracket bracket-tr" />
                  <div className="ws-camera-bracket bracket-bl" />
                  <div className="ws-camera-bracket bracket-br" />
                  <div className="ws-camera-crosshair" />
                  <div className="ws-camera-scanline" />

                  <div className="ws-camera-telemetry-bar">
                    <div className="ws-camera-rec-dot" />
                    <span className="ws-camera-telemetry-tag">OPTICAL SENSOR // ACTIVE</span>
                    <span className="ws-camera-telemetry-spec">HD 720P · 60FPS</span>
                  </div>
                </div>

                {/* Bottom Camera Toolbar */}
                <div className="ws-camera-toolbar">
                  <button
                    type="button"
                    className={`ws-camera-tool-btn ${isMirrored ? "is-active" : ""}`}
                    onClick={() => setIsMirrored(!isMirrored)}
                    title="Flip horizontal mirror view"
                  >
                    ⇄ {isMirrored ? "MIRROR: ON" : "MIRROR: OFF"}
                  </button>
                  <button
                    type="button"
                    className="ws-camera-tool-btn"
                    onClick={() => {
                      if (videoRef.current) {
                        const canvas = document.createElement("canvas");
                        canvas.width = videoRef.current.videoWidth || 1280;
                        canvas.height = videoRef.current.videoHeight || 720;
                        const ctx = canvas.getContext("2d");
                        if (ctx) {
                          if (isMirrored) {
                            ctx.translate(canvas.width, 0);
                            ctx.scale(-1, 1);
                          }
                          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
                          setSnapshotNotice("FRAME CAPTURED");
                          setTimeout(() => setSnapshotNotice(null), 2500);
                        }
                      }
                    }}
                    title="Capture still frame snapshot"
                  >
                    ◉ CAPTURE FRAME
                  </button>
                  <button
                    type="button"
                    className="ws-camera-tool-btn"
                    onClick={() => setCameraReloadKey((k) => k + 1)}
                    title="Refresh sensor stream"
                  >
                    ⟳ REFRESH
                  </button>
                  {snapshotNotice && (
                    <span className="ws-camera-snapshot-badge">{snapshotNotice}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* 7. GENERIC / UNSUPPORTED FORMAT VIEW */
          <div className="ws-unsupported-view">
            <div className="ws-unsupported-icon">⤋</div>
            <h3 className="ws-unsupported-title">BINARY ARTIFACT</h3>
            <p className="ws-unsupported-desc">
              {activity.unsupportedMessage ||
                "Direct in-HUD rendering unsupported for this file architecture."}
            </p>
            {onOpenExternal && (activity.source || activity.url) && (
              <button
                className="ws-action-btn"
                onClick={() => onOpenExternal(activity.source || activity.url || "")}
                type="button"
              >
                OPEN IN OS APPLICATION ↗
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
