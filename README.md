# Melodock

Self-hosted music manager powered by [Deezer](https://www.deezer.com) / [deemix](https://gitlab.com/RemixDev/deemix-py). Organizes your library in a folder structure compatible with Plex, Jellyfin, and Emby.

![version](https://img.shields.io/badge/version-1.0.0-7C3AED?style=flat-square)
![python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![docker](https://img.shields.io/docker/image-size/desilascarvalho/melodock/latest?style=flat-square&logo=docker&logoColor=white)
![license](https://img.shields.io/badge/license-MIT-green?style=flat-square)

## Features

- **Artist library** — search Deezer, add artists, auto-sync full discography
- **Download queue** — real-time progress via WebSocket, per-track or full album
- **Smart scanner** — scans `/music` with mutagen, maps files to the database
- **Clean metadata** — featured artists go to track title only, never to artist/albumArtist tags
- **Deemix settings UI** — folder structure, name templates, tags, artwork, all exposed in the dashboard
- **Rich logs** — emoji-annotated logs streamed live to the dashboard
- **Multi-page frontend** — Tailwind CSS, no build step required

## Screenshots

> Dashboard · Downloads · Artist detail · Settings

## Quick Start

### Docker Compose

```yaml
services:
  melodock:
    image: desilascarvalho/melodock:latest
    container_name: melodock
    restart: unless-stopped
    ports:
      - "9014:9014"
    volumes:
      - /your/music:/music
      - /your/downloads:/downloads
      - /your/config:/config
    environment:
      - TZ=America/Sao_Paulo
```

```bash
docker compose up -d
```

Open `http://localhost:9014` in your browser.

### Docker Run

```bash
docker run -d \
  --name melodock \
  -p 9014:9014 \
  -v /your/music:/music \
  -v /your/downloads:/downloads \
  -v /your/config:/config \
  -e TZ=America/Sao_Paulo \
  desilascarvalho/melodock:latest
```

## Configuration

All settings are persisted in `/config/settings.json` and editable via the Settings page.

| Setting | Default | Description |
|---------|---------|-------------|
| `DEEZER_ARL` | — | Deezer authentication cookie (required) |
| `DOWNLOAD_QUALITY` | `MP3_320` | `FLAC`, `MP3_320`, or `MP3_128` |
| `MUSIC_DIR` | `/music` | Final destination for audio files |
| `DOWNLOADS_DIR` | `/downloads` | Temporary deemix working directory |
| `CONFIG_DIR` | `/config` | Database, settings, and deemix config |
| `ALLOWED_TYPES` | `album,ep,single` | Release types to download |
| `MAX_TRACKS_PER_ALBUM` | `0` | `0` = no limit |
| `DOWNLOAD_DELAY_MIN` | `2.0` | Anti-ban delay minimum (seconds) |
| `DOWNLOAD_DELAY_MAX` | `6.0` | Anti-ban delay maximum (seconds) |
| `ACCESS_PASSWORD` | — | If set, protects the web interface |

### Getting your Deezer ARL

1. Log in to [deezer.com](https://www.deezer.com) in your browser
2. Open DevTools → Application → Cookies → `deezer.com`
3. Copy the value of the `arl` cookie
4. Paste it in Melodock's Settings page and click **Test ARL**

## Volumes

| Container path | Purpose |
|----------------|---------|
| `/music` | Final music library (point to your Plex/Jellyfin media folder) |
| `/downloads` | Temporary download staging area |
| `/config` | SQLite database, settings.json, deemix config.json, cached artwork |

## API

REST API available at `/api`. Interactive docs at `/docs`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/artists` | Paginated artist list |
| `POST` | `/api/artists/search` | Search Deezer |
| `POST` | `/api/artists/add` | Add artist + queue discography |
| `GET` | `/api/downloads` | Download queue |
| `POST` | `/api/downloads/queue` | Queue a job manually |
| `GET` | `/api/library` | Library stats |
| `POST` | `/api/library/scan` | Trigger library scan |
| `GET` | `/api/settings` | Current settings |
| `PUT` | `/api/settings` | Update settings |
| `GET` | `/api/settings/deemix` | Deemix config |
| `PUT` | `/api/settings/deemix` | Update deemix config |
| `GET` | `/health` | `{"status":"ok","version":"1.0.0"}` |
| `WS` | `/ws` | WebSocket — live events |

## WebSocket Events

```json
{ "type": "job_progress", "data": { "job_id": 1, "progress": 45 } }
{ "type": "job_done",     "data": { "job_id": 1, "album_title": "..." } }
{ "type": "job_error",    "data": { "job_id": 1, "error": "..." } }
{ "type": "log",          "data": { "level": "INFO", "msg": "..." } }
{ "type": "ping" }
```

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 |
| Framework | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.x async + aiosqlite |
| Migrations | Alembic |
| Downloads | deemix 3.6.6 + deezer-py |
| Audio metadata | mutagen |
| Frontend | Tailwind CSS CDN + vanilla JS |
| Database | SQLite (`/config/melodock.db`) |

## Development

```bash
git clone https://github.com/desilascarvalho/melodock
cd melodock

pip install -r requirements.txt
python run.py
```

The server starts on port `9014`. Volumes default to `/music`, `/downloads`, and `/config` — create them locally or override via environment variables.

## License

MIT
