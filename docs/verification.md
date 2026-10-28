# Verification

## Exact source state

Baseline: `5e6edea`. The October 27 OpenAI migration and the preceding mobile rebuild are included in the requested commit/push. See Git history for the commit identity. Runtime and test source identity:

```text
SHA-256: 9bd4e26675f5a9a07fccf49e458af693482f29423108af565d2100ba375fc114
```

The digest includes 17 sorted files: root Python modules, all static assets, test Python files, both requirements files, Dockerfile, and pytest.ini. It hashes each relative path, a null byte, file bytes, and a null byte. Documentation and generated evidence are excluded.

```sh
python - <<'PY'
import hashlib
from pathlib import Path
paths = sorted([*Path('.').glob('*.py'), *Path('static').glob('*'), *Path('tests').glob('*.py'), Path('requirements.txt'), Path('requirements-dev.txt'), Path('Dockerfile'), Path('pytest.ini')], key=str)
h = hashlib.sha256()
for path in paths:
    h.update(str(path).encode() + b'\0' + path.read_bytes() + b'\0')
print(h.hexdigest())
PY
```

## Automated acceptance

The tests start a real Uvicorn server, drive real Chromium and WebKit browsers, decode actual files, and persist data in temporary SQLite storage. Only external provider HTTP responses use a test-only `httpx.MockTransport`. Production has no fixture flag, fixture endpoint, or hidden sample fallback. Test fixture keys are inert strings.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium webkit
pytest --browser chromium --browser webkit --tb=short --junitxml=test-results/junit.xml
```

October 27 result: the focused Chromium run passed **16 checks in 104.12 seconds**. The combined Chromium/WebKit run passed **31 checks in 222.48 seconds**. Earlier mobile revisions passed 27 checks; the OpenAI migration adds refusal and malformed generated-image cases. Screenshots show the real utilitarian interface with simulated provider responses. The generated JUnit report is `test-results/junit.xml` (ignored by Git).

| Acceptance condition | Evidence and scope |
| --- | --- |
| Mobile controls and no horizontal overflow | Sample journeys at 320, 390, 768, and 1280px in Chromium and WebKit. Includes camera capture hint, dialog, saved pick, and privacy notice. |
| Extraction reaches the interface | Actual sample JPEG passes upload decoding and reaches a simulated OpenAI Responses boundary. Spanish dish text, original names, printed price variants, and ten dishes render in the real UI. This does not verify OCR or translation quality. |
| Search, filtering, detail, and choices | Searches original text within a translated menu, filters four entrées, checks empty results, saves a pick, reloads, and opens course suggestions. The sample cannot replace the real saved menu. |
| Image lifecycle and no duplicate submission | Simulated OpenAI background response runs through pending, reload, base64 output decoding, private WebP delivery, and server restart. One generation submission remains one. Known failure permits retry; ambiguous timeout cannot submit a replacement. |
| Session isolation and deletion | Another browser receives 404 for private menu and image. Cross-origin deletion receives 403. Deleting through the UI makes the menu inaccessible after refresh. |
| Failure and recovery | Service failure, empty extraction, missing required fields, and truncated model output, and model refusal remain errors. Invalid generated-image bytes also produce a retryable image failure. Retry retains the original file. Invalid image bytes are rejected. Model-supplied HTML is rendered literally. |
| Bounds | Two-page PDF renders both pages; oversize request, unsupported language, and per-browser scan limit are rejected through public HTTP endpoints. |

These expectations include a human transcription of `tests/example_menus/simple menu.jpg`. The fixture cannot establish provider behavior. Its generated picture is a flat color test image, not evidence of food-image quality.

## Other checks actually run

- During the earlier rebuild, a new Python 3.12 environment installed all 22 pinned production packages and imported the app. The OpenAI migration adds no packages.
- During the earlier rebuild, the clean environment started the HTTP server and served the homepage, config, and health endpoints. A real JPEG upload without keys returned 503 and left the latest menu empty. It never substituted sample data.
- During the earlier rebuild, actual JPEG, PNG, WebP, HEIC, and AVIF codec round trips succeeded. A four-page PDF was rejected.
- Python compilation, `node --check static/app.js`, unique HTML IDs, and `git diff --check` passed.
- General inspected the desktop app and mobile screenshots, then manually exercised sample-menu search in the app browser. Search visibly reduced the menu to the matching dish.
- Container build and execution were not repeated for this migration; they remain unverified. The earlier run found the Docker daemon unavailable.

Screenshots `screenshots/mobile-start.png` and `screenshots/mobile-menu.png` come from the explicitly simulated browser run. They show the real interface at 390px. They do not show live provider results.

## Required live provider acceptance

Oscar authorized reuse of the existing `OPENAI_API_KEY`. Direct GET requests to the `gpt-6-luna` and `gpt-image-2.5-flare` model metadata endpoints both returned HTTP 401 with `account_deactivated`. An active project key is required. No paid generation, successful extraction, image quality assessment, Decisions evaluation, staging check, or deployment occurred. Supply the replacement through the server environment, not browser code or chat.

1. Start the normal app with valid keys and confirmed spending authority.
2. Upload `tests/example_menus/simple menu.jpg`. Compare every dish and printed price with the image. Expect the salad, four entrées, two desserts, and three beverage entries. The salad's printed price variant must survive without invented decimal conversion.
3. Repeat using Spanish, then a non-English menu with English as target. This checks the old English-target translation failure. Independently read and compare the source photograph.
4. Use the Italian and Hideki sample photographs as additional cases. Check small text, categories, prices, omissions, and unreadable sections. Record actual failures rather than silently correcting the result for the demo.
5. Request one GPT Image 2.5 Flare picture. Check successful task creation, completed base64 output decoding, a useful food depiction, and the visible AI label. Refresh during generation; confirm that no second paid submission occurs.
6. Confirm private access from another browser and delete the test menu. Check local picture removal and pending-task cancellation behavior.
7. Record elapsed time, request counts, provider-reported usage/cost, and usefulness for each live case. No latency or quality target is established by the simulated suite.
8. Deploy one HTTPS instance with persistent storage, then repeat camera/file input and essential journeys on physical iPhone Safari and Android Chrome. Verify a complete backup and restore on safe data.

## Release status

Implemented and locally exercised, with real provider acceptance blocked by the deactivated OpenAI account. Not deployed. Physical phone camera, live model quality, provider account access, hosted reliability, Docker, and backup/restore remain explicit gaps. No independent agent review was performed because Oscar requests work in this chat without delegation.


## OpenAI contract coverage

The simulated boundary checks the Luna model, low reasoning effort, high-detail JPEG page inputs, strict Responses `text.format`, and `store=false` for menu extraction. It checks the Flare tool model, medium 1024 × 1024 WebP settings, forced image tool, one tool call, background mode, explicit response storage, and the hashed session safety identifier. The same fake transport handles response retrieval, cancellation, and deletion; no alternate production endpoint or fixture flag is added.
