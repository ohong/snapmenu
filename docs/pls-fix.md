# SnapMenu handoff

## Creator decisions

SnapMenu turns a text-only restaurant menu into a visual menu for diners, especially travellers. The user requested plain system typography, minimal controls, a mobile single-page app without page scrolling, Muse compatibility through a provider flag, and Base UI. They explicitly chose TypeScript Worker/D1/R2 on Cloudflare over retaining Python hosting. They authorized a Terra team to collect 50 real SF menus.

## Architecture decision

The previous FastAPI/static/SQLite implementation had useful recovery and privacy rules, but depended on a persistent Python server and native codecs. This version moves the runtime to TypeScript and Cloudflare. React/Base UI handles the screen; device-side normalization removes production Python codec dependencies. Background response handles preserve recovery. User data files and old infrastructure remain untouched.

## Integrated state

Default `AI_PROVIDER=muse`: Muse Ember reads menus; Muse Image renders dishes. `openai` selects Luna/Flare. D1 claims prevent duplicate paid submissions, R2 stores private WebP output, and tasks keep their original provider. Pictures start automatically only for visible dish cards. The sample makes no paid calls. The screen uses two or four cards with Next/Back; long detail dialogs can scroll internally.

Five Terra collectors produced 50 distinct SF restaurant source snapshots. Original PDFs/SVGs or genuine menu screenshots have source manifests, dates, hashes, and partial dish/price anchors. Historical and sample menus are flagged. Offline normalization produces 58 JPEG pages, 40 development cases and 10 holdout cases. This is an extraction benchmark input set, not proof of model accuracy or a current restaurant directory.

## Evidence and limits

See `docs/verification.md` for final checks against the current source digest. Provider-boundary simulation drives real workerd, D1, R2, Chromium, and WebKit. No live Muse extraction or image generation ran: a Meta key is absent. The existing OpenAI key still returns `401 account_deactivated`. Local Cloudflare migration and deployment dry run passed. No remote resources were provisioned and no new deployment was published.

No independent code-review agent was used; the user authorized the agent team for menu collection. Runtime integration and review stayed in the main chat.

## Next action

Add a working provider key securely, run the small live evaluation, and complete the release checks in `docs/plan.md`. The Cloudflare D1 ID remains a placeholder. The previous Python runtime and its data remain recoverable from Git history and the untouched ignored local data directory. The original October 16 archive also remains at `/Users/ohong/.codex/backups/snapmenu-2026-10-16/source.tar` if present; its continued existence was not checked in this rebuild.
