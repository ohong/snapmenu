# Operations

Production: https://snapmenu-gamma.vercel.app
Project: `ohong-projects/snapmenu` (Pacific Systems). Vercel project ID: `prj_YjtkMWXmnbOB6RZPtFJYhcY7vQaT`.

Neon `snapmenu-db` was provisioned through Vercel Marketplace using the existing integration's default plan. The initial attempt to select Free was rejected because it would downgrade an existing account with a branch above the free limit; no existing data was changed. Provisioning without a plan override succeeded. Private Blob `snapmenu-images` is linked. Both resources and functions use iad1.

## Secrets

Add `MODEL_API_KEY` as a sensitive Production environment variable in Vercel project Settings → Environment Variables. Redeploy afterward. Alternatively run `vercel env add MODEL_API_KEY production --sensitive` and enter it in the masked prompt. Do not send credentials in chat. OpenAI uses `OPENAI_API_KEY` when `AI_PROVIDER=openai`.

`DATABASE_URL` and `BLOB_READ_WRITE_TOKEN` are supplied by the linked resources. `CRON_SECRET` is generated and installed in Production. No real AI key was copied into Vercel. `AI_PROVIDER=muse` is configured in Production.

Use `vercel env pull .env.local` for local development. This file is ignored. Never put backend secrets in Vite-prefixed variables. `npm run dev:api` runs Vercel locally. `npm run dev` provides frontend hot reload with the API proxy at port 8787.

## Migrations and release

`npm run db:migrate` applies the additive Postgres schema using local linked credentials. Use the intended environment's credentials, and export a backup before changing populated schemas. The new SnapMenu database began empty. Tests use uniquely named disposable schemas and private Blob prefixes inside that database; they never delete public application tables.

Run `npm run check` and `npm test`, then `vercel deploy --prod`. Verify the public alias, `/api/health`, `/api/config`, saved-menu route, and unauthorized maintenance rejection. Test the public mobile screen. Build success alone does not establish runtime health or model access.

The cron is configured in `vercel.json`, hourly at minute 17. It requires an Authorization bearer token matching `CRON_SECRET`. Requests without that secret return 401. Keep both AI provider credentials configured while either provider has pending tasks.

Daily limits default to 100 scans and 100 pictures. Hourly browser limits default to 10 and 20. `DAILY_SCAN_LIMIT`, `DAILY_IMAGE_LIMIT`, `HOURLY_SCAN_LIMIT`, and `HOURLY_IMAGE_LIMIT` override these. A zero daily limit stops new paid requests. For a full local 50-menu evaluation, deliberately set the local hourly scan cap to 60. Do not copy that override into production by accident.

## Recovery and old resources

Postgres and private Blob objects must be backed up/restored together. Validate ownership and image retrieval in a separate environment after restoring. Restore has not been exercised. A Vercel rollback does not undo schema changes, image writes, or provider charges. Never replay uncertain submissions.

The empty Cloudflare D1 resource `snapmenu` (`4db9f5b6-f399-4bfa-b8f8-a07d41ed7e85`) remains untouched. R2 was never activated. The app has no dependency on either. Older local `.env`, `data/`, and unrelated Neon resources also remain untouched. This version does not migrate old sessions or menus.

## Diagnostics

`/api/health` checks the actual database. It does not prove Blob or model access. Use `vercel logs --project snapmenu --since 1h --json` for current runtime errors; startup failures can appear at info level with stderr content. Logs must never contain credentials or complete private menu payloads.

Production storage is provisioned and migrated. AI scanning remains unavailable until a working provider key is added. The existing local OpenAI key previously returned HTTP 401 `account_deactivated`.
