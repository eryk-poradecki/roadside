# The public demo runs in memory, in demo mode only, behind the existing Cloudflare Tunnel

The public demo is the base compose stack (ADR 0007) on the author's Raspberry Pi 5, published as one more hostname on a Cloudflare Tunnel that already serves other apps. A committed `compose.pi.yaml` override changes four things. It fixes demo mode, which the server itself enforces. It keeps all data in a `tmpfs` that a nightly restart wipes. It attaches `web` to the tunnel's Docker network instead of publishing a port. It sets restart policies. The demo is meant to run for about a week so reviewers can try it live, then it is stopped, so each choice is the simplest one that is still safe for strangers to use.

## Considered Options

- **A second `cloudflared` connector in the override**, or `cloudflared` on the host. Rejected: the Pi's existing `cloudflared` container already serves other apps. Adding one public hostname to it is less to run and reuses a setup known to work.
- **Publishing `web` on a host port** (even `127.0.0.1`). Not needed: `cloudflared` is a container, so a shared Docker network reaches nginx with no port open.
- **A `pi` profile in the base compose file.** Rejected: it mixes deploy concerns into the file reviewers run with no keys.
- **Keeping the override local only.** Rejected: it holds no secrets, and the demo-mode guard in it is a safety claim a reviewer should be able to read.
- **Multi-arch images built in CI and pulled from GHCR**, or Watchtower. Rejected for a single deploy: native arm64 builds on the Pi take minutes and need no registry. This is a README follow-up.
- **Keeping the database on a volume across releases**, with backups. Rejected: visitors' incidents can hold their real geolocation and notes, and nothing on a public demo is worth keeping.
- **Resetting with a sidecar that holds the Docker socket**, or an in-app cleanup timer. Rejected: socket access is bad practice, and a timer is code that has to stay correct. A host crontab restart is enough.
- **CI auto-deploy over SSH** or a self-hosted runner. Rejected: it adds attack surface and setup for what is expected to be one deploy.
- **In-project monitoring or an external uptime ping.** Rejected: the author's existing Pi container dashboard covers it.

## Consequences

- **Override contents (`compose.pi.yaml`)**, used as `docker compose -f compose.yaml -f compose.pi.yaml up -d --build` (wrapped as `make deploy-pi`):
  - `backend` environment fixed to `DEMO_MODE=true`, `PUBLIC_DEPLOY=true`, `FRONTEND_ORIGINS=` (empty). `environment:` beats any `env_file`, so a stray `.env` can't turn demo mode off.
  - The data dir (`DATABASE_PATH`, `UPLOAD_DIR`) is a `tmpfs` capped at 256 MB and writable by the image's non-root user. It replaces the base named volume (`!reset`). Nothing a visitor enters reaches the Pi's disk. If the cap is ever hit, writes fail until the next reset.
  - `web` joins the tunnel's existing Docker network as an external network. Its name comes from env (`TUNNEL_NETWORK`), not hard-coded, and `web` gets a stable alias (e.g. `roadside-web`). No host ports are published.
  - `restart: unless-stopped` on both services.
- **The server enforces demo mode.** A new `PUBLIC_DEPLOY` setting (default `false`) makes startup refuse `DEMO_MODE=false` or `LLM_RECORD=true`, failing fast like the rest of `Settings` (ADR 0007). This sits on top of the 403 on uploads (ADR 0002) and the absence of the `claude` binary from the image (ADR 0007).
- **Nightly reset:** a host crontab line restarts `backend` at 04:00 Europe/Warsaw. A restart empties the `tmpfs`, and startup migrations rebuild the schema. This changes ADR 0006's reason for rejecting `schema.sql`: what persists is local and self-hosted databases, not the Pi's.
- **Same origin, no CORS in production.** The browser talks only to `https://<subdomain>`, then `cloudflared`, nginx and uvicorn. `FRONTEND_ORIGINS` is empty, so no CORS headers are sent. `--proxy-headers` stays only so the scheme reads `https`. Nothing uses the client IP (no rate limiting, ADR 0007, and no PII in logs), so there is no `CF-Connecting-IP` handling.
- **Caching headers live in the base nginx config**, so local compose behaves the same: `no-cache` on `index.html`, the service worker and the web manifest; `public, max-age=31536000, immutable` on hashed `/assets/*`; `no-store` on `/api/*`, unless the API sets its own `Cache-Control` (the bundled sample photos are cacheable for a day, a driver's photos are `private, no-cache`). Without them, Cloudflare's edge or a cached service worker could pin visitors to an old build after even one hotfix. Cloudflare settings stay at their defaults, with no Cloudflare Access. nginx still must not send a restrictive `Referrer-Policy` (ADR 0008).
- **Images build on the Pi** from a checkout of `main`.
- **Updates follow a manual runbook** in `docs/deploy.md`: ssh to the Pi, `git pull`, `make deploy-pi`. It also covers the one-time setup: add the public hostname → `http://roadside-web:80` to the existing tunnel in the Cloudflare dashboard, set `TUNNEL_NETWORK`, install the crontab line. It notes that changing `VITE_TILE_URL` means updating the README privacy line.
- **README "Live demo" section:**
  - the URL, available during the review period;
  - AI answers are pre-recorded, so they follow fixed scenarios;
  - photo uploads are off, sample photos only (ADR 0002);
  - anything entered is held in memory only and wiped nightly;
  - in demo mode the server calls neither Overpass nor Nominatim (ADR 0004), but the browser loads map tiles directly from the tile provider in `VITE_TILE_URL`. For this deploy that is OpenStreetMap's standard tile servers (ADR 0008), so the OSMF sees the visitor's IP and the map area viewed;
  - it runs on a home Raspberry Pi, so it may sometimes be offline.
- **Cut order unchanged:** the Raspberry Pi deploy is still the third thing cut.
