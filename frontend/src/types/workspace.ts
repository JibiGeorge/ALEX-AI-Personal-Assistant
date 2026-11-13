/**
 * Dynamic HUD Workspace & Intelligent Avatar Positioning Types
 * (ALEX Dynamic Workspace Architecture)
 */

export type WorkspaceMode = "normal" | "workspace";

export type WorkspaceActivityType =
  | "video"
  | "music"
  | "image"
  | "pdf"
  | "document"
  | "browser"
  | "tool"
  | "camera";

export type WorkspaceStatus =
  | "idle"
  | "workspace_opening"
  | "video_playing"
  | "video_paused"
  | "music_playing"
  | "music_paused"
  | "file_viewing"
  | "document_viewing"
  | "image_viewing"
  | "browser_viewing"
  | "camera_viewing"
  | "workspace_closing";

export interface WorkspaceFileMetadata {
  name: string;
  size?: number;
  mimeType: string;
  url?: string;
  content?: string;
  base64?: string;
  dimensions?: { width: number; height: number };
  pageCount?: number;
  wordCount?: number;
}

export interface WorkspaceMusicMetadata {
  title: string;
  artist?: string;
  album?: string;
  duration?: number;
  artworkUrl?: string;
  audioUrl?: string;
}

export interface WorkspaceActivity {
  id: string;
  type: WorkspaceActivityType;
  title: string;
  subtitle?: string;
  source?: string;
  url?: string;
  audioUrl?: string;
  isPlaying?: boolean;
  isMuted?: boolean;
  isMinimized?: boolean;
  isMaximized?: boolean;
  statusText?: string;
  zoomLevel?: number;
  currentPage?: number;
  totalPages?: number;
  fileData?: WorkspaceFileMetadata;
  musicData?: WorkspaceMusicMetadata;
  unsupportedFormat?: boolean;
  unsupportedMessage?: string;
}

