"""Test-only provider simulation. Production never imports this module."""
import base64
import io
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import uvicorn
from PIL import Image
import app as product

stats = {"scans": 0, "image_submissions": 0, "polls": 0}
mode = {"next": "ok"}
tasks = {}


def menu(spanish=False):
    # Human transcription of example_menus/simple menu.jpg; not a production model result.
    names = ["Hand Tossed Salad", "Roast Beef with Mushroom Sauce", "Loaded Baked Potato", "Roasted Vegetables", "Fruit Salad", "Strawberry Cake", "Peach & Blackberry Cobble", "Tea/Coffee/Capuccino", "Soft Drinks", "Juices"]
    translated = ["Ensalada fresca", "Rosbif con salsa de champiñones", "Patata al horno", "Verduras asadas", "Ensalada de frutas", "Tarta de fresa", "Pastel de melocotón y moras", "Té/Café/Capuchino", "Refrescos", "Zumos"]
    dishes = []
    for i, name in enumerate(names):
        category, course = ("Salads", "starter") if i == 0 else ("Entrées", "main") if i < 5 else ("Desserts", "dessert") if i < 7 else ("Beverages", "drink")
        dishes.append(dict(name_original=name, name_translated=translated[i] if spanish else name,
            description_original="with ranch or thousand island" if i == 0 else "",
            description_translated=("con aderezo ranch o mil islas" if spanish else "with ranch or thousand island") if i == 0 else "",
            price="7$ / 6$" if i == 0 else "5$" if i == 8 else "2$" if i in {7, 9} else "7$", category=category, course=course))
    return dict(title="Your menu", source_language="English", warnings=[], dishes=dishes)


async def handle(request):
    assert request.url.host == "api.openai.com", "Unexpected external host"
    assert request.headers["authorization"] == "Bearer fixture-openai"
    if request.method == "DELETE":
        return httpx.Response(200, json={"deleted": True})
    if request.url.path.endswith("/cancel"):
        return httpx.Response(200, json={"status": "cancelled"})
    if request.method == "POST":
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-6-luna"
        assert payload["reasoning"]["effort"] == "low"
        assert len(payload["safety_identifier"]) == 64
        if "tools" in payload:
            stats["image_submissions"] += 1
            assert payload["background"] is True and payload["store"] is True
            assert payload["tool_choice"] == {"type": "image_generation"}
            assert payload["max_tool_calls"] == 1
            assert payload["tools"] == [{"type": "image_generation", "model": "gpt-image-2.5-flare", "action": "generate", "size": "1024x1024", "quality": "medium", "output_format": "webp", "output_compression": 85}]
            scenario, mode["next"] = mode["next"], "ok"
            if scenario == "image_timeout":
                raise httpx.ReadTimeout("simulated timeout", request=request)
            task = f"resp_fixture-{stats['image_submissions']}"
            tasks[task] = {"scenario": scenario, "polls": 0}
            return httpx.Response(200, json={"id": task, "status": "queued", "output": []})
        stats["scans"] += 1
        assert payload["store"] is False
        assert payload["text"]["format"]["type"] == "json_schema"
        assert payload["text"]["format"]["strict"] is True
        pages = [item["image_url"] for item in payload["input"][0]["content"] if item["type"] == "input_image"]
        stats["pages"] = len(pages)
        for page in pages:
            assert page.startswith("data:image/jpeg;base64,")
            Image.open(io.BytesIO(base64.b64decode(page.split(",")[1]))).verify()
        scenario, mode["next"] = mode["next"], "ok"
        if scenario == "scan_unavailable":
            return httpx.Response(503, json={"error": {"code": "fixture_failure"}})
        result = menu("Español" in payload["instructions"])
        if scenario == "empty": result["dishes"] = []
        if scenario == "unreadable": result["dishes"][0].pop("price")
        if scenario == "unsafe_text": result["dishes"][0]["name_translated"] = '<img src=x onerror="alert(1)">'
        content = [{"type": "refusal", "refusal": "Fixture refusal"}] if scenario == "refusal" else [{"type": "output_text", "text": json.dumps(result)}]
        return httpx.Response(200, json={"id": "resp_fixture-menu", "status": "incomplete" if scenario == "truncated" else "completed", "output": [{"type": "reasoning", "summary": []}, {"type": "message", "role": "assistant", "content": content}]})
    stats["polls"] += 1
    task = tasks.setdefault(request.url.path.split("/")[-1], {"scenario": "ok", "polls": 0})
    task["polls"] += 1
    if task["scenario"] == "image_failed":
        return httpx.Response(200, json={"status": "failed", "output": []})
    if task["polls"] == 1:
        return httpx.Response(200, json={"status": "in_progress", "output": []})
    image = io.BytesIO()
    Image.new("RGB", (160, 160), "#a6b68c").save(image, "WEBP")
    encoded = "not-a-base64-image" if task["scenario"] == "image_invalid" else base64.b64encode(image.getvalue()).decode()
    return httpx.Response(200, json={"status": "completed", "output": [{"type": "image_generation_call", "status": "completed", "result": encoded}]})


product.providers.client = httpx.AsyncClient(transport=httpx.MockTransport(handle), follow_redirects=False)


@product.app.get("/__fixture/stats")
def fixture_stats():
    return stats


@product.app.post("/__fixture/mode/{value}")
def fixture_mode(value: str):
    mode["next"] = value
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(product.app, host="127.0.0.1", port=int(os.environ["FIXTURE_PORT"]), log_level="warning")
