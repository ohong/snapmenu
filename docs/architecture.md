# Architecture

```text
Phone: React / Base UI / Vite
  └─ Vercel Node API (api/index.ts)
       ├─ Muse or OpenAI Responses
       ├─ Neon Postgres: menus, claims, budgets
       └─ Private Vercel Blob: WebP images
```

The existing React screen and provider logic remain. A full Next.js rebuild was considered, but server rendering and extra routing do not improve this single upload screen. One Vercel function keeps related routes together and avoids a framework adapter. Neon and Blob replace D1 and R2. The user explicitly authorized the Vercel move after Cloudflare billing blocked R2 activation.

`src/app.ts` owns HTTP behavior. `src/storage.ts` owns parameter binding, database transactions, and private image access. The small query interface isolates storage mechanics without exposing SDK details to provider or frontend code. SQL parameters are numbered outside quoted strings. Quota/claim batches use a Postgres advisory transaction lock; external model requests run after commit, outside the lock. Unique constraints prevent duplicate menu/dish claims. Queries and Blob reads stay server-side.

The browser normalizes photos and renders PDFs. Original files are limited to 10 MB. Normalized JPEG pages are limited to 1800 pixels, at most three pages, and 4 MB combined JSON. Vercel's function request limit makes the combined limit necessary; the screen requests a single page when needed. PDF code loads lazily. The initial photo scan sends bytes directly to the selected AI provider without retaining the original upload.

Both extraction outputs pass a shared strict schema. Refusals, incomplete responses, empty dishes, and invalid data fail visibly. React escapes model text. No model response can choose an arbitrary fetch URL.

Muse uses Ember for extraction and Muse Image directly for background image responses. Muse image search, web search, and shell tools are disabled; reasoning strength is low. OpenAI uses Luna with a forced Flare image tool. Images use `background=true, store=true` so persisted task IDs survive reloads and server restarts. Every task saves its provider. Switching the default never reissues existing tasks.

Pictures start only for visible dishes, with three active tasks per browser. Unknown submission outcomes stay uncertain and never automatically retry. Pending tasks are polled while the tab is visible. Completed base64 output is bounded and checked for a WebP signature, stored privately, then marked ready. Provider response deletion follows successful persistence. Storage failures leave the provider task pending; known bad results fail. A database lease prevents overlapping provider polls.

A random HTTP-only, SameSite cookie authorizes ownership. It is Secure on HTTPS. Postgres stores only a hash. All menu, deletion, and image reads check ownership. Cross-origin mutations fail. Private pictures stream through the API and cache privately. Hashed static assets cache publicly. CSP permits same-origin scripts/connections and Base UI's inline positioning styles.

The hourly Vercel cron uses `CRON_SECRET` and deletes expired image objects and seven-day menu rows, attempting pending provider cancellation. Provider deletion remains best effort. Browser closure can defer image retrieval and provider deletion until return or expiry. This does not guarantee immediate physical erasure by the provider.

Neon, Blob, and functions are placed in iad1. Client resizing, lazy PDF parsing, concurrent visible images, and persisted results reduce work. Upload bandwidth, provider latency, database wake-up, network distance, and image polling remain measurable costs. No live model latency claim is established.
