# Operations

## Local setup

`npm ci`, copy `.dev.vars.example` to ignored `.dev.vars`, add a provider key, then run `npm run build`, `npm run db:local`, and `npm run dev:worker`. The Worker serves the built frontend at port 8787. `npm run dev` provides frontend hot reload with an API proxy.

Runtime configuration is in `wrangler.jsonc`. Use `AI_PROVIDER=muse` or `openai`. Muse reads `MODEL_API_KEY`; OpenAI reads `OPENAI_API_KEY`. Optional `MUSE_MENU_MODEL`, `MUSE_IMAGE_MODEL`, `OPENAI_MENU_MODEL`, and `OPENAI_IMAGE_MODEL` override defaults. Never use Vite-prefixed secret variables.

## Provision and release

The checked-in database ID is a placeholder, not a provisioned resource. Create D1 `snapmenu` and R2 `snapmenu-images` in the intended account, replace the D1 ID, apply migrations remotely, add provider secrets through `wrangler secret put`, and deploy with `npm run deploy`. Verify the account with `wrangler whoami` first. The existing local OAuth session points to the Side Projects account; recheck before provisioning.

Keep R2 private. Do not expose a bucket public URL. Serve pictures only through the authenticated Worker route. The cron runs hourly at minute 17. Keep both provider secrets available if there are pending tasks from both providers.

Before public launch, set account/provider spending limits, run the five-case live evaluation, check a real phone, test deletion, confirm scheduled expiry, and verify deployed bindings. Local workerd tests and a deployment dry run do not prove these conditions.

## Budgets and failures

Defaults: 100 scans/day, 100 pictures/day, 10 scans/hour/browser, 20 pictures/hour/browser. Failed submissions count. Limits are rolling windows in D1. `HOURLY_SCAN_LIMIT` and `HOURLY_IMAGE_LIMIT` can override the per-browser defaults. For a deliberate 50-menu local evaluation, set the local scan cap to 60; do not copy that override into production. Set a daily limit to zero to stop new paid requests without breaking saved-menu reading. D1 transaction batches make claim and usage updates atomic.

An interrupted image submission becomes uncertain and never automatically retries. Known failed images allow one explicit retry. A stale starting request becomes uncertain after two minutes when checked. Background tasks retain their provider even if the configured default changes.

A `503` can mean missing credentials, provider authorization, quota, or provider availability. Logs record safe status information, never provider keys or complete menu payloads. Check `/api/health` for D1 availability; it does not test R2 or model credentials. Provider failures need a live credentialed check.

## Backup and recovery

Export D1 before schema changes with `wrangler d1 export snapmenu --remote --output <backup.sql>`. Protect backups as private menu data. Back up R2 objects with their original `menu-id/dish-id.webp` keys if persistence beyond the short retention window matters. Restore D1 and R2 together into a separate environment, then exercise ownership and image retrieval before promotion. Restore has not been verified in this rebuild.

The old ignored `data/` directory and `.env` are untouched. This release does not import old SQLite data, cookies, or generated files into D1/R2. Keep the old checkout from Git history if existing local sessions must remain available. Do not overwrite or remove legacy data as part of deploying this version. Older Neon infrastructure remains outside the deployment and needs a separate review before deletion.

## Rollback

Keep the previous Worker version and D1 export before deployment. Roll back the Worker only when its schema remains compatible. The initial Cloudflare schema is additive and separate from the old SQLite database. A Worker rollback does not roll back provider charges or generated objects. Do not replay uncertain submissions during recovery.

## Credentials now

No Meta key is present locally. The existing OpenAI key returned HTTP 401 `account_deactivated` on November 10, 2026. These checks made no paid generation requests. Runtime tests use inert fixture credentials and intercept only external AI HTTP. Never put real keys into the test fixture.
