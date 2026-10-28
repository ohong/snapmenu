"""Real browser + HTTP API + SQLite, with only external providers simulated."""
import io
from pathlib import Path
import httpx
import pytest
from PIL import Image
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "tests/example_menus/simple menu.jpg"


def scan(page, language="en"):
    page.locator("#language").select_option(language)
    page.locator("#upload-file").set_input_files(MENU)
    page.get_by_role("button", name="Read my menu").click()
    expect(page.locator("#menu-view")).to_be_visible(timeout=15000)


def mode(server, scenario):
    httpx.post(server.url + "/__fixture/mode/" + scenario).raise_for_status()


def counts(server):
    return httpx.get(server.url + "/__fixture/stats").json()


@pytest.mark.parametrize("width", [320, 390, 768, 1280])
def test_sample_mobile_layout_and_core_controls(phone, width):
    phone.set_viewport_size({"width": width, "height": 844})
    expect(phone.get_by_role("button", name="Take a photo", exact=True)).to_be_visible()
    assert phone.locator("#camera-file").get_attribute("capture") == "environment"
    assert phone.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    if width == 390:
        (ROOT / "docs/screenshots").mkdir(exist_ok=True)
        phone.screenshot(path=ROOT / "docs/screenshots/mobile-start.png", full_page=True)
    phone.get_by_role("button", name="View sample menu").click()
    expect(phone.locator("#demo-notice")).to_contain_text("sample content")
    expect(phone.locator(".dish-card")).to_have_count(6)
    expect(phone.locator("#shortlist-toggle")).to_have_accessible_name("My picks")
    assert phone.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    phone.get_by_role("button", name="View Spaghetti pomodoro", exact=True).click()
    expect(phone.get_by_role("dialog", name="Spaghetti pomodoro")).to_be_visible()
    expect(phone.locator("#original-name")).to_have_text("Spaghetti al pomodoro")
    phone.get_by_role("button", name="Add to my picks").click()
    expect(phone.get_by_role("button", name="Remove from my picks", exact=True)).to_be_visible()
    phone.get_by_role("button", name="Close dish details").click()
    phone.locator("#shortlist-toggle").click()
    expect(phone.locator(".dish-card")).to_have_count(1)
    if width == 390: phone.screenshot(path=ROOT / "docs/screenshots/mobile-menu.png", full_page=True)
    phone.get_by_role("button", name="About your menu").click()
    expect(phone.get_by_role("dialog", name="Menu privacy")).to_be_visible()
    phone.get_by_role("button", name="Got it").click()


def test_translated_scan_search_categories_picks_and_reload(phone):
    scan(phone, "es")
    expect(phone.locator("#menu-summary")).to_contain_text("10 dishes")
    first = phone.locator(".dish-card").first
    expect(first).to_contain_text("Ensalada fresca")
    expect(first).to_contain_text("Hand Tossed Salad")
    expect(first).to_contain_text("7$ / 6$")
    phone.get_by_role("button", name="Entrées", exact=True).click()
    expect(phone.locator(".dish-card")).to_have_count(4)
    phone.get_by_role("button", name="All dishes", exact=True).click()
    phone.get_by_role("searchbox").fill("Roasted")
    expect(phone.locator(".dish-card")).to_have_count(1)
    phone.get_by_role("button", name="View Verduras asadas", exact=True).click()
    expect(phone.locator("#original-name")).to_have_text("Roasted Vegetables")
    phone.get_by_role("button", name="Add to my picks").click()
    phone.get_by_role("button", name="Close dish details").click()
    phone.get_by_role("searchbox").fill("does not exist")
    expect(phone.locator("#empty-results")).to_be_visible()
    phone.get_by_role("button", name="Show all dishes").click()
    phone.get_by_role("button", name="Help me choose").click()
    expect(phone.locator(".suggested-dish")).to_have_count(3)
    phone.reload()
    expect(phone.locator("#menu-view")).to_be_visible()
    phone.locator("#shortlist-toggle").click()
    expect(phone.locator(".dish-card")).to_have_count(1)
    expect(phone.locator(".dish-card")).to_contain_text("Verduras asadas")
    phone.get_by_role("button", name="New menu").click()
    phone.get_by_role("button", name="View sample menu").click()
    phone.get_by_role("button", name="New menu").click()
    phone.get_by_role("button", name="Back to your last menu").click()
    expect(phone.locator("#menu-title")).to_have_text("Your menu")


def test_image_task_survives_reload_and_restart_without_resubmission(phone, browser, server):
    scan(phone)
    original = counts(server)["image_submissions"]
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    phone.get_by_role("button", name="Generate image").click()
    expect(phone.get_by_role("button", name="Generating image…")).to_be_disabled()
    phone.get_by_role("button", name="Close dish details").click()
    phone.reload()
    expect(phone.locator("#menu-view")).to_be_visible()
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    expect(phone.locator("#dish-picture .picture-badge")).to_have_text("AI INTERPRETATION", timeout=25000)
    assert counts(server)["image_submissions"] == original + 1
    picture_url = phone.locator("#dish-picture img").get_attribute("src")
    assert picture_url.startswith("/api/menus/")
    assert phone.request.get(server.url + picture_url).status == 200
    stranger = browser.new_context()
    assert stranger.request.get(server.url + picture_url).status == 404
    assert stranger.request.get(server.url + "/api/menus/" + picture_url.split("/")[3]).status == 404
    stranger.close()
    phone.get_by_role("button", name="Close dish details").click()
    server.restart()
    phone.reload()
    expect(phone.locator("#menu-view")).to_be_visible()
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    expect(phone.locator("#dish-picture img")).to_have_attribute("src", picture_url)
    assert phone.request.get(server.url + picture_url).status == 200


