/**
 * Embedded HUD Media Player (ALEX Step 5 — YouTube Search, Playback & Floating Window)
 *
 * Provides in-stage media playback for YouTube streams (via YouTube IFrame Player API),
 * local video files, and direct stream URLs, with full programmatic synchronization:
 * - Play / Pause / Resume / Stop
 * - Volume & Mute control
 * - Seek slider & live progress ticker
 * - Loading indicator during buffering
 * - Error overlay for restricted/unavailable videos with external fallback
 * - Autoplay blocker detection with tap-to-play prompt
 */

import { useCallback, useEffect, useId, useRef, useState } from "react";

export interface VideoPlayerProps {
  src: string;
  audioSrc?: string;
  title?: string;
  autoPlay?: boolean;
  initialMuted?: boolean;
  isPlaying?: boolean;
  onClose: () => void;
  onMuteChange?: (muted: boolean) => void;
  onPlayStateChange?: (playing: boolean) => void;
  onOpenExternal?: (url: string) => void;
}

export function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

export function extractYouTubeVideoId(urlOrId: string): string | null {
  if (!urlOrId) return null;
  const trimmed = urlOrId.trim();
  // Direct 11-char ID
  if (/^[0-9A-Za-z_-]{11}$/.test(trimmed)) return trimmed;
  // Standard YouTube URL formats
  const match = trimmed.match(/(?:v=|\/embed\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})/i);
  return match ? match[1] : null;
}

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

// Global script loader for YouTube IFrame Player API
let ytApiPromise: Promise<void> | null = null;
function loadYouTubeIFrameApi(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.YT && window.YT.Player) return Promise.resolve();

  if (!ytApiPromise) {
    ytApiPromise = new Promise<void>((resolve) => {
      const existing = document.querySelector('script[src*="youtube.com/iframe_api"]');
      if (!existing) {
        const tag = document.createElement("script");
        tag.src = "https://www.youtube.com/iframe_api";
        tag.async = true;
        document.head.appendChild(tag);
      }

      const prevOnReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (typeof prevOnReady === "function") prevOnReady();
        resolve();
      };

      let count = 0;
      const poll = setInterval(() => {
        count++;
        if (typeof window !== "undefined" && (window as any).YT && (window as any).YT.Player) {
          clearInterval(poll);
          resolve();
        } else if (count > 50 || typeof window === "undefined") {
          clearInterval(poll);
          resolve();
        }
      }, 100);
    });
  }
  return ytApiPromise;
}

