import { describe, expect, it, vi } from "vitest";

import { createScreenAttachment } from "./screenCapture";

interface FakeImage {
  isEmpty(): boolean;
  getSize(): { width: number; height: number };
  toJPEG(quality: number): Buffer;
  resize(options: { width: number; height: number; quality: "good" }): FakeImage;
}

function fakeImage(
  bytes: Buffer,
  size = { width: 1280, height: 720 },
  resized?: FakeImage,
): FakeImage {
  return {
    isEmpty: vi.fn(() => false),
    getSize: vi.fn(() => size),
    toJPEG: vi.fn(() => bytes),
    resize: vi.fn(() => resized ?? fakeImage(bytes, size)),
  };
}

describe("createScreenAttachment", () => {
  it("returns no attachment when the user cancels display selection", async () => {
    const image = fakeImage(Buffer.from("jpeg"));
    const attachment = await createScreenAttachment(
      [{ thumbnail: image }],
      async () => null,
    );

    expect(attachment).toBeNull();
    expect(image.toJPEG).not.toHaveBeenCalled();
  });

  it("encodes only the explicitly selected display as a bounded JPEG attachment", async () => {
    const first = fakeImage(Buffer.from("first"));
    const second = fakeImage(Buffer.from("selected"));
    const chooseSource = vi.fn(async (count: number) => {
      expect(count).toBe(2);
      return 1;
    });

    const attachment = await createScreenAttachment(
      [{ thumbnail: first }, { thumbnail: second }],
      chooseSource,
    );

    expect(chooseSource).toHaveBeenCalledOnce();
    expect(first.toJPEG).not.toHaveBeenCalled();
    expect(attachment).toEqual({
      name: "screen-capture.jpg",
      mime_type: "image/jpeg",
      data_base64: Buffer.from("selected").toString("base64"),
    });
  });

  it("downscales oversized screenshots before producing an attachment", async () => {
    const resized = fakeImage(Buffer.from("small"), { width: 960, height: 540 });
    const original = fakeImage(
      Buffer.alloc(8 * 1024 * 1024 + 1),
      { width: 1280, height: 720 },
      resized,
    );
    const attachment = await createScreenAttachment(
      [{ thumbnail: original }],
      async () => 0,
    );

    expect(original.resize).toHaveBeenCalledWith({
      width: 960,
      height: 540,
      quality: "good",
    });
    expect(attachment?.data_base64).toBe(Buffer.from("small").toString("base64"));
  });

  it("rejects unavailable or empty captures and invalid selection results", async () => {
    await expect(createScreenAttachment([], async () => 0)).rejects.toThrow("No displays");
    const empty = fakeImage(Buffer.alloc(0));
    empty.isEmpty = vi.fn(() => true);
    await expect(
      createScreenAttachment([{ thumbnail: empty }], async () => 0),
    ).rejects.toThrow("screen recording permission");
    await expect(
      createScreenAttachment([{ thumbnail: fakeImage(Buffer.from("jpeg")) }], async () => 1),
    ).rejects.toThrow("selected display is invalid");
  });
});
