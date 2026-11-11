# SnapMenu handoff

The user wants a simple phone-browser tool: photograph a text-only menu, then see translated dish cards and illustrative pictures. Keep system fonts and a utilitarian single-screen flow. The main page does not scroll; two or four cards paginate. Long dialogs can scroll internally for accessibility.

After Cloudflare R2 activation failed in billing, the user explicitly authorized a move to Vercel and selection of Marketplace storage. Production now targets https://snapmenu-gamma.vercel.app in `ohong-projects/snapmenu`. Neon `snapmenu-db` and private Blob `snapmenu-images` are provisioned and linked. The Postgres migration passed. No unrelated database was modified and no Cloudflare resource was deleted.

The React screen and Muse/OpenAI provider contracts remain. `api/index.ts` is the Vercel function entry; `src/app.ts` is HTTP logic; `src/storage.ts` provides Neon transactions and private Blob access. The API uses an HTTP-only private browser session and seven-day expiry. Claims and usage records commit together; model calls never hold the transaction lock. Ambiguous image submissions never retry automatically.

No real Meta key is configured. Production `AI_PROVIDER=muse` selects Ember/Image. Add `MODEL_API_KEY` securely in Vercel project environment settings and redeploy to enable scans. The old OpenAI key was not copied and previously returned `account_deactivated`.

The five Terra menu collectors produced 50 distinct SF restaurant snapshots. Only selected text-menu pages become inputs: 53 JPEG pages, 211 dish checks, 184 price checks, 40 development cases and 10 holdout cases. Historical and sample menus are flagged. The corpus is not served to diners.

Verification drives the real Node API, Neon, private Blob, Chromium, and WebKit. Only external AI HTTP is simulated. See `docs/verification.md` for final results and limits. Deployment checks include the public alias, health/config/latest routes, cron authorization, and public mobile UI. No live model-quality claim is made.

Old local Python data, original Git history, the empty Cloudflare D1 database, and unrelated Neon resources remain untouched. No automatic legacy data or session migration occurs. The original archive path recorded in history was not rechecked.
