# Public demo on the Raspberry Pi

This is the manual deployment runbook for [ADR 0011](adr/0011-public-demo-on-existing-tunnel.md).
Build natively on the Pi 5 from `main`; no image registry or CI deployment is needed.
The existing Cloudflare Tunnel publishes nginx over a shared Docker network.

## First deployment

1. On the Pi, install Docker Engine with Docker Compose **2.24.4 or newer**
   (`!reset` support), Git and a running host cron service. Verify with
   `docker compose version`. The deploying account must be able to run Docker.
2. Clone the repository into `/opt/roadside` (or substitute your checkout path in
   every command and cron entry below), then check out `main`:

   ```sh
   cd /opt/roadside
   git switch main
   git pull --ff-only
   ```

3. Find the Docker network used by the existing `cloudflared` container:

   ```sh
   docker inspect cloudflared --format '{{json .NetworkSettings.Networks}}'
   ```

   Substitute the actual container name if different. Put the network name in
   `/opt/roadside/.env` (the root Compose environment file, not `backend/.env`):

   ```dotenv
   TUNNEL_NETWORK=your-existing-tunnel-network
   ```

   The network must already exist. Do not attach unrelated containers to it.
   No model credentials or backend environment file are needed. The override fixes
   `DEMO_MODE=true`, `PUBLIC_DEPLOY=true` and empty CORS origins, overriding any
   `backend/.env`. Remove any `LLM_RECORD=true` setting: startup deliberately
   refuses recording, even in demo mode. The server also refuses a live model
   whenever `PUBLIC_DEPLOY=true`.
4. Validate and start:

   ```sh
   docker compose -f compose.yaml -f compose.pi.yaml config
   make deploy-pi
   docker compose -f compose.yaml -f compose.pi.yaml ps
   ```

   The resolved configuration must have no published `ports`. Both services should
   be healthy/running. On failure, inspect logs with
   `docker compose -f compose.yaml -f compose.pi.yaml logs --tail=100`.
5. In the existing tunnel's Cloudflare dashboard, add a public hostname for this
   demo, with service **HTTP**, URL **`roadside-web:80`**. Keep Cloudflare caching
   defaults and do not add Cloudflare Access. Open the HTTPS hostname and confirm
   the demo banner, a recorded help scenario and sample photos work. Real photo
   uploads must be refused. The browser and API share this origin; no CORS origins
   are needed.
6. Replace the URL placeholder in the README with the public HTTPS URL. If changing
   `VITE_TILE_URL`, update its tile-provider privacy statement too and rebuild the
   frontend image with that build-time configuration.

## Nightly wipe

The SQLite database and uploads directory share a **256 MB tmpfs**, owned by the
image's non-root UID/GID 10001. The base data volume is removed from the backend's
mounts. Visitor entries stay in memory; if the cap is reached, writes fail until
the reset. Do not use real personal information in this shared demo.

Set the Pi's host timezone to `Europe/Warsaw` (check `timedatectl`), then run
`crontab -e` as the deploying account and install this line. Use the actual absolute
Docker path from `command -v docker` if it differs:

```cron
0 4 * * * cd /opt/roadside && /usr/bin/docker compose -f compose.yaml -f compose.pi.yaml restart backend >> /opt/roadside/nightly-reset.log 2>&1
```

This runs at 04:00 local time. Stopping and starting the backend empties its tmpfs;
startup migrations rebuild the schema. Test the command once manually, confirming
that an incident created before the restart disappears and `/health` returns OK
afterward. Check the cron log after the first scheduled reset. A plain
`docker compose restart` without both files would select the local configuration.

## Update

```sh
cd /opt/roadside
git switch main
git pull --ff-only
make deploy-pi
docker compose -f compose.yaml -f compose.pi.yaml ps
```

Recheck the public hostname and a demo scenario. Recreating the backend also wipes
visitor entries. To return to a known revision, check out that revision and run
`make deploy-pi` again. There are no visitor backups to restore.

## End of the review period

Remove the hostname from the existing tunnel and the cron entry, then stop only
this stack (leave the shared tunnel and its network running):

```sh
cd /opt/roadside
docker compose -f compose.yaml -f compose.pi.yaml down
```
