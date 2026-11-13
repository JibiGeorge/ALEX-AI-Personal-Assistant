/**
 * Activity Log Command Parser
 *
 * Recognizes natural-language voice and text commands to open or close
 * the holographic Activity Log drawer with proper animations.
 */

const OPEN_TRIGGERS = new Set([
  "open activity log",
  "open activity logs",
  "open the activity log",
  "open the activity logs",
  "open activity",
  "open activities",
  "open log",
  "open logs",
  "open the logs",
  "open the log",
  "show activity log",
  "show activity logs",
  "show the activity log",
  "show the activity logs",
  "show activity",
  "show activities",
  "show log",
  "show logs",
  "show the logs",
  "view activity log",
  "view activity logs",
  "view the activity log",
  "view the activity logs",
  "view activity",
  "view activities",
  "view log",
  "view logs",
  "view the logs",
  "display activity log",
  "display activity logs",
  "display log",
  "display logs",
  "check activity log",
  "check activity logs",
  "check log",
  "check logs",
  "activity log",
  "activity logs",
  "system log",
  "system logs",
  "open system log",
  "open system logs",
  "show system log",
  "show system logs",
]);

const CLOSE_TRIGGERS = new Set([
  "close activity log",
  "close activity logs",
  "close the activity log",
  "close the activity logs",
  "close activity",
  "close activities",
  "close log",
  "close logs",
  "close the logs",
  "close the log",
  "hide activity log",
  "hide activity logs",
  "hide the activity log",
  "hide the activity logs",
  "hide activity",
  "hide activities",
  "hide log",
  "hide logs",
  "hide the logs",
  "dismiss activity log",
  "dismiss activity logs",
  "dismiss log",
  "dismiss logs",
  "exit activity log",
  "exit activity logs",
  "exit logs",
]);

function cleanInput(text: string): string {
  return text
    .toLowerCase()
    .replace(/^(hey alex|alex|nexora|jarvis|computer)[,\s]+/i, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Checks if the given command is an instruction to open the activity logs.
 */
export function isActivityLogOpenCommand(input: string): boolean {
  if (!input) return false;
  const cleaned = cleanInput(input);
  if (!cleaned) return false;

  if (OPEN_TRIGGERS.has(cleaned)) {
    return true;
  }

  // Regex pattern for looser matching (e.g. "please open my activity logs for me")
  const regex = /\b(open|show|display|view|reveal|launch|expand)\b.*\b(activity log|activity logs|system logs|activities|logs)\b/i;
  return regex.test(cleaned);
}

/**
 * Checks if the given command is an instruction to close the activity logs.
 */
export function isActivityLogCloseCommand(input: string): boolean {
  if (!input) return false;
  const cleaned = cleanInput(input);
  if (!cleaned) return false;

  if (CLOSE_TRIGGERS.has(cleaned)) {
    return true;
  }

  const regex = /\b(close|hide|dismiss|collapse|minimize|exit)\b.*\b(activity log|activity logs|system logs|activities|logs)\b/i;
  return regex.test(cleaned);
}

export interface MediaCommandResult {
  isPlay: boolean;
  isClose: boolean;
  source: string;
  title: string;
}

/**
 * Parses user input for media playback or dismissal commands on the HUD stage.
 */
export function parseMediaCommand(input: string): MediaCommandResult {
  if (!input) return { isPlay: false, isClose: false, source: "", title: "" };
  const cleaned = cleanInput(input);

  // Close or stop media commands
  if (
    /^(close|stop|hide|dismiss|exit)\s+(the\s+)?(video|player|media|youtube|stream|hud video|hud media|workspace|content)(\s+(on|from)\s+(the\s+)?(hud|screen|display))?$/i.test(cleaned) ||
    /^(close|stop)\s+(video|player|youtube|media|this|workspace)$/i.test(cleaned) ||
    /^(return to (normal mode|normal|hud)|back to normal)$/i.test(cleaned) ||
    cleaned === "close video" ||
    cleaned === "stop video" ||
    cleaned === "close youtube" ||
    cleaned === "stop youtube" ||
    cleaned === "close this" ||
    cleaned === "return to normal mode" ||
    cleaned === "back to normal"
  ) {
    return { isPlay: false, isClose: true, source: "", title: "" };
  }

  // Direct YouTube or media URL in input
  const urlMatch = input.match(/(https?:\/\/(?:www\.)?(?:youtube\.com|youtu\.be)\/[^\s]+)/i);
  if (urlMatch) {
    return { isPlay: true, isClose: false, source: urlMatch[1], title: "YouTube Video" };
  }

  // Generic Open/Play YouTube on HUD
  if (
    /^(open|play|launch|show|display|start|watch|view)\s+(the\s+)?youtube(\s+on\s+(the\s+)?(hud|screen|display|stage))?$/i.test(cleaned) ||
    /^(youtube\s+on\s+(the\s+)?(hud|screen|display))$/i.test(cleaned) ||
    cleaned === "open youtube" ||
    cleaned === "open youtube on the hud" ||
    cleaned === "open youtube on hud" ||
    cleaned === "play youtube" ||
    cleaned === "play youtube on the hud" ||
    cleaned === "youtube"
  ) {
    return { isPlay: true, isClose: false, source: "youtube", title: "YouTube" };
  }

  // Play <query> on YouTube (e.g. "play dune trailer on youtube on the hud")
  const playQueryMatch = cleaned.match(/^(?:play|watch|open|show)\s+(.+?)\s+on\s+youtube(?:\s+on\s+(?:the\s+)?(?:hud|screen|display))?$/i);
  if (playQueryMatch && playQueryMatch[1]) {
    const query = playQueryMatch[1].trim();
    if (query.toLowerCase() !== "camera" && query.toLowerCase() !== "webcam") {
      return { isPlay: true, isClose: false, source: query, title: query };
    }
  }

  // Play <query> on the HUD
  const playHudMatch = cleaned.match(/^(?:play|watch|open|show)\s+(.+?)\s+on\s+(?:the\s+)?hud(?:\s+display)?$/i);
  if (playHudMatch && playHudMatch[1]) {
    const query = playHudMatch[1].trim();
    const lowerQuery = query.toLowerCase();
    if (
      lowerQuery !== "camera" &&
      lowerQuery !== "webcam" &&
      !lowerQuery.includes("camera") &&
      !lowerQuery.includes("webcam")
    ) {
      return { isPlay: true, isClose: false, source: query, title: query };
    }
  }

  return { isPlay: false, isClose: false, source: "", title: "" };
}

