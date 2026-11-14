import { describe, expect, it } from "vitest";
import { isActivityLogCloseCommand, isActivityLogOpenCommand, parseMediaCommand } from "./activityCommands";

describe("activityCommands", () => {
  describe("isActivityLogOpenCommand", () => {
    it("recognizes exact commands", () => {
      expect(isActivityLogOpenCommand("open activity log")).toBe(true);
      expect(isActivityLogOpenCommand("open activity logs")).toBe(true);
      expect(isActivityLogOpenCommand("show logs")).toBe(true);
      expect(isActivityLogOpenCommand("view activity")).toBe(true);
      expect(isActivityLogOpenCommand("display logs")).toBe(true);
      expect(isActivityLogOpenCommand("activity logs")).toBe(true);
    });

    it("recognizes commands prefixed with wake words or assistant names", () => {
      expect(isActivityLogOpenCommand("Hey Alex, open activity logs")).toBe(true);
      expect(isActivityLogOpenCommand("Alex show logs")).toBe(true);
      expect(isActivityLogOpenCommand("Jarvis, view activity log")).toBe(true);
      expect(isActivityLogOpenCommand("computer, open the logs")).toBe(true);
    });

    it("recognizes conversational variations", () => {
      expect(isActivityLogOpenCommand("please show me the activity logs")).toBe(true);
      expect(isActivityLogOpenCommand("can you open system logs")).toBe(true);
    });

    it("does not match unrelated commands", () => {
      expect(isActivityLogOpenCommand("open settings")).toBe(false);
      expect(isActivityLogOpenCommand("what is the weather")).toBe(false);
      expect(isActivityLogOpenCommand("")).toBe(false);
    });
  });

  describe("isActivityLogCloseCommand", () => {
    it("recognizes close commands", () => {
      expect(isActivityLogCloseCommand("close activity log")).toBe(true);
      expect(isActivityLogCloseCommand("close logs")).toBe(true);
      expect(isActivityLogCloseCommand("hide activity logs")).toBe(true);
      expect(isActivityLogCloseCommand("dismiss logs")).toBe(true);
    });

    it("recognizes assistant prefix on close commands", () => {
      expect(isActivityLogCloseCommand("Hey Alex, close activity log")).toBe(true);
      expect(isActivityLogCloseCommand("Alex, hide logs")).toBe(true);
    });

    it("does not match unrelated text", () => {
      expect(isActivityLogCloseCommand("close settings")).toBe(false);
      expect(isActivityLogCloseCommand("hello alex")).toBe(false);
    });
  });

  describe("parseMediaCommand", () => {
    it("recognizes commands to open youtube on the hud", () => {
      const res1 = parseMediaCommand("open youtube on the hud");
      expect(res1.isPlay).toBe(true);
      expect(res1.source).toBe("youtube");

      const res2 = parseMediaCommand("play youtube on the hud");
      expect(res2.isPlay).toBe(true);
      expect(res2.source).toBe("youtube");

      const res3 = parseMediaCommand("open youtube");
      expect(res3.isPlay).toBe(true);

      const res4 = parseMediaCommand("Hey Alex, open youtube on the hud");
      expect(res4.isPlay).toBe(true);
      expect(res4.source).toBe("youtube");
    });

    it("recognizes commands to play specific query on youtube", () => {
      const res = parseMediaCommand("play dune trailer on youtube on the hud");
      expect(res.isPlay).toBe(true);
      expect(res.source).toBe("dune trailer");
    });

    it("recognizes commands to close the video player", () => {
      expect(parseMediaCommand("close video").isClose).toBe(true);
      expect(parseMediaCommand("stop video").isClose).toBe(true);
      expect(parseMediaCommand("close youtube").isClose).toBe(true);
      expect(parseMediaCommand("stop media on the hud").isClose).toBe(true);
    });

    it("does not trigger on unrelated input", () => {
      expect(parseMediaCommand("what is the time").isPlay).toBe(false);
      expect(parseMediaCommand("what is the time").isClose).toBe(false);
      expect(parseMediaCommand("open camera on hud display").isPlay).toBe(false);
      expect(parseMediaCommand("open camera on the hud").isPlay).toBe(false);
      expect(parseMediaCommand("open camera on hud").isPlay).toBe(false);
      expect(parseMediaCommand("open job hunting on hud").isPlay).toBe(false);
      expect(parseMediaCommand("Alex, open job hunting on hud").isPlay).toBe(false);
      expect(parseMediaCommand("show job hunting on the hud").isPlay).toBe(false);
      expect(parseMediaCommand("open settings on hud").isPlay).toBe(false);
      expect(parseMediaCommand("career radar on hud").isPlay).toBe(false);
    });
  });
});

