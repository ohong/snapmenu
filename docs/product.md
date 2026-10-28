# SnapMenu product specification

## Purpose

Help a diner understand a restaurant menu on their phone. A photograph becomes a readable menu in their chosen language. Optional dish images help explain unfamiliar food.

Oscar's current decisions: use GPT-6 Luna for menu understanding, GPT Image 2.5 Flare for dish visualization, and a utilitarian mobile browser experience. These replace the earlier Fireworks/Runway choice. The October 2026 rebuild replaces the old implementation, not the core promise.

## Essential journey

1. Take a photo or choose an existing file.
2. Choose a reading language.
3. Tap **Read my menu**.
4. Read translated dishes with original names and printed prices.
5. Search, filter categories, or tap a dish for its original text.
6. Optionally request a picture, save personal picks, or ask for a course suggestion.
7. Return after a reload, start another menu, or delete the current menu.

No login, onboarding tour, subscription gate, checkout, chat, or restaurant administration is required.

## Inputs and extraction

- One image or one PDF per scan. Maximum file size: 10 MB.
- JPEG, PNG, WebP, HEIC/HEIF, and AVIF decode locally. PDFs contain one to three pages.
- Images have at most 50 million pixels. Input is rotated using photo metadata, flattened onto white, and resized to fit 1800 × 1800.
- A single OpenAI Responses request using Luna extracts up to 100 dishes and translates names, descriptions, and categories.
- Original names, descriptions, printed order, and literal prices are retained. Prices may contain currency symbols, size variants, or text. There is no currency conversion or invented price.
- No readable dishes, incomplete JSON, truncated output, or provider failure produces an explicit error. The selected file remains available for retry.
- Model instructions prohibit invented ingredients and allergy claims. This is an instruction, not a proven accuracy guarantee.

## Reading and choosing

Menus preserve category order. Search matches original and translated names and descriptions. Dish detail shows both versions when they differ. Long names wrap. Right-to-left dish text uses automatic direction.

Picks are a personal shortlist saved in this browser's local storage. There is no order placement or cross-device synchronization. A course suggestion randomly selects one available starter, main, and dessert. If these courses are absent, it picks one available dish. It does not claim chef judgment or dietary suitability.

The sample menu is explicitly labeled and contains authored example dishes. It is independent of uploads, works without credentials, and never makes provider requests. It does not include generated or decorative food images.

## Pictures

A tap on **Generate image** starts one OpenAI background image response. The menu remains usable while it runs. A completed image is labeled **AI interpretation**. Pictures illustrate possible appearance, not the restaurant's actual serving or ingredients.

Task IDs are stored before polling and reused after reloads and server restarts. At most three recent image tasks are active at once. A known failed task permits one explicit retry. An ambiguous submission or interrupted creation cannot automatically submit again. This avoids duplicate paid requests when the original outcome is unknown.

Images are saved locally before they are displayed. Temporary provider URLs and task IDs are never sent to the browser. Image retrieval or local storage failure leaves a visible error and can be checked again without a new generation. The app decodes bounded base64 output rather than fetching generated URLs.

## Privacy and lifetime

No account is required. An unguessable HTTP-only cookie links a browser to its menus. The server stores only a hash of the cookie. Other browser sessions cannot fetch menus or pictures by guessing their IDs.

The original upload is not retained after processing. Its normalized pages are sent to OpenAI with `store=false`. Requested dish names and descriptions are sent to OpenAI. Image requests use background Responses with `store=true`; completed responses are deleted on a best-effort basis after local image storage. Provider retention is governed by the provider account and terms; SnapMenu does not claim to control it.

Menus become inaccessible after seven days. An hourly cleanup removes expired menus, task records, and picture files; startup and new scans also trigger cleanup. Picks are browser-local identifiers and may outlive expired menu data. Deleting a menu removes that menu and its pictures and requests cancellation of known pending image tasks. Cancellation cannot guarantee that incurred provider charges are reversed.

## Mobile and accessibility

The interface is utilitarian: system sans-serif text, direct instructions, standard controls, and a single-column menu list. It has no marketing hero, decorative artwork, or empty photo placeholders. The primary layout targets 320–430px phones and also adapts to tablet and desktop browsers. Native file input offers a rear-camera capture hint where supported. Standard file selection remains available.

Controls have accessible names, visible focus, and touch targets. Native dialogs contain focus and close with Escape. Content does not require hover. There is no decorative animation. Reduced-motion preferences disable smooth scrolling. There is no app installation requirement.

## Boundaries

No fifteen-second promise is made. Menu extraction and image generation have separate waits. There is no offline extraction, saved original photograph, guaranteed allergy detection, restaurant ordering integration, public sharing link, or imported Neon history.

Live model accuracy, phone-camera behavior, provider permissions, and hosted performance remain release checks. Engineering tests do not establish diner demand.
