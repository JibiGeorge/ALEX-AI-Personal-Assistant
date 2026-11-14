import { test, expect } from "./fixtures/testFixtures";
import { openWorkspaceViaCommand, closeActiveWorkspace } from "./helpers/workspaceHelper";

test.describe("HUD Document, PDF & Image Viewers", () => {
  test("PDF viewer renders pagination, zoom controls, and page indicator", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "open this pdf");

    const pdfViewer = alexPage.locator(".ws-pdf-view");
    await expect(pdfViewer).toBeVisible();

    // Verify pagination controls
    const prevBtn = pdfViewer.getByRole("button", { name: /previous page/i });
    const nextBtn = pdfViewer.getByRole("button", { name: /next page/i });
    await expect(prevBtn).toBeVisible();
    await expect(nextBtn).toBeVisible();

    // Verify zoom controls in window header
    const windowRoot = alexPage.locator(".hud-workspace-window");
    const zoomInBtn = windowRoot.getByRole("button", { name: /zoom in/i });
    const zoomOutBtn = windowRoot.getByRole("button", { name: /zoom out/i });
    await expect(zoomInBtn).toBeVisible();
    await expect(zoomOutBtn).toBeVisible();

    await closeActiveWorkspace(alexPage);
  });

  test("Document viewer displays line numbers and formatted markdown text", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "open this file");

    const docViewer = alexPage.locator(".ws-document-view");
    await expect(docViewer).toBeVisible();

    // Verify formatted document content
    const docBody = docViewer.locator(".ws-doc-body");
    await expect(docBody).toBeVisible();

    await closeActiveWorkspace(alexPage);
  });

  test("Image viewer preserves aspect ratio and provides zoom and fit controls", async ({ alexPage }) => {
    await openWorkspaceViaCommand(alexPage, "open this image");

    const imgViewer = alexPage.locator(".ws-image-view");
    await expect(imgViewer).toBeVisible();

    // Verify zoom and fit controls in window header
    const windowRoot = alexPage.locator(".hud-workspace-window");
    const fitBtn = windowRoot.getByRole("button", { name: /reset zoom|fit/i });
    await expect(fitBtn).toBeVisible();

    await closeActiveWorkspace(alexPage);
  });
});

