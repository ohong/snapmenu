# Operations and release

## Local setup

Use Python 3.12+, install `requirements.txt`, and configure `.env` from `.env.example`. Do not overwrite an existing `.env`. The current app reads `OPENAI_API_KEY`, `OPENAI_MENU_MODEL`, `OPENAI_IMAGE_MODEL`, and documented application settings. Fireworks and Runway keys are no longer used.

Start one process:

```sh
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

`/api/health` checks the database. `/api/config` reports whether keys are present, not whether they are valid. The labeled sample menu works without providers. Missing credentials never manufacture an extracted result.

## Hosted release

This repository includes a Dockerfile. The image has not been built here because the local Docker daemon is not running. To build on a Docker-enabled host:

```sh
docker build -t snapmenu .
docker volume create snapmenu-data
docker run --rm -p 8000:8000 --env-file .env -e DATA_DIR=/data -e SECURE_COOKIES=true -v snapmenu-data:/data snapmenu
```

Terminate HTTPS at the hosting platform. Verify that the container user can write `/data`. Set `SECURE_COOKIES=true` for HTTPS. Set it to false only for local HTTP testing. The Dockerfile defaults to secure cookies; an explicit environment setting overrides it.

Run one worker and one replica. Keep `DATA_DIR` on a persistent volume. Ephemeral serverless filesystems and multiple independent containers cannot preserve the current session and task guarantees. No mandatory Koyeb, Neon, or Vercel account is needed.

Configure an ingress request-body limit of 11 MB and a request timeout above 105 seconds. The app checks declared request size, reads at most 10 MB of the uploaded file, and bounds decoded image size. The hosting body limit also prevents oversized chunked uploads from filling temporary disk during multipart parsing.

Before public use, validate live provider access, set provider account spend limits, and apply host-level rate limiting. App defaults allow at most 100 scan attempts and 100 image submissions per rolling day across all browsers. Per-browser hourly caps are ten scans and twenty image attempts. Failed attempts consume budget. Set either daily cap to zero to stop new requests of that kind without losing saved menus. The account budget is the final external spending control.

## Data and retention

`DATA_DIR/snapmenu.sqlite3` contains private menus, hashed browser-session identifiers, provider task IDs, and request counts. `DATA_DIR/images/` contains completed WebP pictures. Neither directory belongs in Git or a container image.

Original menu images and PDFs are discarded after processing. Menu extraction uses `store=false`. Background image generation uses explicit `store=true` to retain its response ID for interruption recovery. Completed and cancelled image responses are deleted on a best-effort basis. Provider-side retention remains subject to the OpenAI account settings and terms, including when no browser returns to poll a completed image. Local expiry does not guarantee provider-side deletion. Menus become inaccessible at seven days; cleanup runs hourly, on startup, and on new scans. Physical removal may occur up to one hour after expiry. Clearing a browser cookie prevents access; it does not immediately delete server data.

The delete button removes the selected menu and pictures and requests cancellation of known pending tasks. Other menus previously scanned by that browser retain their original expiry. Cancellation is best effort and does not refund charges. Deleting an uncertain task cannot identify or cancel a provider request whose task ID was never received.

## Backup and recovery

For a consistent complete backup, stop the app, then copy the entire `DATA_DIR` to a protected backup location. Backups contain private menu text. Apply a retention policy that matches the product's deletion promise, and remove backups containing deleted menus where required.

To restore, stop the app, restore the complete directory, preserve its write permissions, and restart the same app version. Existing browser cookies continue to work. Expired records are removed on startup. A `starting` task becomes `uncertain`; the app never automatically resubmits it. An OpenAI `pending` task retains its response ID and resumes checking when its menu is open in a browser. Old pending Runway tasks are marked unavailable, never polled against OpenAI or automatically resubmitted. Completed local WebP files remain readable.

Before any future schema change, back up the current data directory. This release creates separate local tables and does not touch the legacy Neon database. Do not deprovision Neon or reset unknown data as part of this deployment.

The starting source commit is `5e6edea`. The clean source archive at `/Users/ohong/.codex/backups/snapmenu-2026-10-16/source.tar` excludes credentials and the pre-existing local settings edit. It is a developer recovery reference, not a data backup or a reason to restore retired provider paths in production.

## Diagnostics

- **App does not start:** confirm Python version, pinned dependencies, and write access to `DATA_DIR`.
- **Reading is not connected:** add an active `OPENAI_API_KEY` to the server environment and restart.
- **Pictures are not connected:** verify the same OpenAI key has GPT Image access and restart after changing settings.
- **Provider rejected a request:** inspect server log provider/reason fields; verify key, account balance, model access, quotas, and supported schema. Do not paste keys or image access URLs into logs or issues.
- **HTTP 401 `account_deactivated`:** the configured key was rejected during October 27 verification. Replace it with a key from an active OpenAI account/project; do not share the key in chat.
- **No readable dishes:** try a well-lit close photo of one page. A blank result stays an error.
- **Picture is pending:** keep the menu open to resume polling. The task is retained; do not create replacements manually without checking provider state.
- **Picture request is uncertain:** an interrupted submission may have incurred cost. Inspect the OpenAI project request history before any manual repair. The UI intentionally does not resubmit it.
- **Picture cannot be saved:** check response format, disk space, and directory write permissions. The app accepts bounded base64 bytes from OpenAI and does not fetch generated URLs.
- **Service limit reached:** inspect request counts and provider budgets before raising caps. A cookie reset cannot bypass the global caps.
- **Menu disappeared:** check cookie lifetime, original browser session, seven-day expiry, volume persistence, and HTTPS cookie settings.

Provider errors shown to users are sanitized. Uploaded content, credentials, task IDs, and temporary image URLs should not be logged. Avoid debug-level HTTP client logging in production.
