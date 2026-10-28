# SnapMenu handoff

## Current brief and authority

On October 16, 2026, Oscar requested a mobile web rebuild, provider replacement, and current product docs. Oscar then requested a utilitarian interface with system fonts and no decorative serif design. On October 27, Oscar requested current OpenAI models, a Decisions API proposal, and a commit/push of all latest changes. Oscar authorized reuse of the existing local OpenAI key.

The core promise remains: photograph a menu, read translated dishes alongside original names and printed prices, and optionally visualize a dish. Work and review stay in this chat without delegated agents.

## Preservation and history

The original source baseline is `5e6edea`. The earlier clean archive is `/Users/ohong/.codex/backups/snapmenu-2026-10-16/source.tar`. Git history preserves replaced implementations. The license, sample menu photographs, existing local settings edit, original `.env`, and legacy Neon resources are preserved. The requested commit includes the existing tracked local settings change; credentials and runtime data remain ignored.

The original app had competing Streamlit/Pixtral/FLUX implementations. Failed reading silently substituted a sample menu. The rebuild retired these paths and removed the false claim that fallback sample content proved extraction worked. The initial Fireworks/Runway replacement is now superseded by Oscar's OpenAI request.

## Chosen architecture

FastAPI plus static HTML/CSS/JavaScript keeps one runtime and gives full control over the small phone interface. Repairing Streamlit would retain mobile-layout and rerun constraints. A JavaScript framework would add a second runtime and build pipeline. SQLite holds private browser-session menus, image state, and usage caps on persistent storage. Run one worker and one replica.

Luna (`gpt-6-luna`) reads and translates menu pages in one Responses request with strict structured output and `store=false`. GPT Image 2.5 Flare (`gpt-image-2.5-flare`) generates dish images through a forced image tool in a Luna background Response. This preserves durable task IDs at the cost of mainline-model usage and provider-side response storage. Direct Image API calls are simpler but do not expose resumable task IDs.

Completed image bytes are saved atomically to private WebP files. The app requests deletion of completed or cancelled OpenAI image responses. Provider deletion is best effort and separate from local expiry. Old completed pictures remain readable; old pending non-OpenAI task IDs become unavailable and are never automatically resubmitted.

## Acceptance

- Phone users can take/select a photo, choose a language, read progress, and browse without horizontal overflow.
- Original names and literal prices survive. Empty, refused, truncated, or malformed extraction remains an error; no sample substitution occurs.
- Search, category filters, details, saved picks, and random course suggestions work.
- Requested images have explicit pending, ready, failed, and uncertain states. Reloads and restarts reuse known OpenAI response IDs. Ambiguous paid submissions do not automatically retry.
- Private sessions isolate menus and images. Menus expire after seven days and can be deleted.
- Upload size, page count, codecs, and request budgets are bounded. Setup, diagnostics, recovery, and current limits are documented.

The final combined run passed 31 Chromium, WebKit, and API checks with simulated OpenAI responses. See `docs/verification.md` for source identity, commands, observed results, and explicit gaps.

## Current limits and next action

Both OpenAI model metadata endpoints rejected the existing key with `401 account_deactivated` on October 27. No paid extraction, image generation, or Decisions evaluation ran live. An active OpenAI project key is needed before those checks can complete. No account was provisioned and no deployment occurred.

The Decisions API is a documented proposal in `docs/decisions.md`, not another default paid request. The existing **Help me choose** feature still makes a free random selection.

Before a public release, complete live menu/translation/image checks, measure provider usage and quality, verify a single HTTPS deployment with persistent storage, test physical iPhone/Android camera workflows, and exercise backup/restore on safe data. Do not treat simulated provider acceptance as production validation or evidence of demand.
