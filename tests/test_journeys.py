"""Real browser and Node/Neon/Blob; only external model HTTP is simulated."""

import base64
import io
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from PIL import Image
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "tests/example_menus/simple menu.jpg"


def scan(page, language="en", file=MENU):
    expect(page.get_by_role("button", name="Upload menu", exact=True)).to_be_enabled()
    if language != "en":
        page.get_by_role("combobox", name="Reading language").click()
        page.get_by_role("option", name="Español", exact=True).click()
    page.get_by_label("Choose a menu file").set_input_files(file)
    expect(page.get_by_role("region", name="Visual menu")).to_be_visible(timeout=20000)


def mode(server, value):
    httpx.post(server.url + "/__fixture/mode/" + value).raise_for_status()


def counts(server):
    return httpx.get(server.url + "/__fixture/stats").json()


def no_page_scroll(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight")
    for control in ["Next dishes", "Previous dishes"]:
        button = page.get_by_role("button", name=control)
        if button.count():
            rect = button.bounding_box()
            assert (
                rect["y"] >= 0
                and rect["y"] + rect["height"] <= page.viewport_size["height"] + 1
            )


def upload_data(color="white"):
    image = Image.new("RGB", (100, 100), color)
    output = io.BytesIO()
    image.save(output, "JPEG")
    return {
        "pages": [
            "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()
        ],
        "language": "en",
    }


def wait_image(client, path):
    for _ in range(30):
        response = client.get(path)
        response.raise_for_status()
        image = response.json()
        if image["status"] not in ["pending", "starting"]:
            return image
        time.sleep(0.5)
    raise AssertionError("Image did not complete")


@pytest.mark.parametrize(
    "width,height", [(320, 568), (390, 844), (768, 1024), (844, 390)]
)
def test_no_scroll_and_sample_controls(phone, width, height, server):
    phone.set_viewport_size({"width": width, "height": height})
    expect(phone.get_by_role("button", name="Take a photo", exact=True)).to_be_enabled()
    assert (
        phone.get_by_label("Take a photo of the menu").get_attribute("capture")
        == "environment"
    )
    no_page_scroll(phone)
    if width == 390 and server.provider == "muse":
        phone.screenshot(path=ROOT / "docs/screenshots/mobile-start.png")
    before = counts(server)
    phone.get_by_role("button", name="View sample menu").click()
    expect(phone.locator(".dish-card")).to_have_count(2 if height < 700 else 4)
    no_page_scroll(phone)
    phone.get_by_role("button", name="View Hand Tossed Salad", exact=True).click()
    expect(phone.get_by_role("dialog", name="Hand Tossed Salad")).to_be_visible()
    phone.get_by_role("button", name="Close dish", exact=True).click()
    assert counts(server)["scans"] == before["scans"]
    assert counts(server)["image_submissions"] == before["image_submissions"]


def test_scan_translation_pagination_categories_reload(phone, server):
    scan(phone, "es")
    expect(phone.locator(".dish-card").first).to_contain_text("Ensalada fresca")
    expect(phone.locator(".dish-card").first).to_contain_text("7$ / 6$")
    no_page_scroll(phone)
    phone.get_by_role("button", name="View Ensalada fresca", exact=True).click()
    expect(phone.get_by_role("dialog")).to_contain_text("Hand Tossed Salad")
    phone.get_by_role("button", name="Close dish", exact=True).click()
    phone.get_by_role("button", name="Next dishes").click()
    expect(phone.locator(".dish-card").first).to_contain_text("Ensalada de frutas")
    phone.get_by_role("combobox", name="Menu category").click()
    phone.get_by_role("option", name="Desserts", exact=True).click()
    expect(phone.locator(".dish-card")).to_have_count(2)
    phone.wait_for_load_state("networkidle")
    phone.reload()
    phone.get_by_role("button", name="Back to your last menu").click()
    expect(phone.locator(".dish-card").first).to_contain_text("Ensalada fresca")
    no_page_scroll(phone)


def test_images_appear_and_reload_does_not_resubmit(phone, server):
    scan(phone)
    expect(phone.locator(".dish-visual img")).to_have_count(4, timeout=35000)
    before = counts(server)["image_submissions"]
    assert phone.locator(".dish-visual img").first.evaluate(
        "(image)=>image.complete && image.naturalWidth>0"
    )
    if server.provider == "muse":
        phone.screenshot(path=ROOT / "docs/screenshots/mobile-menu.png")
    phone.wait_for_load_state("networkidle")
    phone.reload()
    phone.get_by_role("button", name="Back to your last menu").click()
    expect(phone.locator(".dish-visual img")).to_have_count(4)
    assert counts(server)["image_submissions"] == before


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("empty", "No readable dishes"),
        ("unreadable", "could not be read completely"),
        ("truncated", "could not be read completely"),
        ("refusal", "could not be read completely"),
        ("scan_unavailable", "AI service is unavailable"),
    ],
)
def test_scan_failures_are_visible(phone, server, scenario, expected):
    mode(server, scenario)
    phone.get_by_label("Choose a menu file").set_input_files(MENU)
    expect(phone.get_by_role("alert")).to_contain_text(expected, timeout=20000)
    expect(phone.get_by_role("button", name="Upload menu")).to_be_visible()
    no_page_scroll(phone)


