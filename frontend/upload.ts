async function jpeg(
  source: CanvasImageSource,
  width: number,
  height: number,
): Promise<string> {
  if (!width || !height || width * height > 50_000_000)
    throw Error("This photo is too large. Choose a smaller version.");
  const scale = Math.min(1, 1800 / Math.max(width, height)),
    canvas = window.document.createElement("canvas");
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const context = canvas.getContext("2d");
  if (!context) throw Error("This browser cannot prepare photos.");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}
export async function prepare(file: File): Promise<string[]> {
  if (file.size > 10 * 1024 * 1024)
    throw Error("Choose a file smaller than 10 MB.");
  if (
    file.type === "application/pdf" ||
    file.name.toLowerCase().endsWith(".pdf")
  ) {
    // PDF code and its worker load only when someone chooses a PDF.
    const pdf = await import("pdfjs-dist");
    const worker = await import("pdfjs-dist/build/pdf.worker.min.mjs?url");
    pdf.GlobalWorkerOptions.workerSrc = worker.default;
    const task = pdf.getDocument({ data: await file.arrayBuffer() });
    const document = await task.promise;
    try {
      if (document.numPages > 3) throw Error("Choose a PDF with 1–3 pages.");
      const pages: string[] = [];
      for (let i = 1; i <= document.numPages; i++) {
        const page = await document.getPage(i),
          base = page.getViewport({ scale: 1 }),
          viewport = page.getViewport({
            scale: Math.min(2, 1800 / Math.max(base.width, base.height)),
          });
        const canvas = window.document.createElement("canvas");
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        await page.render({ canvas, viewport }).promise;
        pages.push(canvas.toDataURL("image/jpeg", 0.85));
        page.cleanup();
      }
      return pages;
    } finally {
      await task.destroy();
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    return [await jpeg(image, image.naturalWidth, image.naturalHeight)];
  } catch (error) {
    if (error instanceof Error && error.message.includes("too large"))
      throw error;
    throw Error(
      "This photo could not be opened. Try JPG, PNG, WebP, or a PDF.",
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}
