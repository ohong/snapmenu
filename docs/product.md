# Product specification

## Promise

A diner photographs a text-only menu and sees an illustrated menu in their reading language. Useful when travelling or ordering unfamiliar dishes without restaurant photos.

## Current journey

1. Choose a reading language.
2. Take a photo or upload a photo/PDF. Reading starts immediately.
3. Read four dish cards per page, or two on short screens.
4. Pictures fill in automatically for visible dishes, up to three concurrently.
5. Use Next/Back or category selection to browse without page scrolling.
6. Tap a dish to read original text, translated description, and printed price.

The main page stays within the dynamic viewport. Dialogs and select popups can scroll internally for long text, text zoom, or small screens. Zoom remains enabled. Landscape and 320-pixel screens remain usable. No serif fonts, marketing sections, decorative artwork, empty menus presented as successful scans, or fabricated restaurant photos.

## Input and output

Photos must decode in the browser. Unsupported HEIC files get a useful error. PDFs support 1–3 pages. Maximum input file size is 10 MB; normalized JPEG pages are at most 1800 pixels. Browser resizing reduces upload time. The original photo is not saved by SnapMenu.

Menu reading supports English, Chinese, Spanish, Hindi, Arabic, Portuguese, Russian, Japanese, German, and French. The app controls use English. At most 100 dishes are extracted. Original names and descriptions, printed prices, source order, category, and warnings remain available. Model output must pass the shared schema before display.

Pictures are labeled as AI illustrations. They cannot verify actual plating, ingredients, allergens, portion size, or availability. No price conversion or inferred dietary certification.

## Provider choice

Default: Muse Ember for reading and Muse Image for pictures. Set the server provider flag to OpenAI to use Luna and Flare. This setting does not appear in the diner flow. Pending tasks retain their original provider.

## Privacy and cost controls

No accounts or public share links. Menus and R2 pictures require the originating browser cookie and expire after seven days. Changing devices or clearing cookies loses access. Deletion removes private app data and attempts provider cancellation/deletion. Background provider retention is disclosed.

Only visible dishes create new image requests. Reloads reuse persisted tasks; uncertain submissions never retry automatically. Failed images allow one explicit retry. The sample menu makes no model requests and is clearly labeled. Global daily and per-browser hourly request limits survive Worker restarts in D1.

## Acceptance conditions

- Upload or camera selection starts reading without a second submit step.
- No document scrolling at tested phone and landscape sizes.
- Extracted dishes become usable before image completion.
- Images appear without extra per-dish clicks.
- Reload and repeated requests do not duplicate a paid image submission.
- Cross-browser sessions cannot read, delete, or download another browser's menu.
- Provider failure produces a visible error rather than a substitute menu.
- No production Python service is required.

Search, personal picks, random meal suggestions, accounts, payments, restaurant lookup, and the Decisions API are outside the current screen. The old broader UI was removed to make the core task direct.
