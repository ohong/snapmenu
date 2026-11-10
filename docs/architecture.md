# Architecture

React, TypeScript, and Base UI form a static single-page frontend. Vite creates hashed assets. A TypeScript Cloudflare Worker handles same-origin API routes. D1 stores menus, image task state, and request usage. A private R2 bucket stores WebP image bytes. No frontend or backend framework adapter is required.

## Why this stack

Two approaches were considered. Keeping FastAPI preserves proven local codecs and SQLite behavior, but requires a server with a persistent disk. A TypeScript Worker removes that server and matches the requested Cloudflare target, but requires new storage contracts and browser-side PDF/image preparation. The user chose Worker/D1/R2. Next.js could host a similar app, but its server rendering and routing add little to this one-screen upload tool. A static React app plus Worker keeps the deployment smaller and direct.

## Request path

The browser decodes a selected photo, respects orientation, resizes it, and encodes JPEG at quality 0.85. Browser PDF.js renders up to three pages; its code and worker load on demand. The Worker limits JSON body bytes, checks JPEG markers/dimensions, validates language, and hashes provider/model/language/pages for deduplication. This is structural input checking, not an independent server-side image decode. Providers must still reject corrupt image content.

Extraction sends image content to the selected provider's fixed `/v1/responses` endpoint with strict JSON schema output, low reasoning effort, and `store=false`. A shared Zod schema validates output at runtime and supplies frontend types. Refusals, incomplete output, schema errors, and empty dishes fail visibly.

Muse defaults: `muse-ember-1.0` and `muse-image-1.0`. OpenAI defaults: `gpt-6-luna` and `gpt-image-2.5-flare`. Each provider uses its own secret and fixed origin. Arbitrary URLs and credentials never reach browser code.

## Background image recovery

Each image claim is persisted before submitting a paid request. D1 transaction batches claim the task and record quota usage together. A unique menu/dish key prevents duplicate requests across tabs. Provider name and response ID stay together. Switching the provider flag changes only new tasks.

Muse Image is the Responses model itself. Its image tool uses low reasoning strength, square aspect ratio, WebP, and disabled search/shell tools. OpenAI uses Luna with a forced Flare image tool, medium quality, square output, and WebP. Both use `background=true` and `store=true`.

Synchronous Images endpoints were considered. They remove background state handling, but interrupted requests can leave no retrievable result handle. Responses preserves recovery by ID. No automatic retry follows an ambiguous paid timeout.

The browser starts at most three visible dish tasks and checks pending tasks every 1.5 seconds while the tab is visible. Completed tasks are stored as WebP bytes in R2, then marked ready in D1. The Worker checks base64 length and RIFF/WEBP signatures; it never fetches model-generated URLs. It requests response deletion after persistence. Invalid output fails; storage failure remains pending for recovery. A 45-second D1 lease prevents overlapping provider polls. Deletion races cancel newly accepted tasks or remove orphan picture bytes.

There is no global limit on accepted pending generation tasks. There is a short-lived cap of twelve submissions in flight, plus daily/hourly request budgets. An abandoned browser cannot occupy a shared pending-generation queue. The provider still controls its own capacity and rate limits.

## Privacy and retention

A random cookie is HTTP-only, SameSite=Lax, Secure on HTTPS, and scoped to `/`. D1 stores only its SHA-256 hash. Every menu and picture request checks ownership. Cross-origin mutations fail. Private data responses are not publicly cached; pictures can cache privately for an hour. Static hashed assets cache for a year. CSP limits scripts and connections to the same origin; inline styles support Base UI positioning.

Menus expire after seven days. The hourly scheduled handler removes expired R2 objects, attempts pending-response cancellation/deletion, and deletes expired D1 rows. Provider deletion is best effort. Returning to a menu polls its pending tasks; closing the browser delays retrieval until return or expiry cleanup. Menu deletion does not revoke already cached bytes from a user's own device. Provider retention policies still apply.

The original Python data store is not migrated automatically. Existing files and credentials remain untouched. No legacy provider task is silently reissued.

## Performance boundaries

- Local JPEG resizing reduces bytes before the network upload.
- PDF parsing stays out of the initial JavaScript chunk.
- Text display does not wait for pictures.
- Visible dish pictures generate concurrently, without rendering all 100 dishes.
- Persisted tasks and pictures avoid repeated model work.
- No polling occurs while the page is hidden.
- Extraction returns `Server-Timing` for preparation and model/persistence work.

The `model` timing currently includes output validation and final D1 persistence. It is not pure provider compute time. Background pictures add up to a polling interval before display. Browser decoding, upload bandwidth, network distance, storage, and cold starts remain real costs. Production latency has not been measured; no claim that provider latency is the sole remaining delay is made.
