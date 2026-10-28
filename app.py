"""SnapMenu browser API. Run one worker with a persistent DATA_DIR."""
import asyncio
import hashlib
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from config import settings
from media import prepare_upload, save_generated_image
from models import LANGUAGES
from providers import ProviderError, Providers
from storage import Store

ROOT = Path(__file__).parent
log = logging.getLogger("snapmenu")
store = Store(settings.data_dir)
providers = Providers(settings)
scan_slots = asyncio.Semaphore(3)
running_scans = set()
image_lock = asyncio.Lock()
decode_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    store.initialize()
    async def expire_menus():
        while True:
            await asyncio.sleep(3600)
            await run_in_threadpool(store.cleanup)
    cleanup = asyncio.create_task(expire_menus())
    try:
        yield
    finally:
        cleanup.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup
        await providers.close()


app = FastAPI(title="SnapMenu", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def browser_session(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Please open SnapMenu in its own browser tab."}, 403)
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 11 * 1024 * 1024:
            return JSONResponse({"detail": "Choose a file smaller than 10 MB."}, 413)
    token = request.cookies.get("snapmenu_session", "")
    new_session = not re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
    if new_session:
        token = secrets.token_urlsafe(32)
    request.state.owner = hashlib.sha256(token.encode()).hexdigest()
    response = await call_next(request)
    if new_session:
        response.set_cookie("snapmenu_session", token, max_age=7 * 86400,
                            httponly=True, samesite="lax", secure=settings.secure_cookies)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    return response


@app.exception_handler(ProviderError)
async def provider_error(request, exc):
    log.warning("provider=%s reason=%s", exc.provider, exc.reason)
    return JSONResponse({"detail": exc.message}, status_code=exc.status)


@app.get("/api/health")
async def health():
    store.check()
    return {"status": "ok"}


@app.get("/api/config")
async def configuration():
    return {"languages": LANGUAGES, "reading_available": bool(settings.openai_key),
            "images_available": bool(settings.openai_key), "max_upload_mb": 10}


def owned_menu(menu_id, owner):
    menu = store.get(menu_id, owner)
    if not menu:
        raise HTTPException(404, "This menu has expired or is not available in this browser.")
    return menu


@app.get("/api/menus/latest")
async def latest(request: Request):
    return {"menu": store.latest(request.state.owner)}


@app.post("/api/menus")
async def scan(request: Request, file: UploadFile, language: str = "en"):
    if language not in LANGUAGES:
        raise HTTPException(422, "Choose one of the supported languages.")
    content = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Choose a file smaller than 10 MB.")
    try:
        # PDFium is not thread-safe. Serialize decoding and cap peak memory for large phone photos.
        async with decode_lock:
            pages = await run_in_threadpool(prepare_upload, content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    if not settings.openai_key:
        raise HTTPException(503, "Menu reading is not connected yet. Please try again later or explore the sample menu.")
    fingerprint = hashlib.sha256(content + language.encode()).hexdigest()
    existing = store.find(request.state.owner, fingerprint)
    if existing:
        return existing
    scan_key = (request.state.owner, fingerprint)
    if scan_key in running_scans:
        raise HTTPException(409, "This menu is already being read. Wait a moment, then refresh to check for your saved menu.")
    if scan_slots.locked():
        raise HTTPException(429, "The kitchen is busy. Please try again in a moment.")
    running_scans.add(scan_key)
    try:
        async with scan_slots:
            store.consume(request.state.owner, "scan", settings.daily_scan_limit, 10)
            result = await providers.read_menu(pages, language, request.state.owner)
            if not result.dishes:
                raise HTTPException(422, "No readable dishes found. Try a closer, well-lit photo of the menu.")
            return store.create(request.state.owner, fingerprint, language, result)
    finally:
        running_scans.discard(scan_key)


@app.get("/api/menus/{menu_id}")
async def get_menu(menu_id: str, request: Request):
    return owned_menu(menu_id, request.state.owner)


@app.delete("/api/menus/{menu_id}")
async def delete_menu(menu_id: str, request: Request):
    owned_menu(menu_id, request.state.owner)
    async with image_lock:
        for task_id in store.pending_tasks(menu_id):
            await providers.cancel_image(task_id)
        store.delete(menu_id, request.state.owner)
    return {"deleted": True}


def dish_from(menu, dish_id):
    for dish in menu["dishes"]:
        if dish["id"] == dish_id:
            return dish
    raise HTTPException(404, "This dish is not on the menu.")


@app.post("/api/menus/{menu_id}/dishes/{dish_id}/image")
async def create_image(menu_id: str, dish_id: str, request: Request):
    menu = owned_menu(menu_id, request.state.owner)
    dish = dish_from(menu, dish_id)
    if not settings.openai_key:
        raise HTTPException(503, "Dish pictures are not connected yet. You can still read every dish.")
    async with image_lock:
        owned_menu(menu_id, request.state.owner)
        current = store.image(menu_id, dish_id)
        if current and current["status"] != "failed":
            return store.public_image(current)
        if current and current["attempts"] >= 2:
            raise HTTPException(429, "This picture could not be made. Please keep browsing the menu.")
        if store.active_images() >= 3:
            raise HTTPException(429, "Three pictures are already being prepared. Try again when one finishes.")
        store.consume(request.state.owner, "image", settings.daily_image_limit, 20)
        # Claim before the paid POST. Ambiguous timeouts must never trigger automatic duplicate charges.
        store.claim_image(menu_id, dish_id)
        try:
            task_id = await providers.start_image(dish, request.state.owner)
            store.update_image(menu_id, dish_id, status="pending", task_id=task_id)
        except ProviderError as exc:
            log.warning("provider=%s reason=%s", exc.provider, exc.reason)
            message = "This picture request could not be confirmed. Please keep browsing the menu." if exc.uncertain else exc.message
            store.update_image(menu_id, dish_id, status="uncertain" if exc.uncertain else "failed", error=message)
        return store.public_image(store.image(menu_id, dish_id))


@app.get("/api/menus/{menu_id}/dishes/{dish_id}/image")
async def poll_image(menu_id: str, dish_id: str, request: Request):
    owned_menu(menu_id, request.state.owner)
    async with image_lock:
        owned_menu(menu_id, request.state.owner)
        current = store.image(menu_id, dish_id)
        if not current:
            raise HTTPException(404, "No picture has been requested yet.")
        if current["status"] != "pending" or time.time() - current["checked_at"] < 5:
            return store.public_image(current)
        store.update_image(menu_id, dish_id, checked_at=time.time())
        try:
            result = await providers.image_status(current["task_id"])
            status = result.get("status")
            if status == "completed":
                encoded = providers.image_result(result)
                path = settings.data_dir / "images" / f"{menu_id}-{dish_id}.webp"
                await run_in_threadpool(save_generated_image, encoded, path)
                store.update_image(menu_id, dish_id, status="ready", error="")
                await providers.delete_image(current["task_id"])
            elif status in {"failed", "cancelled", "incomplete"}:
                message = "This dish picture could not be made." + (" You can try once more." if current["attempts"] < 2 else " Please keep browsing the menu.")
                store.update_image(menu_id, dish_id, status="failed", error=message)
                await providers.delete_image(current["task_id"])
            elif time.time() - current["created_at"] > 600:
                store.update_image(menu_id, dish_id, error="This picture is taking longer than usual. Check again later.")
        except ProviderError as exc:
            log.warning("provider=%s reason=%s", exc.provider, exc.reason)
            fields = {"error": exc.message}
            if exc.reason in {"missing_image", "invalid_image"}:
                fields["status"] = "failed"
                await providers.delete_image(current["task_id"])
            store.update_image(menu_id, dish_id, **fields)
        return store.public_image(store.image(menu_id, dish_id))


@app.get("/api/menus/{menu_id}/dishes/{dish_id}/picture")
async def picture(menu_id: str, dish_id: str, request: Request):
    owned_menu(menu_id, request.state.owner)
    image = store.image(menu_id, dish_id)
    if not image or image["status"] != "ready":
        raise HTTPException(404, "Picture is not ready.")
    return FileResponse(settings.data_dir / "images" / f"{menu_id}-{dish_id}.webp", media_type="image/webp")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(ROOT / "static" / "index.html")
