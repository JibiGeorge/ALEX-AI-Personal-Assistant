/**
 * Workspace Command Parser
 * Identifies user intents to open, control, or dismiss HUD workspace activities.
 */

import type { WorkspaceActivityType } from "../types/workspace";

export interface WorkspaceCommandResult {
  isWorkspaceCommand: boolean;
  action: "open" | "close" | "pause" | "resume" | "minimize" | "restore" | "none";
  activityType?: WorkspaceActivityType;
  panel?: "overview" | "chat" | "memory" | "settings" | "search" | "audio" | "reminders" | "actions" | "computer" | "job_hunting";
  query?: string;
  source?: string;
  title?: string;
}

function cleanInput(input: string): string {
  return (input || "")
    .trim()
    .toLowerCase()
    .replace(/^(?:me|user|human)[:\s]+/i, "")
    .replace(/^(?:alex|hey alex|jarvis|computer)[,\s]+/i, "")
    .replace(/^(?:yeah|yes|ok|okay|hey|hi|please|can you|could you|would you)[,\s]+/i, "")
    .replace(/[.,/#!$%^&*;:{}=\-_`~()?'"]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseWorkspaceCommand(input: string): WorkspaceCommandResult {
  if (!input) {
    return { isWorkspaceCommand: false, action: "none" };
  }

  const cleaned = cleanInput(input);

  // 1. Return to Normal Mode / Close Workspace commands
  if (
    /^(return to (normal mode|normal|hud|dashboard)|back to normal( mode)?|restore (normal mode|normal|hud)|normal mode)$/i.test(cleaned) ||
    /^(close (this window|the window|window|this|workspace|content|player|video|music|file|document|image|pdf|viewer|camera|webcam))$/i.test(cleaned) ||
    /^(stop (this window|the window|window|this|workspace|content|player|video|music|playback|camera|webcam))$/i.test(cleaned) ||
    /^(turn off (the\s+)?(camera|webcam|video feed|optical sensor))$/i.test(cleaned) ||
    /^(dismiss (this window|the window|window|this|workspace|content|viewer|camera|webcam))$/i.test(cleaned) ||
    /^(exit (workspace|viewer|window|camera))$/i.test(cleaned) ||
    cleaned === "close this window" ||
    cleaned === "close the window" ||
    cleaned === "close window" ||
    cleaned === "close this" ||
    cleaned === "close workspace" ||
    cleaned === "close camera" ||
    cleaned === "stop camera" ||
    cleaned === "turn off camera" ||
    cleaned === "close webcam" ||
    cleaned === "stop webcam" ||
    cleaned === "turn off webcam" ||
    cleaned === "return to normal mode" ||
    cleaned === "back to normal"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "close",
    };
  }

  // 2. Minimize workspace window commands
  if (
    /^(minimize (this window|the window|window|this|workspace|content|stage)|minimize)$/i.test(cleaned) ||
    cleaned === "minimize this window" ||
    cleaned === "minimize the window" ||
    cleaned === "minimize window" ||
    cleaned === "minimize"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "minimize",
    };
  }

  // 3. Restore workspace window commands
  if (
    /^(restore (the window|this window|window|workspace|this|content|stage)|restore|maximize (the window|this window|window|workspace))$/i.test(cleaned) ||
    cleaned === "restore the window" ||
    cleaned === "restore this window" ||
    cleaned === "restore window" ||
    cleaned === "restore" ||
    cleaned === "maximize the window" ||
    cleaned === "maximize window"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "restore",
    };
  }

  // 4. Pause / Resume media commands
  if (
    /^(pause|pause the video|pause video|pause this video|pause music|pause the music|pause player|pause playback|pause the window)$/i.test(cleaned)
  ) {
    return {
      isWorkspaceCommand: true,
      action: "pause",
    };
  }

  if (
    /^(resume|resume the video|resume video|resume this video|resume music|resume the music|resume player|resume playback|unpause)$/i.test(cleaned)
  ) {
    return {
      isWorkspaceCommand: true,
      action: "resume",
    };
  }

  // 3. Camera / Optical sensor feed commands
  if (
    /^(?:open|launch|start|turn on|show|view|activate|display)\s+(?:the\s+)?(?:camera|webcam|optical sensor|video feed)(?:\s+(?:on|in|to)\s+(?:the\s+)?(?:head\s+up\s+display|hud(?:\s+display)?|display|workspace|screen))?/i.test(cleaned) ||
    /^(?:open\s+(?:the\s+)?(?:camera|webcam)\s+(?:and\s+)?)?show\s+(?:me\s+)?(?:on|in)\s+(?:the\s+)?(?:head\s+up\s+display|hud(?:\s+display)?|display|workspace|screen)/i.test(cleaned) ||
    /^(?:camera|webcam|optical sensor)(?:\s+(?:feed|stream))?(?:\s+(?:on|in)\s+(?:the\s+)?(?:head\s+up\s+display|hud(?:\s+display)?|display|workspace|screen))?$/i.test(cleaned) ||
    cleaned === "open camera" ||
    cleaned === "show camera" ||
    cleaned === "open webcam" ||
    cleaned === "show webcam" ||
    cleaned === "camera" ||
    cleaned === "webcam" ||
    cleaned.includes("open camera") ||
    cleaned.includes("show camera") ||
    cleaned.includes("open webcam") ||
    cleaned.includes("show webcam") ||
    cleaned.includes("show me in head up display") ||
    cleaned.includes("show me on hud")
  ) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "camera",
      title: "Optical Sensor Feed",
    };
  }

  // 4. Job Hunting & Career Radar HUD panel commands
  if (
    /^(?:open|show|launch|start|display|view|switch to|access)\s+(?:the\s+)?(?:job\s+hunting|career\s+radar|career\s+hub|job\s+search|job\s+hunter|career)(?:\s+(?:on|in|to)\s+(?:the\s+)?(?:hud|dashboard|screen|workspace))?$/i.test(cleaned) ||
    /^(?:job\s+hunting|career\s+radar|career\s+hub|job\s+hunter)(?:\s+(?:on|in|to)\s+(?:the\s+)?(?:hud|dashboard|screen|workspace))?$/i.test(cleaned) ||
    cleaned === "open job hunting" ||
    cleaned === "open job hunting on hud" ||
    cleaned === "job hunting on hud" ||
    cleaned === "job hunting" ||
    cleaned === "career radar" ||
    cleaned === "career hub"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      panel: "job_hunting",
      title: "Job Hunting & Career Radar",
    };
  }

  // 5. Other system HUD panels
  if (
    /^(?:open|show|launch|display|view|access)\s+(?:the\s+)?(?:settings|customise|customize|audio devices|memory|reminders|actions|computer control)(?:\s+(?:on|in|to)\s+(?:the\s+)?(?:hud|dashboard|screen))?$/i.test(cleaned)
  ) {
    let targetPanel: WorkspaceCommandResult["panel"] = "overview";
    if (cleaned.includes("setting") || cleaned.includes("custom")) targetPanel = "settings";
    else if (cleaned.includes("audio")) targetPanel = "audio";
    else if (cleaned.includes("memory")) targetPanel = "memory";
    else if (cleaned.includes("reminder")) targetPanel = "reminders";
    else if (cleaned.includes("action")) targetPanel = "actions";
    else if (cleaned.includes("computer")) targetPanel = "computer";
    return {
      isWorkspaceCommand: true,
      action: "open",
      panel: targetPanel,
    };
  }

  // 4. Music commands
  if (
    /^(open (the\s+)?workspace|show (the\s+)?workspace|launch (the\s+)?workspace|floating workspace|empty workspace|open floating workspace)$/i.test(cleaned) ||
    cleaned === "open workspace" ||
    cleaned === "show workspace"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "tool",
      title: "Holographic Workspace",
    };
  }

  if (
    /^(play music|start music|listen to music|play some music|play audio)$/i.test(cleaned) ||
    cleaned === "play music"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "music",
      title: "Cyberpunk Ambient Synthesis",
      query: "ambient",
    };
  }

  const musicMatch = cleaned.match(/^(?:play|listen to)\s+(?:song|track|music)\s+(.+)$/i);
  if (musicMatch && musicMatch[1]) {
    const title = musicMatch[1].trim();
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "music",
      title: title.toUpperCase(),
      query: title,
    };
  }

  // 5. PDF, Document, Image, File commands (checked before open video)
  const pdfMatch = cleaned.match(/^(?:open|view|show|read)\s+(?:this\s+|the\s+)?pdf(?:\s+(.+))?$/i);
  if (pdfMatch) {
    const title = pdfMatch[1]?.trim() || "Document Preview.pdf";
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "pdf",
      title: title.endsWith(".pdf") ? title : `${title}.pdf`,
    };
  }

  const imageMatch = cleaned.match(/^(?:open|view|show)\s+(?:this\s+|the\s+)?(?:image|photo|picture)(?:\s+(.+))?$/i);
  if (imageMatch) {
    const title = imageMatch[1]?.trim() || "Visual Asset.png";
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "image",
      title: title.endsWith(".png") || title.endsWith(".jpg") ? title : `${title}.png`,
    };
  }

  const docMatch = cleaned.match(/^(?:open|view|show|read)\s+(?:this\s+|the\s+)?(?:document|file|doc|markdown|text)(?:\s+(.+))?$/i);
  if (docMatch) {
    const title = docMatch[1]?.trim() || "System Document.md";
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "document",
      title: title.endsWith(".md") || title.endsWith(".txt") ? title : `${title}.md`,
    };
  }

  // 5. Browser commands
  const browserRawMatch = input.match(/^(?:(?:alex|hey alex|jarvis|computer)[,\s]+)?(?:open\s+(?:the\s+)?browser|browse|open\s+(?:the\s+)?web(?:site)?|launch\s+browser)(?:\s+(?:to\s+)?(.+))?$/i);
  if (browserRawMatch) {
    const rawTarget = browserRawMatch[1]?.trim() || "https://google.com";
    const targetUrl = /^https?:\/\//i.test(rawTarget) ? rawTarget : `https://${rawTarget}`;
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "browser",
      title: rawTarget,
      source: targetUrl,
    };
  }

  // 6. Video commands
  // Direct YouTube or video URLs
  const urlMatch = input.match(/(https?:\/\/(?:www\.)?(?:youtube\.com|youtu\.be)\/[^\s]+)/i);
  if (urlMatch) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "video",
      source: urlMatch[1],
      title: "YouTube Video",
    };
  }

  if (
    /^(open youtube|play youtube|watch youtube|open video|play video|play this video)$/i.test(cleaned) ||
    cleaned === "open youtube" ||
    cleaned === "play video" ||
    cleaned === "play this video"
  ) {
    return {
      isWorkspaceCommand: true,
      action: "open",
      activityType: "video",
      source: "youtube",
      title: "YouTube Video",
    };
  }

  const videoMatch =
    cleaned.match(/^(?:play|watch)\s+video\s+(.+)$/i) ||
    cleaned.match(/^(?:play|watch|open)\s+(.+?)\s+(?:video|on youtube|on the hud)$/i) ||
    cleaned.match(/^(?:search\s+youtube\s+for|youtube\s+search\s+for|search\s+video\s+for)\s+(.+)$/i) ||
    cleaned.match(/^(?:play|watch)\s+(.+?)\s+trailer$/i);
  if (videoMatch && videoMatch[1]) {
    const title = videoMatch[1].trim();
    const lowerTitle = title.toLowerCase();
    const systemKeywords = [
      "camera",
      "webcam",
      "job hunting",
      "job search",
      "career radar",
      "career hub",
      "jobs",
      "settings",
      "memory",
      "reminders",
      "actions",
      "computer",
      "activity log",
      "logs",
    ];
    if (!systemKeywords.some((kw) => lowerTitle === kw || lowerTitle.includes(kw))) {
      return {
        isWorkspaceCommand: true,
        action: "open",
        activityType: "video",
        source: title,
        title: title,
      };
    }
  }

  return { isWorkspaceCommand: false, action: "none" };
}