def test_pdf_preparation_real_browser(phone, server):
    source = ROOT / "evals/menus/sources/a/nopa/source.pdf"
    scan(phone, file=source)
    expect(phone.locator(".dish-card")).to_have_count(4)


def test_invalid_upload_visible(phone):
    phone.get_by_label("Choose a menu file").set_input_files(
        {"name": "invalid.jpg", "mimeType": "image/jpeg", "buffer": b"not-an-image"}
    )
    expect(phone.get_by_role("alert")).to_contain_text("could not be opened")


def test_api_ownership_duplicate_claims_and_delete(server):
    with (
        httpx.Client(base_url=server.url, timeout=30) as owner,
        httpx.Client(base_url=server.url, timeout=30) as stranger,
    ):
        menu = owner.post("/api/menus", json=upload_data()).json()
        assert "id" in menu, menu
        path = "/api/menus/" + menu["id"]
        assert stranger.get(path).status_code == 404
        assert owner.post("/api/menus", json=upload_data()).json()["id"] == menu["id"]
        image_path = path + "/dishes/1/image"
        before = counts(server)["image_submissions"]
        with ThreadPoolExecutor(3) as pool:
            responses = list(pool.map(lambda _: owner.post(image_path), range(3)))
        assert all(r.status_code == 200 for r in responses)
        assert counts(server)["image_submissions"] == before + 1
        result = wait_image(owner, image_path)
        assert result["status"] == "ready", result
        assert stranger.get(path + "/dishes/1/picture").status_code == 404
        image = owner.get(path + "/dishes/1/picture")
        assert image.status_code == 200
        Image.open(io.BytesIO(image.content)).verify()
        assert owner.delete(path).status_code == 200
        assert owner.get(path).status_code == 404
        assert owner.get(path + "/dishes/1/picture").status_code == 404


@pytest.mark.parametrize(
    "scenario,status",
    [
        ("image_timeout", "uncertain"),
        ("image_invalid", "failed"),
        ("image_failed", "failed"),
    ],
)
def test_image_failures_do_not_duplicate_paid_requests(server, scenario, status):
    with httpx.Client(base_url=server.url, timeout=30) as client:
        menu = client.post("/api/menus", json=upload_data()).json()
        path = f"/api/menus/{menu['id']}/dishes/1/image"
        mode(server, scenario)
        image = client.post(path).json()
        if image["status"] == "pending":
            image = wait_image(client, path)
        assert image["status"] == status, image
        if status == "uncertain":
            before = counts(server)["image_submissions"]
            assert client.post(path).json()["status"] == "uncertain"
            assert counts(server)["image_submissions"] == before


def test_request_guards(server):
    with httpx.Client(base_url=server.url) as client:
        assert (
            client.post(
                "/api/menus",
                json=upload_data(),
                headers={"Origin": "https://evil.invalid"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/menus",
                json={"pages": ["data:image/jpeg;base64,AAAA"], "language": "en"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/menus", json={**upload_data(), "language": "invalid"}
            ).status_code
            == 422
        )
        assert client.get("/api/unknown").status_code == 404


def test_model_markup_is_displayed_as_text(phone, server):
    mode(server, "unsafe_text")
    scan(phone)
    expect(phone.locator(".dish-card").first).to_contain_text(
        '<img src=x onerror="alert(1)">'
    )
    assert phone.locator('img[src="x"]').count() == 0


def test_known_image_failure_allows_only_one_explicit_retry(server):
    with httpx.Client(base_url=server.url, timeout=30) as client:
        menu = client.post("/api/menus", json=upload_data()).json()
        path = f"/api/menus/{menu['id']}/dishes/1/image"
        for attempt in [1, 2]:
            mode(server, "image_failed")
            assert client.post(path).status_code == 200
            image = wait_image(client, path)
            assert image["status"] == "failed" and image["attempts"] == attempt
        before = counts(server)["image_submissions"]
        assert client.post(path).status_code == 429
        assert counts(server)["image_submissions"] == before


def test_failed_scan_can_be_explicitly_retried_with_same_photo(phone, server):
    expect(phone.get_by_role("button", name="Upload menu", exact=True)).to_be_enabled()
    mode(server, "scan_unavailable")
    phone.get_by_label("Choose a menu file").set_input_files(MENU)
    expect(phone.get_by_role("alert")).to_contain_text(
        "AI service is unavailable", timeout=20000
    )
    before = counts(server)["scans"]
    scan(phone)
    assert counts(server)["scans"] == before + 1
