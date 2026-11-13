import { describe, expect, it } from "vitest";
import { parseWorkspaceCommand } from "./workspaceCommands";

describe("workspaceCommands parser", () => {
  it("recognizes commands to return to normal mode and close workspace", () => {
    expect(parseWorkspaceCommand("return to normal mode").action).toBe("close");
    expect(parseWorkspaceCommand("back to normal").action).toBe("close");
    expect(parseWorkspaceCommand("close this").action).toBe("close");
    expect(parseWorkspaceCommand("close workspace").action).toBe("close");
    expect(parseWorkspaceCommand("exit workspace").action).toBe("close");
  });

  it("recognizes open workspace and floating workspace commands", () => {
    const ws1 = parseWorkspaceCommand("open workspace");
    expect(ws1.isWorkspaceCommand).toBe(true);
    expect(ws1.action).toBe("open");
    expect(ws1.activityType).toBe("tool");
    expect(ws1.title).toBe("Holographic Workspace");

    const ws2 = parseWorkspaceCommand("launch the workspace");
    expect(ws2.isWorkspaceCommand).toBe(true);
    expect(ws2.action).toBe("open");
    expect(ws2.activityType).toBe("tool");

    const ws3 = parseWorkspaceCommand("floating workspace");
    expect(ws3.isWorkspaceCommand).toBe(true);
    expect(ws3.action).toBe("open");
  });

  it("recognizes pause and resume commands", () => {
    expect(parseWorkspaceCommand("pause video").action).toBe("pause");
    expect(parseWorkspaceCommand("pause the video").action).toBe("pause");
    expect(parseWorkspaceCommand("pause music").action).toBe("pause");
    expect(parseWorkspaceCommand("resume video").action).toBe("resume");
    expect(parseWorkspaceCommand("resume music").action).toBe("resume");
  });

  it("recognizes music playback commands", () => {
    const res1 = parseWorkspaceCommand("play music");
    expect(res1.isWorkspaceCommand).toBe(true);
    expect(res1.action).toBe("open");
    expect(res1.activityType).toBe("music");

    const res2 = parseWorkspaceCommand("play song synthwave neon");
    expect(res2.isWorkspaceCommand).toBe(true);
    expect(res2.action).toBe("open");
    expect(res2.activityType).toBe("music");
    expect(res2.title).toBe("SYNTHWAVE NEON");
  });

  it("recognizes video playback commands", () => {
    const res1 = parseWorkspaceCommand("play video");
    expect(res1.isWorkspaceCommand).toBe(true);
    expect(res1.action).toBe("open");
    expect(res1.activityType).toBe("video");

    const res2 = parseWorkspaceCommand("play this video");
    expect(res2.isWorkspaceCommand).toBe(true);
    expect(res2.activityType).toBe("video");

    const res3 = parseWorkspaceCommand("play cyberpunk trailer on youtube");
    expect(res3.isWorkspaceCommand).toBe(true);
    expect(res3.activityType).toBe("video");
    expect(res3.title).toBe("cyberpunk trailer");

    const res4 = parseWorkspaceCommand("ALEX, play video Disco Malayalam movie.");
    expect(res4.isWorkspaceCommand).toBe(true);
    expect(res4.action).toBe("open");
    expect(res4.activityType).toBe("video");
    expect(res4.title).toBe("disco malayalam movie");

    const res5 = parseWorkspaceCommand("search youtube for Interstellar trailer");
    expect(res5.isWorkspaceCommand).toBe(true);
    expect(res5.action).toBe("open");
    expect(res5.activityType).toBe("video");
    expect(res5.title).toBe("interstellar trailer");
  });

  it("recognizes document, PDF, and image commands", () => {
    const pdfRes = parseWorkspaceCommand("open this pdf");
    expect(pdfRes.isWorkspaceCommand).toBe(true);
    expect(pdfRes.activityType).toBe("pdf");

    const imgRes = parseWorkspaceCommand("show image");
    expect(imgRes.isWorkspaceCommand).toBe(true);
    expect(imgRes.activityType).toBe("image");

    const docRes = parseWorkspaceCommand("open this file");
    expect(docRes.isWorkspaceCommand).toBe(true);
    expect(docRes.activityType).toBe("document");
  });

  it("recognizes browser workspace commands", () => {
    const b1 = parseWorkspaceCommand("open browser");
    expect(b1.isWorkspaceCommand).toBe(true);
    expect(b1.action).toBe("open");
    expect(b1.activityType).toBe("browser");

    const b2 = parseWorkspaceCommand("browse https://example.com");
    expect(b2.isWorkspaceCommand).toBe(true);
    expect(b2.action).toBe("open");
    expect(b2.activityType).toBe("browser");
    expect(b2.source).toBe("https://example.com");
  });

  it("recognizes all 10 Step 7 voice commands accurately", () => {
    // 1. "ALEX, play video Disco Malayalam movie."
    const c1 = parseWorkspaceCommand("ALEX, play video Disco Malayalam movie.");
    expect(c1.isWorkspaceCommand).toBe(true);
    expect(c1.action).toBe("open");
    expect(c1.activityType).toBe("video");
    expect(c1.title).toBe("disco malayalam movie");

    // 2. "ALEX, pause the video."
    const c2 = parseWorkspaceCommand("ALEX, pause the video.");
    expect(c2.isWorkspaceCommand).toBe(true);
    expect(c2.action).toBe("pause");

    // 3. "ALEX, resume video."
    const c3 = parseWorkspaceCommand("ALEX, resume video.");
    expect(c3.isWorkspaceCommand).toBe(true);
    expect(c3.action).toBe("resume");

    // 4. "ALEX, open this PDF."
    const c4 = parseWorkspaceCommand("ALEX, open this PDF.");
    expect(c4.isWorkspaceCommand).toBe(true);
    expect(c4.action).toBe("open");
    expect(c4.activityType).toBe("pdf");

    // 5. "ALEX, play music."
    const c5 = parseWorkspaceCommand("ALEX, play music.");
    expect(c5.isWorkspaceCommand).toBe(true);
    expect(c5.action).toBe("open");
    expect(c5.activityType).toBe("music");

    // 6. "ALEX, open this image."
    const c6 = parseWorkspaceCommand("ALEX, open this image.");
    expect(c6.isWorkspaceCommand).toBe(true);
    expect(c6.action).toBe("open");
    expect(c6.activityType).toBe("image");

    // 7. "ALEX, minimize this window."
    const c7 = parseWorkspaceCommand("ALEX, minimize this window.");
    expect(c7.isWorkspaceCommand).toBe(true);
    expect(c7.action).toBe("minimize");

    // 8. "ALEX, restore the window."
    const c8 = parseWorkspaceCommand("ALEX, restore the window.");
    expect(c8.isWorkspaceCommand).toBe(true);
    expect(c8.action).toBe("restore");

    // 9. "ALEX, close this window."
    const c9 = parseWorkspaceCommand("ALEX, close this window.");
    expect(c9.isWorkspaceCommand).toBe(true);
    expect(c9.action).toBe("close");

    // 10. "ALEX, return to normal mode."
    const c10 = parseWorkspaceCommand("ALEX, return to normal mode.");
    expect(c10.isWorkspaceCommand).toBe(true);
    expect(c10.action).toBe("close");
  });

  it("recognizes camera and optical sensor commands", () => {
    const cam1 = parseWorkspaceCommand("Open camera and show me in head up display.");
    expect(cam1.isWorkspaceCommand).toBe(true);
    expect(cam1.action).toBe("open");
    expect(cam1.activityType).toBe("camera");

    const cam2 = parseWorkspaceCommand("ALEX, open camera");
    expect(cam2.isWorkspaceCommand).toBe(true);
    expect(cam2.action).toBe("open");
    expect(cam2.activityType).toBe("camera");

    const cam3 = parseWorkspaceCommand("show camera");
    expect(cam3.isWorkspaceCommand).toBe(true);
    expect(cam3.action).toBe("open");
    expect(cam3.activityType).toBe("camera");

    const cam4 = parseWorkspaceCommand("show me in head up display");
    expect(cam4.isWorkspaceCommand).toBe(true);
    expect(cam4.action).toBe("open");
    expect(cam4.activityType).toBe("camera");

    const cam5 = parseWorkspaceCommand("close camera");
    expect(cam5.isWorkspaceCommand).toBe(true);
    expect(cam5.action).toBe("close");

    const cam6 = parseWorkspaceCommand("open camera on hud display");
    expect(cam6.isWorkspaceCommand).toBe(true);
    expect(cam6.action).toBe("open");
    expect(cam6.activityType).toBe("camera");

    const cam7 = parseWorkspaceCommand("open camera on the hud");
    expect(cam7.isWorkspaceCommand).toBe(true);
    expect(cam7.action).toBe("open");
    expect(cam7.activityType).toBe("camera");

    const cam8 = parseWorkspaceCommand("turn off camera");
    expect(cam8.isWorkspaceCommand).toBe(true);
    expect(cam8.action).toBe("close");
  });

  it("does not match unrelated commands", () => {
    expect(parseWorkspaceCommand("what is the weather today").isWorkspaceCommand).toBe(false);
    expect(parseWorkspaceCommand("").isWorkspaceCommand).toBe(false);
  });
});

