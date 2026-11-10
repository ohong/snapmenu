# Verification

## Final local run

November 10, 2026: `npm run check` passed. The production Vite build and Cloudflare deployment dry run passed. The local D1 migration applied successfully. The combined real-browser/API suite passed **72 checks in 53.39 seconds**:

```sh
npm run test:prepare
.venv/bin/pytest --browser chromium --browser webkit --tb=short --junitxml=test-results/junit.xml
```

Both `AI_PROVIDER=muse` and `AI_PROVIDER=openai` run in Cloudflare's real local Worker runtime with D1 and R2. The external paid provider HTTP boundary alone is simulated by the test harness. It checks fixed provider origins, model IDs, schema requests, extraction storage settings, background image requests, Muse tool settings, and OpenAI image-tool settings. Production has no fixture routes or simulation flag.

The browser suite verifies automatic reading after file selection, language changes, category selection, pagination, image appearance, reload reuse, original text, no-scroll layouts at 320×568, 390×844, 768×1024, and 844×390, real PDF rendering, invalid uploads, model refusals, incomplete JSON, escaped model markup, missing dishes, and provider failures, and explicit retries of the same photo after a failed scan. API checks verify ownership, duplicate concurrent image claims, private R2 image delivery, deletion, uncertain submissions, corrupt image output, known failures, one explicit image retry, and request guards.

Screenshots under `docs/screenshots/` show the current UI. The green picture blocks are test-only image bytes, not live model output. They demonstrate layout and delivery, not image quality. No physical iPhone or Android device was tested.

A separate Chromium smoke check ran against actual `wrangler dev` static asset delivery, including its CSP. Base UI category selection and the dish dialog worked without page errors. `/api/health` and `/api/config` returned 200. Manually triggering the local scheduled handler returned 200 on an empty local store. Expiry with populated remote data, backup restoration, and hosted R2 delivery remain unverified.

## Real-menu corpus

Offline preparation validated 50 distinct restaurants, source hashes, and normalized files: **53 JPEG pages, 211 dish anchors, 184 price anchors**, with 40 development cases and 10 fixed holdout cases. Source collectors visually inspected menu pages or captured regions for dish photos. The corpus contains original restaurant files and genuine browser screenshots; it is not synthetic test content. Some menus are historical or samples. See `evals/menus/README.md`.

The extraction runner was checked against the local unconfigured Muse runtime. It stopped after the first HTTP 503 with zero completed cases and no model request. The optional image-review helper also completed a real local Worker/D1/R2 HTTP flow using simulated image output. These checks validate runner plumbing and failure handling only. No accuracy or latency result exists for live Muse or OpenAI inference.

## Credential and deployment limits

No Meta `MODEL_API_KEY` is configured locally. A read-only metadata request with the existing OpenAI key returned HTTP 401 `account_deactivated` on November 10. No paid extraction or image generation was run. D1 snapmenu was created in the Side Projects account on November 10, and the remote initial migration passed (8 commands). R2 bucket creation failed because R2 is not enabled (Cloudflare code 10042). No Cloudflare release was deployed. The checked-in D1 ID now references the provisioned database. Runtime code is unchanged from the 72-check run; release configuration and local-secret documentation were updated afterward.

The initial browser JavaScript bundle is about 120 kB gzip. PDF.js and its worker load only for PDF input. This is a build artifact size, not a measured mobile startup time. Provider quality, model access, real-device upload time, first-text latency, first-image latency, browser HEIC compatibility, provider retention, and production capacity require live checks.

## Reproduce the source identity

Run `node scripts/source-digest.mjs`. It hashes sorted paths, a NUL separator, file bytes, and a trailing NUL. It includes runtime code, dependencies, QA, migrations, and corpus artifacts. It excludes documentation, screenshots, secrets, and generated builds. Final SHA-256: `90f7efc75b34b46257f29c142e2832924a97b9fd110abb04650285d1bea07f49` across 196 files.
