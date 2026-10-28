# Release plan

## Implemented locally

- Replace competing Streamlit/Pixtral/FLUX paths with one Python API and mobile browser interface.
- Read and translate with `gpt-6-luna`; generate dish images with `gpt-image-2.5-flare` through recoverable background Responses.
- Preserve literal prices and original text; remove silent sample fallbacks.
- Persist private menus, image tasks, and completed image files.
- Add explicit error recovery, request budgets, and menu expiry.
- Rewrite product, architecture, setup, and operating documentation.
- Exercise browser journeys and failure states with test-only provider responses.

Exact verification results and remaining gaps are recorded in `verification.md` and the revival handoff `pls-fix.md`.

## Required before a public release

1. Replace the deactivated OpenAI account key with an active project key, and confirm model access and budgets.
2. Complete the live provider checks in `verification.md` using the supplied sample menu photographs.
3. Inspect extraction and translations against the photographs. Reject invented dishes, altered prices, or hidden omissions.
4. Request one real dish image. Inspect quality, label, base64 output storage, reload, and task reuse.
5. Deploy one instance with HTTPS, a persistent data volume, request limits, and provider budget caps.
6. Test camera capture and file selection on physical iPhone Safari and Android Chrome.
7. Repeat essential journeys against the hosted version, then verify backup and restore.

## Later, only with evidence

Restaurant sharing, accounts, cross-device history, public menus, and automatic image batches are not part of this release. Revisit them only when actual use justifies the added cost and complexity. Importing legacy Neon history is a separate authorized migration, not an automatic setup step.

## Decisions API follow-up

The [integration proposal](decisions.md) covers optional preference-based dish ranking and photo quality checks. Keep these out of the default paid flow until held-out examples show a useful improvement. The current course suggestion remains a free random selection.
