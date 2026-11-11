# SnapMenu

Photograph a restaurant menu and see the dishes in your language. Built for travellers and unfamiliar menus without food photos.

**Live:** https://snapmenu-gamma.vercel.app

One screen, system fonts, large touch controls. Choose a photo or PDF; reading starts immediately. Text appears first, then pictures fill in for visible dishes. Next/Back replace page scrolling. Tap a dish for original text, translation, and printed price.

## Runtime

- React, TypeScript, Vite, and Base UI for the mobile screen.
- One Vercel Node function for related API routes.
- [Neon](https://vercel.com/marketplace/neon) Postgres, provisioned through Vercel Marketplace, for private menus, task state, and request budgets.
- Private Vercel Blob for generated WebP pictures. Images pass through an ownership check; the bucket is not public.
- Vercel Cron for seven-day expiry, protected by `CRON_SECRET`.

The Vercel project is `snapmenu` in Pacific Systems (`ohong-projects`). Database, image storage, and functions use `iad1`. No Cloudflare activation or Python server is needed.

## Add the Meta key securely

Open [project environment variables](https://vercel.com/ohong-projects/snapmenu/settings/environment-variables). Add `MODEL_API_KEY` as a sensitive environment variable for Production. Then redeploy so the new environment is available.

Or use the masked CLI prompt:

```sh
vercel env add MODEL_API_KEY production --sensitive
vercel deploy --prod
```

Never paste the key into chat or place it in `VITE_*`. Without the key, the deployed sample works and real scanning stays visibly unavailable.

| `AI_PROVIDER` | Extraction | Dish images | Secret |
| --- | --- | --- | --- |
| `muse` (default) | `muse-ember-1.0` | `muse-image-1.0` | `MODEL_API_KEY` |
| `openai` | `gpt-6-luna` | `gpt-image-2.5-flare` | `OPENAI_API_KEY` |

Task rows retain their provider, so changing the flag cannot send an old response ID to the wrong service. Keep credentials for both providers while either has pending work. Menu extraction requests strict JSON schema output with `store=false`; background images use `store=true` for recovery. After saving images, the app requests provider-response deletion. Provider retention rules still apply.

## Local development

```sh
npm ci
vercel link
vercel env pull .env.local
npm run db:migrate
npm run dev:api
```

Vercel supplies the linked `DATABASE_URL` and `BLOB_READ_WRITE_TOKEN`. Add the AI key locally in ignored `.env.local` if needed. Environment files remain local; they do not configure production. Frontend-only hot reload can run with `npm run dev`; its API proxy targets port 8787.

The browser resizes photos to at most 1800 pixels. PDFs render locally, with PDF.js loaded only when selected. Original files may be up to 10 MB; normalized JSON uploads must fit within 4 MB for Vercel's request limit. Oversized page combinations ask for one page at a time. Unsupported HEIC files show an error. Up to three PDF pages and 100 dishes are supported.

## Privacy, recovery, and budgets

An HTTP-only cookie authorizes private menus for seven days. No account is needed. Original photos are not retained by SnapMenu. Text and pictures expire after seven days. Deletion removes app data and attempts to cancel pending provider tasks.

Only visible dishes start pictures, with up to three concurrently. Atomic Postgres claims prevent duplicate paid submissions across reloads and tabs. Ambiguous image submissions never retry automatically. A known failure allows one explicit retry. Selecting a photo again can explicitly retry a failed extraction.

Defaults: 100 scans and 100 pictures per rolling day across the app; 10 scans and 20 pictures per browser per hour. Settings survive function restarts. These are request caps, not currency budgets. AI pictures are estimates of appearance, not restaurant photos or allergy assurances. Prices remain as printed.

## Verification and evaluation

```sh
npm run check
npm test
```

QA requires Python browser tooling from `requirements-dev.txt`; Python is not part of production. The suite uses real Node, Neon, and private Blob storage in disposable `qa_*` schemas and `qa/` image prefixes. Only model HTTP is simulated. Never point these tests at unrelated databases. Test cleanup removes only its generated schema and prefix.

Five Terra agents collected [50 real text-only SF menus](evals/menus/README.md): 53 selected pages, 211 dish checks, and 184 printed-price checks. Original sources and provenance are preserved; some are historical or sample menus. The fixed split contains 40 development and 10 holdout cases.

```sh
.venv/bin/python evals/menus/prepare.py
.venv/bin/python evals/menus/run.py --url https://snapmenu-gamma.vercel.app --limit 5 --allow-paid
```

The default eval makes five extraction calls. `--images` adds at most five image requests and a human review rubric. Live model quality and latency remain unverified until a working provider key is configured. The existing OpenAI key previously returned `account_deactivated`; it was not copied into Vercel.

## Project references

[Architecture](docs/architecture.md) · [Operations](docs/operations.md) · [Product](docs/product.md) · [Verification](docs/verification.md) · [Release plan](docs/plan.md) · [Handoff](docs/pls-fix.md)

Cloudflare's empty D1 database and the older local Python data remain untouched. This release uses a separate, newly provisioned Neon database. It does not silently migrate old cookies, menus, or provider tasks.
