# CCTV Centralization — Dev Notes

Everything needed to pick up this project on another machine.

---

## Quick start

```bash
# Clone, then:
cd cctv-centralization
docker compose up -d
# App at http://localhost:8080
# Backend API at http://localhost:8080/api/v1/docs
```

**Requires OrbStack** (or Docker Desktop — both work, same socket path).

---

## Stack

| Layer | Tech | Port (host) |
|---|---|---|
| Frontend | React + Vite (dev server, HMR) | 5173 |
| Backend | FastAPI + SQLAlchemy async | 8000 |
| Database | PostgreSQL 15 | 5432 |
| Cache/sessions | Redis 7 | 6379 |
| Streaming | go2rtc | 1984 |
| Reverse proxy | nginx | **8080** ← main entry point |

All services talk over the `internal` Docker bridge network.
The nginx at `:8080` is the only port you open in the browser.

---

## Key file locations

```
cctv-centralization/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/     ← FastAPI route handlers
│   │   ├── models/             ← SQLAlchemy ORM models
│   │   ├── services/
│   │   │   └── playback/       ← Recording search + download logic
│   │   │       ├── hikvision_playback.py   ← ISAPI search + RTSP probe
│   │   │       ├── download_service.py     ← ffmpeg streaming download
│   │   │       ├── acti_playback.py        ← ACTi SNVR support
│   │   │       └── playback_manager.py     ← go2rtc session management
│   │   └── core/config.py      ← All settings (pydantic-settings)
│   ├── alembic/versions/       ← DB migrations
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── pages/              ← Top-level pages (Playback.jsx, etc.)
│       └── components/playback/← Playback UI components
├── go2rtc/
│   └── go2rtc.yaml             ← Live stream definitions (RTSP URLs)
├── nginx/nginx.conf            ← Reverse proxy config
└── docker-compose.yml
```

---

## Environment / secrets

All secrets live in `docker-compose.yml` directly (no `.env` file needed for Docker).
For local development outside Docker, copy `.env.example` → `.env` and fill in.

Default credentials:
- **DB**: `postgres / postgres` on `cctv_db`
- **JWT secret**: `supersecretkey` (change for production)
- **App login**: created via seed script or admin user in DB

---

## Database

```bash
# Run migrations
docker exec cctv_backend alembic upgrade head

# Connect to DB
docker exec -it cctv_postgres psql -U postgres -d cctv_db

# Backup DB data
docker exec cctv_postgres pg_dump -U postgres cctv_db > backup.sql

# Restore
docker exec -i cctv_postgres psql -U postgres cctv_db < backup.sql
```

Data is persisted in Docker volume `pgdata`. Moving to another machine:
```bash
# On old machine — export volume
docker run --rm -v cctv-centralization_pgdata:/data -v $(pwd):/backup \
  alpine tar czf /backup/pgdata.tar.gz -C /data .

# On new machine — import volume
docker run --rm -v cctv-centralization_pgdata:/data -v $(pwd):/backup \
  alpine tar xzf /backup/pgdata.tar.gz -C /data
```

---

## go2rtc

Live streams are defined in `go2rtc/go2rtc.yaml`. The file is bind-mounted into both the `go2rtc` and `backend` containers.

**Stream naming convention:** `{site-slug}_{channel}` e.g. `arohera-lt3_4`

**To add a live stream:**
```bash
# Via API (runtime only — won't survive restart)
curl -X PUT "http://localhost:1984/api/streams?name=my_stream&src=rtsp://..."

# Persistent — add entry to go2rtc/go2rtc.yaml, then:
docker restart cctv_go2rtc
```

**IMPORTANT: go2rtc does NOT handle SIGHUP** — sending SIGHUP kills the container (exit 129).
Always use `docker restart cctv_go2rtc` for config reloads.

**Two RTSP source types in use:**
- `ffmpeg:rtsp://...#video=h264` — transcodes to H.264 (for Hikvision NVRs)
- `exec:python3 /scripts/acti_pipe.py {ip} {ch} {user} {pass}#video=h264` — for ACTi SNVR cameras

**Password URL encoding in go2rtc.yaml:** Special chars must be percent-encoded:
- `@` → `%40`
- `#` → `%23`
- `*` → `%2A`

---

## NVR compatibility notes

### Hikvision (most sites)
- Recording search: `POST /ISAPI/ContentMgmt/search` with XML
- Live stream: `/Streaming/Channels/{channel}01` (e.g. channel 4 → `401`)
- Playback RTSP: `/Streaming/tracks/{channel}01?starttime=...&endtime=...`

### Hikvision AROHERA Lt3 (10.11.32.200, DS-7108NI-Q1/M)
This NVR has a firmware quirk — **`/Streaming/tracks/` always returns `453 Not Enough Bandwidth`** for playback RTSP, even when no other connections are active. This is a firmware limitation, not a real bandwidth issue.

**Workaround:** Use PSIA format instead:
```
/PSIA/Streaming/channels/{channel}01?starttime=20260608T080000Z&endtime=20260608T081000Z
```
The download service (`download_service.py`) automatically falls back to PSIA when tracks returns 453 or produces no data within 12 seconds.