@pytest.mark.parametrize("scenario, expected", [("scan_unavailable", "temporarily unavailable"), ("empty", "No readable dishes"), ("unreadable", "could not be read"), ("truncated", "could not be read"), ("refusal", "could not be read")])
def test_scan_failure_is_visible_and_retry_keeps_original_file(phone, server, scenario, expected):
    mode(server, scenario)
    phone.locator("#upload-file").set_input_files(MENU)
    phone.get_by_role("button", name="Read my menu").click()
    expect(phone.locator("#upload-error")).to_contain_text(expected)
    expect(phone.locator("#file-name")).to_have_text("simple menu.jpg")
    expect(phone.locator("#menu-view")).to_be_hidden()
    phone.get_by_role("button", name="Read my menu").click()
    expect(phone.locator(".dish-card")).to_have_count(10)


def test_failed_picture_can_retry_but_uncertain_submission_cannot_duplicate(phone, server):
    scan(phone)
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    mode(server, "image_failed")
    phone.get_by_role("button", name="Generate image").click()
    expect(phone.get_by_role("button", name="Retry image")).to_be_enabled(timeout=15000)
    phone.get_by_role("button", name="Retry image").click()
    expect(phone.locator("#dish-picture .picture-badge")).to_have_text("AI INTERPRETATION", timeout=25000)
    phone.get_by_role("button", name="Close dish details").click()
    phone.get_by_role("button", name="View Loaded Baked Potato", exact=True).click()
    mode(server, "image_timeout")
    before = counts(server)["image_submissions"]
    phone.get_by_role("button", name="Generate image").click()
    expect(phone.locator("#image-error")).to_be_visible()
    expect(phone.locator("#generate-image")).to_be_hidden()
    latest = phone.request.get(server.url + "/api/menus/latest").json()["menu"]
    image_path = f"/api/menus/{latest['id']}/dishes/3/image"
    assert phone.request.post(server.url + image_path).json()["status"] == "uncertain"
    assert counts(server)["image_submissions"] == before + 1


def test_invalid_files_and_delete_are_real_public_api_paths(phone, server):
    phone.locator("#upload-file").set_input_files({"name": "bad.jpg", "mimeType": "image/jpeg", "buffer": b"not a photo"})
    phone.get_by_role("button", name="Read my menu").click()
    expect(phone.locator("#upload-error")).to_contain_text("could not be opened")
    scan(phone)
    menu = phone.request.get(server.url + "/api/menus/latest").json()["menu"]
    response = phone.request.delete(server.url + f"/api/menus/{menu['id']}", headers={"Origin": "https://untrusted.example"})
    assert response.status == 403
    phone.once("dialog", lambda dialog: dialog.accept())
    phone.get_by_role("button", name="Delete this menu").click()
    expect(phone.locator("#home")).to_be_visible()
    assert phone.request.get(server.url + f"/api/menus/{menu['id']}").status == 404
    phone.reload()
    expect(phone.locator("#home")).to_be_visible()


def test_pdf_pages_are_sent_to_vision_and_model_text_is_not_html(phone, server):
    output = io.BytesIO()
    Image.new("RGB", (300, 400), "white").save(output, "PDF", save_all=True, append_images=[Image.new("RGB", (300, 400), "white")])
    phone.locator("#upload-file").set_input_files({"name": "menu.pdf", "mimeType": "application/pdf", "buffer": output.getvalue()})
    mode(server, "unsafe_text")
    phone.get_by_role("button", name="Read my menu").click()
    expect(phone.locator(".dish-card")).to_have_count(10)
    assert counts(server)["pages"] == 2
    expect(phone.locator(".dish-card h3").first).to_have_text('<img src=x onerror="alert(1)">')
    assert phone.locator(".dish-text img").count() == 0


def test_upload_size_language_and_rate_limits(server):
    with httpx.Client(base_url=server.url) as client:
        client.get("/api/config")
        assert client.post("/api/menus?language=nope", files={"file": ("menu.jpg", MENU.read_bytes())}).status_code == 422
        assert client.post("/api/menus", content=b"x" * (11 * 1024 * 1024 + 1)).status_code == 413
        for index in range(11):
            data = io.BytesIO()
            Image.new("RGB", (10, 10), (index, 100, 200)).save(data, "PNG")
            response = client.post("/api/menus", files={"file": ("menu.png", data.getvalue())})
            assert response.status_code == (429 if index == 10 else 200)


def test_invalid_generated_image_remains_an_explicit_failure(phone, server):
    scan(phone)
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    mode(server, "image_invalid")
    phone.get_by_role("button", name="Generate image").click()
    expect(phone.locator("#image-error")).to_contain_text("unreadable", timeout=25000)
    expect(phone.get_by_role("button", name="Retry image")).to_be_enabled()
    expect(phone.locator("#dish-picture img")).to_have_count(0)
