import type { FileAttachment } from "../src/types/api";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_RESIZE_ATTEMPTS = 5;

interface ScreenImage {
  isEmpty(): boolean;
  getSize(): { width: number; height: number };
  toJPEG(quality: number): Buffer;
  resize(options: {
    width: number;
    height: number;
    quality: "good";
  }): ScreenImage;
}

interface ScreenSource {
  thumbnail: ScreenImage;
}

export async function createScreenAttachment(
  sources: readonly ScreenSource[],
  chooseSource: (sourceCount: number) => Promise<number | null>,
): Promise<FileAttachment | null> {
  if (sources.length === 0) {
    throw new Error("No displays are available for screen capture.");
  }
  const selectedIndex = await chooseSource(sources.length);
  if (selectedIndex === null) return null;
  if (!Number.isInteger(selectedIndex) || selectedIndex < 0 || selectedIndex >= sources.length) {
    throw new TypeError("The selected display is invalid.");
  }

  let image = sources[selectedIndex].thumbnail;
  if (image.isEmpty()) {
    throw new Error("Screen capture is empty. Check the operating system's screen recording permission.");
  }
  let imageBytes: Uint8Array = new Uint8Array();
  for (let attempt = 0; attempt <= MAX_RESIZE_ATTEMPTS; attempt += 1) {
    imageBytes = image.toJPEG(82);
    if (imageBytes.byteLength <= MAX_IMAGE_BYTES) break;
    if (attempt === MAX_RESIZE_ATTEMPTS) {
      throw new Error("The screen image is too large to attach safely.");
    }
    const size = image.getSize();
    const width = Math.floor(size.width * 0.75);
    const height = Math.floor(size.height * 0.75);
    if (width < 320 || height < 180) {
      throw new Error("The screen image is too large to attach safely.");
    }
    image = image.resize({ width, height, quality: "good" });
  }

  return {
    name: "screen-capture.jpg",
    mime_type: "image/jpeg",
    data_base64: Buffer.from(imageBytes).toString("base64"),
  };
}
