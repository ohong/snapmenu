# Architecture

## Current implementation

SnapMenu uses FastAPI, static HTML/CSS/JavaScript, SQLite, and direct HTTP calls to OpenAI. It needs one Python runtime, one worker, one replica, and persistent local storage. The interface uses system fonts and plain menu rows.

Menu reading uses `gpt-6-luna` through `POST /v1/responses`. It combines photo reading, translation, and structured extraction in one call. The request uses high-detail image inputs, low reasoning effort, strict JSON schema output, `store=false`, and a hashed browser-session safety identifier. Pydantic validates the result again. Refusals, incomplete output, invalid objects, and empty menus remain explicit errors.

Dish visualization uses `gpt-image-2.5-flare` through a forced image-generation tool in a Luna background Response. It requests one image, 1024 × 1024, medium quality, WebP output. No client can choose arbitrary provider URLs or send free-form paid prompts.

## Image API versus background Responses

The direct Image API is the simpler choice for a single foreground image. It avoids mainline-model orchestration costs. However, it does not expose a resumable task ID; a dropped response or server restart can leave an uncertain paid generation.

Background Responses adds mainline-model usage and provider-side response storage. It returns an ID that the app can persist before polling. Choose it to preserve SnapMenu's existing reload/restart recovery and avoid automatic duplicate paid requests. OpenAI supports Luna's image-generation tool and background response retrieval; live account compatibility remains unverified because the configured account is deactivated.

A future change to direct Image API calls must explicitly solve task recovery rather than quietly removing it.

## Boundaries

- `app.py`: private browser session, routes, same-origin writes, bounded concurrency, and image lifecycle.
- `config.py`: one `OPENAI_API_KEY`, menu/image model defaults, data path, budgets, and HTTPS cookie settings.
- `providers.py`: OpenAI request contracts, extraction validation, background response retrieval/cancellation/deletion, and sanitized errors.
- `media.py`: file decoding, PDF rendering, photo normalization, and bounded base64 image decoding. Images are written atomically to WebP; no generated URLs are fetched.
- `models.py`: validated menu and dish schema plus supported reading languages.
- `storage.py`: private menus, image task state, rolling usage limits, and seven-day expiry.
- `static/`: mobile browser interface. Extracted text is inserted using DOM text nodes.

## Image lifecycle

A unique `(menu_id, dish_id)` row moves through `starting -> pending -> ready / failed`, or `starting -> uncertain` if task creation cannot be confirmed. The row is claimed before the paid request. A known failure permits one explicit retry; an ambiguous submission cannot automatically create a replacement.

Pending tasks retain their `resp_` ID through reloads and restarts. A browser checks pending jobs every 5.5 seconds; the server shares a five-second minimum poll interval across tabs. At completion it decodes image bytes, writes a private WebP, marks the image ready, and requests deletion of the OpenAI response. Failed terminal responses are also deleted. Menu deletion requests cancellation and deletion of known pending OpenAI responses.

Response cleanup is best effort. `store=true` is required for the chosen long-lived recovery behavior; provider-side retention applies if local cleanup cannot run or fails. Closing the browser pauses polling and cleanup. Local menu expiry does not guarantee provider deletion. OpenAI account retention settings are separate from SnapMenu's seven-day local lifetime.

## Existing-data compatibility

The SQLite schema and private picture routes remain compatible with the earlier app. Existing completed WebP files remain readable. On startup, old pending non-OpenAI task IDs become `uncertain` with a visible message; they are neither polled against OpenAI nor resubmitted. The legacy Neon database is not read, reset, or migrated.

## API

| Method and path | Purpose |
| --- | --- |
| `GET /api/config` | Session cookie, languages, and key-presence flags; not an account validity check. |
| `GET /api/health` | Process and SQLite readiness. |
| `POST /api/menus?language=en` | Validate a multipart upload, normalize it, extract with Luna, and persist the menu. |
| `GET /api/menus/latest` | Latest private unexpired menu, or null. |
| `GET /api/menus/{id}` | One private menu. |
| `DELETE /api/menus/{id}` | Cancel pending image work and remove local menu/picture data. |
| `POST /api/menus/{id}/dishes/{dish}/image` | Start or reuse one image task. |
| `GET /api/menus/{id}/dishes/{dish}/image` | Recover and check its state. |
| `GET /api/menus/{id}/dishes/{dish}/picture` | Private local WebP. |

Requests use at most three extraction slots and three recent pending image tasks. SQLite stores global rolling-day limits and browser-hour limits. These are request caps, not dollar budgets. Use provider account spend controls for financial limits.

## Official contracts checked October 27, 2026

- [GPT-6 Luna: image input, Structured Outputs, reasoning effort, and tools](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [GPT Image 2.5 Flare: model ID and role](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare)
- [Structured Outputs with Responses](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Image tool options and forced tool choice](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [Background response retrieval and cancellation](https://developers.openai.com/api/docs/guides/background)

Both model metadata requests returned `401 account_deactivated` with the existing key. Documented support does not establish this account's access, output quality, latency, or cost.