export function VideoPlayer({
  src,
  audioSrc,
  title = "Media Playback",
  autoPlay = true,
  initialMuted = true,
  isPlaying: isPlayingProp,
  onClose,
  onMuteChange,
  onPlayStateChange,
  onOpenExternal,
}: VideoPlayerProps) {
  const containerId = useId().replace(/[:]/g, "_");
  const ytMountId = `yt_player_${containerId}`;

  // Native video refs
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // YouTube player instance ref
  const ytPlayerRef = useRef<any>(null);

  // Determine if this source is YouTube
  const youtubeVideoId = extractYouTubeVideoId(src);
  const isYouTube = Boolean(
    youtubeVideoId ||
    /youtube\.com|youtu\.be/i.test(src) ||
    src.toLowerCase() === "youtube"
  );

  // Playback states
  const [isPlaying, setIsPlaying] = useState(isPlayingProp ?? autoPlay);
  const [isMuted, setIsMuted] = useState(initialMuted);
  const [volume, setVolume] = useState(80);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isAutoplayBlocked, setIsAutoplayBlocked] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(true);
  const controlsTimeoutRef = useRef<number | null>(null);

  // Synchronize external isPlaying state (e.g. from voice pause/resume command)
  useEffect(() => {
    if (typeof isPlayingProp === "boolean") {
      if (isPlayingProp !== isPlaying) {
        if (isYouTube && ytPlayerRef.current) {
          try {
            if (isPlayingProp) {
              ytPlayerRef.current.playVideo();
              setIsPlaying(true);
            } else {
              ytPlayerRef.current.pauseVideo();
              setIsPlaying(false);
            }
          } catch {
            setIsPlaying(isPlayingProp);
          }
        } else {
          const video = videoRef.current;
          if (video) {
            if (isPlayingProp) {
              void video.play();
              setIsPlaying(true);
            } else {
              video.pause();
              setIsPlaying(false);
            }
          } else {
            setIsPlaying(isPlayingProp);
          }
        }
      }
    }
  }, [isPlayingProp]);

  // 1. YouTube IFrame API Initialization
  useEffect(() => {
    if (!isYouTube || !youtubeVideoId) {
      setIsLoading(false);
      return;
    }

    let isCancelled = false;
    setIsLoading(true);
    setErrorMessage(null);
    setIsAutoplayBlocked(false);

    loadYouTubeIFrameApi().then(() => {
      if (isCancelled) return;
      if (!window.YT || !window.YT.Player) {
        // Fallback if script loading failed (e.g. offline / test)
        setIsLoading(false);
        return;
      }

      try {
        if (ytPlayerRef.current && typeof ytPlayerRef.current.destroy === "function") {
          ytPlayerRef.current.destroy();
        }

        ytPlayerRef.current = new window.YT.Player(ytMountId, {
          videoId: youtubeVideoId,
          playerVars: {
            autoplay: autoPlay ? 1 : 0,
            enablejsapi: 1,
            controls: 1,
            modestbranding: 1,
            rel: 0,
            playsinline: 1,
            origin: typeof window !== "undefined" ? window.location.origin : undefined,
          },
          events: {
            onReady: (event: any) => {
              if (isCancelled) return;
              setIsLoading(false);
              const player = event.target;
              if (initialMuted) {
                player.mute();
                setIsMuted(true);
              } else {
                player.unMute();
                setIsMuted(false);
              }
              const d = player.getDuration();
              if (typeof d === "number" && d > 0) setDuration(d);

              if (autoPlay) {
                try {
                  player.playVideo();
                } catch {
                  setIsAutoplayBlocked(true);
                }
              }
            },
            onStateChange: (event: any) => {
              if (isCancelled) return;
              const state = event.data;
              const YTState = window.YT?.PlayerState;
              if (!YTState) return;

              if (state === YTState.PLAYING) {
                setIsPlaying(true);
                setIsLoading(false);
                setIsAutoplayBlocked(false);
                setErrorMessage(null);
                onPlayStateChange?.(true);
                const d = ytPlayerRef.current?.getDuration?.();
                if (typeof d === "number" && d > 0) setDuration(d);
              } else if (state === YTState.PAUSED) {
                setIsPlaying(false);
                onPlayStateChange?.(false);
              } else if (state === YTState.BUFFERING) {
                setIsLoading(true);
              } else if (state === YTState.ENDED) {
                setIsPlaying(false);
                onPlayStateChange?.(false);
              } else if (state === YTState.CUED) {
                setIsLoading(false);
              }
            },
            onError: (event: any) => {
              if (isCancelled) return;
              setIsLoading(false);
              const code = event.data;
              let msg = "YouTube playback error occurred.";
              if (code === 101 || code === 150) {
                msg = "The video owner has restricted embedding on third-party players. Tap below to watch directly on YouTube, or ask ALEX for another version.";
              } else if (code === 100) {
                msg = "The requested video was not found or has been removed.";
              } else if (code === 2) {
                msg = "Invalid YouTube video identifier.";
              } else if (code === 5) {
                msg = "HTML5 player error on YouTube stream.";
              }
              setErrorMessage(msg);
            },
          },
        });
      } catch (err) {
        setIsLoading(false);
        setErrorMessage(err instanceof Error ? err.message : "Failed to initialize YouTube player");
      }
    });

    return () => {
      isCancelled = true;
      if (ytPlayerRef.current && typeof ytPlayerRef.current.destroy === "function") {
        try {
          ytPlayerRef.current.destroy();
        } catch {
          // Ignore unmount error
        }
        ytPlayerRef.current = null;
      }
    };
  }, [isYouTube, youtubeVideoId, autoPlay, initialMuted, ytMountId, onPlayStateChange]);

  // 2. Telemetry polling for YouTube playback progress
  useEffect(() => {
    if (!isYouTube) return;
    const interval = setInterval(() => {
      const player = ytPlayerRef.current;
      if (player && typeof player.getCurrentTime === "function") {
        try {
          const t = player.getCurrentTime();
          const d = player.getDuration();
          if (typeof t === "number" && !isNaN(t)) setCurrentTime(t);
          if (typeof d === "number" && !isNaN(d) && d > 0) setDuration(d);
        } catch {
          // Buffering or state transitioning
        }
      }
    }, 250);

    return () => clearInterval(interval);
  }, [isYouTube]);

  // 3. Play / Pause / Resume Controls
  const togglePlay = useCallback(() => {
    if (isYouTube && ytPlayerRef.current) {
      try {
        if (isPlaying) {
          ytPlayerRef.current.pauseVideo();
          setIsPlaying(false);
          onPlayStateChange?.(false);
        } else {
          ytPlayerRef.current.playVideo();
          setIsPlaying(true);
          setIsAutoplayBlocked(false);
          onPlayStateChange?.(true);
        }
      } catch {
        // Fallback
      }
      return;
    }

    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      void video.play().catch(() => {});
      if (audioRef.current && audioSrc) {
        void audioRef.current.play().catch(() => {});
      }
      setIsPlaying(true);
      onPlayStateChange?.(true);
    } else {
      video.pause();
      if (audioRef.current && audioSrc) {
        audioRef.current.pause();
      }
      setIsPlaying(false);
      onPlayStateChange?.(false);
    }
  }, [isYouTube, isPlaying, audioSrc, onPlayStateChange]);

  // 4. Mute / Unmute Controls
  const toggleMute = useCallback(() => {
    const nextMuted = !isMuted;
    if (isYouTube && ytPlayerRef.current) {
      try {
        if (nextMuted) {
          ytPlayerRef.current.mute();
        } else {
          ytPlayerRef.current.unMute();
        }
      } catch {
        // Ignore
      }
    }

    if (videoRef.current) {
      videoRef.current.muted = nextMuted;
    }
    if (audioRef.current) {
      audioRef.current.muted = nextMuted;
    }
    setIsMuted(nextMuted);
    onMuteChange?.(nextMuted);
  }, [isMuted, isYouTube, onMuteChange]);

  // 5. Seek Control
  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekTime = parseFloat(e.target.value);
    setCurrentTime(seekTime);

    if (isYouTube && ytPlayerRef.current && typeof ytPlayerRef.current.seekTo === "function") {
      try {
        ytPlayerRef.current.seekTo(seekTime, true);
      } catch {
        // Ignore
      }
      return;
    }

    if (videoRef.current) {
      videoRef.current.currentTime = seekTime;
    }
    if (audioRef.current && audioSrc) {
      audioRef.current.currentTime = seekTime;
    }
  };

  // 6. Volume Control
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVol = parseInt(e.target.value, 10);
    setVolume(newVol);
    if (newVol === 0 && !isMuted) {
      toggleMute();
    } else if (newVol > 0 && isMuted) {
      toggleMute();
    }

    if (isYouTube && ytPlayerRef.current && typeof ytPlayerRef.current.setVolume === "function") {
      try {
        ytPlayerRef.current.setVolume(newVol);
      } catch {
        // Ignore
      }
    }
    if (videoRef.current) {
      videoRef.current.volume = newVol / 100;
    }
  };

  // 7. Native video event handlers
  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;
    setCurrentTime(video.currentTime);

    if (audioRef.current && audioSrc) {
      const drift = Math.abs(audioRef.current.currentTime - video.currentTime);
      if (drift > 0.25) {
        audioRef.current.currentTime = video.currentTime;
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || 0);
      setIsLoading(false);
    }
  };

  // 8. Keyboard navigation (Esc to close, Space to play/pause, M to mute)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === " " || e.key === "k") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "m") {
        toggleMute();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, toggleMute, togglePlay]);

  // 9. Auto-hide controls overlay
  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current !== null) {
      window.clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = window.setTimeout(() => {
      if (isPlaying) {
        setShowControls(false);
      }
    }, 3200);
  };

  const watchUrl = youtubeVideoId
    ? `https://www.youtube.com/watch?v=${youtubeVideoId}`
    : src;

  return (
    <div
      className="media-player-stage"
      data-testid="media-player-stage"
      onMouseMove={handleMouseMove}
    >
      {/* 1. YouTube IFrame Player API Container or Native Fallback */}
      {isYouTube ? (
        <div
          className="media-player-youtube-wrapper"
          data-testid="media-youtube-container"
          style={{ width: "100%", height: "100%", position: "relative" }}
        >
          {youtubeVideoId ? (
            <div
              id={ytMountId}
              data-testid="media-video-element"
              className="media-player-video media-player-iframe"
              style={{ width: "100%", height: "100%" }}
            />
          ) : (
            <iframe
              src={src.includes("embed") ? src : "https://www.youtube.com/embed?listType=search&list=trending&autoplay=1"}
              title={title}
              className="media-player-video media-player-iframe"
              data-testid="media-video-element"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{ width: "100%", height: "100%", border: "none" }}
            />
          )}
        </div>
      ) : (
        <video
          ref={videoRef}
          src={src}
          autoPlay={autoPlay}
          muted={isMuted}
          playsInline
          className="media-player-video"
          data-testid="media-video-element"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => {
            setIsPlaying(false);
            onPlayStateChange?.(false);
          }}
          onClick={togglePlay}
        />
      )}

      {/* Auxiliary audio element for separate audio streams */}
      {audioSrc && (
        <audio
          ref={audioRef}
          src={audioSrc}
          autoPlay={autoPlay}
          muted={isMuted}
          className="media-aux-audio"
        />
      )}

      {/* Loading state indicator */}
      {isLoading && !errorMessage && !isAutoplayBlocked && (
        <div className="media-loading-overlay">
          <div className="media-loading-spinner" />
          <span className="media-loading-text">SYNCHRONIZING TELEMETRY STREAM...</span>
        </div>
      )}

      {/* Autoplay Blocked Action Prompt */}
      {isAutoplayBlocked && (
        <div className="media-error-overlay media-autoplay-prompt">
          <div className="media-error-card">
            <span className="media-error-icon">▶</span>
            <h4 className="media-error-title">AUTOPLAY PERMISSION REQUIRED</h4>
            <p className="media-error-desc">Browser audio policies require a manual trigger to begin streaming.</p>
            <button
              type="button"
              className="media-action-btn media-play-confirm-btn"
              onClick={togglePlay}
            >
              ▶ START PLAYBACK
            </button>
          </div>
        </div>
      )}

      {/* Error state overlay */}
      {errorMessage && (
        <div className="media-error-overlay">
          <div className="media-error-card">
            <span className="media-error-icon">⚠</span>
            <h4 className="media-error-title">PLAYBACK RESTRICTED</h4>
            <p className="media-error-desc">{errorMessage}</p>
            <div className="media-error-actions">
              <button
                type="button"
                className="media-action-btn media-play-confirm-btn"
                onClick={() => {
                  setErrorMessage(null);
                  if (onOpenExternal) {
                    onOpenExternal(watchUrl);
                  } else {
                    window.open(watchUrl, "_blank");
                  }
                }}
              >
                OPEN IN YOUTUBE ↗
              </button>
              <button
                type="button"
                className="media-action-btn media-btn-secondary"
                onClick={onClose}
              >
                CLOSE STAGE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Header Bar */}
      <div className={`media-header-overlay ${showControls ? "visible" : ""}`}>
        <div className="media-tag-group">
          <span className="media-live-badge">{isYouTube ? "YOUTUBE HUD STREAM" : "LOCAL MEDIA STREAM"}</span>
          <span className="media-title" title={title}>
            {title}
          </span>
        </div>
        <div className="media-header-controls">
          {onOpenExternal && (
            <button
              type="button"
              className="media-external-btn"
              onClick={() => onOpenExternal(watchUrl)}
              title="Open video in external browser"
            >
              EXTERNAL ↗
            </button>
          )}
          <button
            type="button"
            className="media-close-button"
            onClick={onClose}
            aria-label="Close video player"
            title="Close video (Esc)"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Bottom Control Bar */}
      <div className={`media-controls-overlay ${showControls ? "visible" : ""}`}>
        {/* Progress scrub bar */}
        <div className="media-progress-bar">
          <input
            type="range"
            min={0}
            max={duration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="media-seek-slider"
            aria-label="Seek video position"
          />
        </div>

        <div className="media-controls-row">
          <div className="media-left-controls">
            <button
              type="button"
              className="media-icon-button"
              onClick={togglePlay}
              aria-label={isPlaying ? "Pause" : "Play"}
              title={isPlaying ? "Pause (Space)" : "Play (Space)"}
            >
              {isPlaying ? "❚❚" : "▶"}
            </button>

            <button
              type="button"
              className="media-icon-button"
              onClick={toggleMute}
              aria-label={isMuted ? "Unmute" : "Mute"}
              title={isMuted ? "Unmute (M)" : "Mute (M)"}
            >
              {isMuted ? "🔇" : "🔊"}
            </button>

            {/* Volume slider */}
            <input
              type="range"
              min={0}
              max={100}
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="media-volume-slider"
              aria-label="Volume level"
              title={`Volume: ${isMuted ? 0 : volume}%`}
            />

            <span className="media-time-display">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div className="media-right-controls">
            <span className="media-sound-warning">
              {isLoading ? "● BUFFERING" : isPlaying ? "● PLAYING" : "● PAUSED"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