- Password: `samator@88` → URL-encode as `samator%4088`
- ISAPI ContentMgmt/search: returns `badXmlContent` (firmware doesn't support it)
- Recording search: falls back to RTSP probe (`_probe_rtsp_segment`)
- go2rtc live streams: use standard `/Streaming/Channels/{channel}01` (works fine)

### ACTi SNVR (sig-pier, sandana-baswara-gas, sgi-tuban, etc.)
- No recording search API — backend probes the playback endpoint directly
- Live stream: via `acti_pipe.py` script (proxies the MJPEG stream as H.264)
- Playback: prefetches recording to temp file, serves via `/session/{id}/stream`

### Uniview ZNR (if present)
- Uses Uniview LAPI (`/LAPI/V1.0/`)
- RTSP path: `/unicast/c{channel}/s0/live`

---

## Recording download (playback)

The download endpoint `POST /api/v1/playback/download` streams an MP4 directly to the browser via ffmpeg. No temp files — data flows as ffmpeg reads from the NVR.

**URL resolution order** (implemented in `download_service.py::stream_recording`):
1. Try `/Streaming/tracks/{track}?starttime=...` — wait up to 12s for first data
2. If no data or 453 → try `/PSIA/Streaming/channels/{ch}01?starttime=...`
3. If PSIA also blocked → free go2rtc live-stream slot for that channel, retry PSIA
4. If all fail → return 502 with error message

**ffmpeg output:** Fragmented MP4 (`frag_keyframe+empty_moov+default_base_moof`) piped to stdout. This allows the browser download to start immediately as data arrives.

**Expected download speed:** NVRs stream recordings at approximately 1× real-time. A 10-minute clip takes ~10 minutes to download.

**Frontend progress:** `PlaybackDownloadDialog.jsx` shows a live bytes-received counter and elapsed timer while downloading.

---

## Playback session flow

1. Frontend `POST /api/v1/playback/session` → backend registers temp go2rtc stream
2. go2rtc stream name: `playback_{device_short_id}_ch{n}_{timestamp}_{random}`
3. Frontend connects WebSocket to go2rtc for MSE/WebRTC playback
4. Session expires after idle timeout; cleanup worker runs every 30s
5. Frontend sends heartbeat every 60s to keep session alive

**Stale playback sessions in go2rtc.yaml:** If the backend crashed during a session, stale entries may persist. To remove:
```bash
# Delete from go2rtc API (removes from runtime)
curl -X DELETE "http://localhost:1984/api/streams?name=playback_xxx"
# Also manually remove from go2rtc/go2rtc.yaml, then:
docker restart cctv_go2rtc
```

---

## Common ops

```bash
# Start everything
docker compose up -d

# Restart just backend (picks up Python code changes if --reload isn't working)
docker restart cctv_backend

# Tail logs
docker logs cctv_backend -f
docker logs cctv_go2rtc -f

# Check all containers
docker compose ps

# Run a migration after model changes
docker exec cctv_backend alembic revision --autogenerate -m "description"
docker exec cctv_backend alembic upgrade head

# Open a Python shell in backend
docker exec -it cctv_backend python3

# Check what ffmpeg sees from an NVR (replace URL)
docker exec cctv_backend ffmpeg -y -loglevel warning -rtsp_transport tcp \
  -i "rtsp://admin:pass@192.168.x.x:554/Streaming/Channels/101" \
  -t 3 -f null -

# Test PSIA playback URL
docker exec cctv_backend ffmpeg -y -loglevel warning -rtsp_transport tcp \
  -i "rtsp://admin:samator%4088@10.11.32.200:554/PSIA/Streaming/channels/401?starttime=20260608T080000Z&endtime=20260608T081000Z" \
  -t 10 -c:v copy -c:a aac -movflags frag_keyframe+empty_moov -f mp4 /tmp/test.mp4
```

---

## Known issues / TODO

- **AROHERA Lt3 download**: Works via PSIA fallback but the initial 12s probe wait is visible to the user (attempts tracks first, waits for timeout, then switches to PSIA). Could be improved by remembering per-NVR which URL format works.
- **`arohera-lt3_1` in go2rtc.yaml**: Has unencoded `@` in password (`samator@88` instead of `samator%4088`). This stream may not connect. Fix: change the source URL to use `samator%4088`.
- **`playback_sessions` table**: Missing from current migrations — playback cleanup worker logs errors at startup. The playback system works without it (sessions are managed in Redis + go2rtc), but the error is noisy.
- **Frontend download dialog**: After a successful download `onClose()` is called automatically — the dialog closes and the browser receives the file. If the dialog stays open, check browser console for errors.

---

## Transferring to another machine

1. **Push git** (code only — no secrets, no DB data):
   ```bash
   git push
   ```

2. **Export DB volume** (see Database section above)

3. **On new machine:**
   ```bash
   git clone <repo>
   cd cctv-centralization
   # Import pgdata volume if needed
   docker compose up -d
   docker exec cctv_backend alembic upgrade head
   ```

4. **go2rtc.yaml** is in git — streams come back automatically after `docker compose up`.
