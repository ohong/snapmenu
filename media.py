import base64
import io
import warnings
from contextlib import suppress
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from providers import ProviderError

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 50_000_000


def jpeg_page(image):
    image = ImageOps.exif_transpose(image)
    if image.width * image.height > Image.MAX_IMAGE_PIXELS:
        raise ValueError("This photo is too large. Choose a smaller version.")
    image.thumbnail((1800, 1800))
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, "white")
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        image = canvas
    else:
        image = image.convert("RGB")
    output = io.BytesIO()
    image.save(output, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()


def prepare_upload(content):
    if not content:
        raise ValueError("Choose a photo or PDF of your menu first.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            if content.startswith(b"%PDF-"):
                with pdfium.PdfDocument(content) as document:
                    if not 1 <= len(document) <= 3:
                        raise ValueError("Choose a PDF with 1–3 pages, or photograph one menu page.")
                    pages = []
                    for index in range(len(document)):
                        page = document[index]
                        width, height = page.get_size()
                        if min(width, height) <= 0:
                            raise ValueError("This PDF has an unreadable page. Try a photo instead.")
                        bitmap = page.render(scale=min(2, 1800 / max(width, height)))
                        pages.append(jpeg_page(bitmap.to_pil()))
                        bitmap.close()
                        page.close()
                    return pages
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP", "HEIF", "AVIF"}:
                    raise ValueError("Choose a JPEG, PNG, WebP, HEIC photo, or PDF.")
                return [jpeg_page(image)]
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning, pdfium.PdfiumError):
        raise ValueError("This file could not be opened. Try another photo or an unlocked PDF.") from None


def save_generated_image(encoded, path: Path):
    """Decode provider bytes locally; never fetch model-generated URLs."""
    try:
        if not isinstance(encoded, str) or len(encoded) > 20 * 1024 * 1024:
            raise ValueError("invalid encoded image")
        data = base64.b64decode(encoded, validate=True)
        if len(data) > 15 * 1024 * 1024:
            raise ValueError("oversized image")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.thumbnail((1000, 1000))
                output = image.convert("RGB")
    except (ValueError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ProviderError("OpenAI", "invalid_image", "The picture was unreadable. You can try once more.") from None
    temporary = path.with_suffix(".tmp")
    try:
        output.save(temporary, "WEBP", quality=85)
        temporary.replace(path)
    except OSError:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise ProviderError("OpenAI", "image_storage_failed", "The picture could not be saved. Please check again later.") from None
