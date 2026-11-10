"""Evaluate the running app API against real source snapshots. Calls cost provider usage."""

import argparse
import base64
import hashlib
import json
import re
import statistics
import time
import unicodedata
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent


def normalized(text):
    return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKD", text).casefold())


def price_normalized(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())


def score(case, menu):
    dishes = menu["dishes"]
    hits = []
    for anchor in case["anchors"]:
        name = normalized(anchor["name"])
        candidates = [
            d
            for d in dishes
            if name == normalized(d["name_original"])
            or name in normalized(d["name_original"] + " " + d["description_original"])
        ]
        hits.append(
            {
                "name": anchor["name"],
                "found": bool(candidates),
                "printed_price": anchor["price"],
                "price_matches": not anchor["price"]
                or any(
                    price_normalized(anchor["price"]) == price_normalized(d["price"])
                    for d in candidates
                ),
            }
        )
    return {
        "anchor_hits": sum(x["found"] for x in hits),
        "anchor_count": len(hits),
        "price_hits": sum(
            x["found"] and x["price_matches"] for x in hits if x["printed_price"]
        ),
        "price_count": sum(bool(x["printed_price"]) for x in hits),
        "checks": hits,
    }


def render_image(client, menu, output_dir):
    dish = menu["dishes"][0]
    endpoint = f"/api/menus/{menu['id']}/dishes/{dish['id']}/image"
    started = time.perf_counter()
    response = client.post(endpoint)
    if not response.is_success:
        return {"status": "request_failed", "http_status": response.status_code}
    image = response.json()
    while (
        image["status"] in ["starting", "pending"]
        and time.perf_counter() - started < 180
    ):
        time.sleep(1.5)
        response = client.get(endpoint)
        response.raise_for_status()
        image = response.json()
    result = {
        "dish": dish,
        "status": image["status"],
        "seconds": round(time.perf_counter() - started, 3),
        "rubric": {
            "main_ingredient_matches": None,
            "preparation_matches": None,
            "serving_style_plausible": None,
            "adds_unsupported_ingredients": None,
            "notes": "",
        },
    }
    if image["status"] == "ready":
        picture = client.get(image["url"])
        picture.raise_for_status()
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / (menu["id"] + "-" + dish["id"] + ".webp")
        target.write_bytes(picture.content)
        result["file"] = str(target)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8787")
    parser.add_argument(
        "--split", choices=["development", "holdout", "all"], default="development"
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="test-results/menu-eval.json")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument(
        "--images",
        action="store_true",
        help="Generate one dish image for each of the first five successful menus, at additional provider cost.",
    )
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error(
            "Add --allow-paid to authorize the selected extraction calls. Images are requested only when --images is also supplied."
        )
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")
    cases = json.loads((ROOT / "cases.json").read_text())
    selected = [c for c in cases if args.split == "all" or c["split"] == args.split][
        : args.limit
    ]
    records = []
    with httpx.Client(base_url=args.url, timeout=180) as client:
        config = client.get("/api/config")
        config.raise_for_status()
        provider = config.json()["provider"]
        for case in selected:
            pages = []
            for entry in case["inputs"]:
                data = (ROOT / entry["file"]).read_bytes()
                assert hashlib.sha256(data).hexdigest() == entry["sha256"]
                pages.append(
                    "data:image/jpeg;base64," + base64.b64encode(data).decode()
                )
            started = time.perf_counter()
            response = client.post(
                "/api/menus", json={"pages": pages, "language": "en"}
            )
            elapsed = time.perf_counter() - started
            row = {
                "case": case["id"],
                "provider": provider,
                "split": case["split"],
                "status": response.status_code,
                "seconds": round(elapsed, 3),
                "server_timing": response.headers.get("server-timing", ""),
                "upload_bytes": sum(x["bytes"] for x in case["inputs"]),
            }
            if response.is_success:
                menu = response.json()
                row.update(score(case, menu))
                row["menu"] = menu
                row["cached"] = not bool(row["server_timing"])
                if args.images and len([r for r in records if "image_review" in r]) < 5:
                    try:
                        row["image_review"] = render_image(
                            client, menu, Path(args.out).parent / "menu-eval-images"
                        )
                    except httpx.HTTPError as error:
                        row["image_review"] = {
                            "status": "retrieval_failed",
                            "error": type(error).__name__,
                        }
            else:
                row["error"] = response.text[:500]
            records.append(row)
            print(case["id"], response.status_code, round(elapsed, 2), flush=True)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n"
            )
            # Stop on auth/rate/provider failure instead of burning the remaining run budget.
            if response.status_code in [429, 503]:
                break
    good = [r for r in records if r["status"] == 200]
    times = [r["seconds"] for r in good if not r.get("cached")]
    summary = {
        "provider": provider,
        "attempted": len(records),
        "selected": len(selected),
        "completed": len(good),
        "anchor_recall_on_success": (
            sum(r["anchor_hits"] for r in good) / sum(r["anchor_count"] for r in good)
        )
        if good
        else None,
        "printed_price_accuracy_on_success": (
            sum(r["price_hits"] for r in good) / sum(r["price_count"] for r in good)
        )
        if sum(r["price_count"] for r in good)
        else None,
        "uncached_median_seconds": statistics.median(times) if times else None,
        "limits": "Partial anchor checks, not exhaustive recall or hallucination measurement. Cached responses are reported and must be excluded from latency comparisons.",
    }
    target.write_text(
        json.dumps(
            {"summary": summary, "records": records}, ensure_ascii=False, indent=2
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
