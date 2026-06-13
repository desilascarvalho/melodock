# Melodock v2 — Contexto do Projeto

Gerenciador de música self-hosted. Baixa via Deemix (Deezer), organiza biblioteca compatível com Plex/Jellyfin/Emby em `/music`, e expõe API REST + WebSocket para frontend estático servido em `/`.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Runtime | Python 3.12 |
| Web framework | FastAPI (async) |
| ORM | SQLAlchemy 2.x async + aiosqlite |
| Validação | Pydantic v2 |
| Migrations | Alembic |
| Download | Deemix 3.6.6 + deezer-py 1.3.7 |
| Metadados de áudio | mutagen |
| Tarefas periódicas | schedule (thread daemon) |
| Configuração | pydantic-settings (lê `/config/settings.json` + env vars) |

> **rclone foi removido.** Não há mais upload para Google Drive. Arquivos ficam em `/music` definitivamente.

---

## Estrutura de Pastas

```
melodock/
├── app/
│   ├── main.py              # FastAPI app, lifespan, WebSocket /ws, error handlers, static mount
│   ├── config.py            # Settings singleton — settings.load() / settings.save()
│   ├── database.py          # async_engine, AsyncSessionLocal, Base, get_db()
│   ├── models/
│   │   ├── artist.py        # Artist (artists)
│   │   ├── album.py         # Album (albums)
│   │   ├── track.py         # Track (tracks)
│   │   └── download_job.py  # DownloadJob (download_jobs)
│   ├── schemas/
│   │   ├── artist.py        # ArtistResponse, ArtistSearchResult, ArtistAddRequest/Response, PaginatedArtists
│   │   ├── album.py         # AlbumResponse, AlbumDetailResponse, PaginatedAlbums
│   │   ├── track.py         # TrackResponse
│   │   ├── download_job.py  # DownloadJobResponse, PaginatedJobs
│   │   ├── library.py       # LibraryStats, RecentAlbum, RecentJob
│   │   └── settings.py      # SettingsResponse/SettingsUpdate
│   ├── routers/
│   │   ├── artists.py       # /api/artists
│   │   ├── library.py       # /api/library
│   │   ├── downloads.py     # /api/downloads
│   │   ├── explorer.py      # /api/explorer
│   │   ├── settings.py      # /api/settings
│   │   └── logs.py          # /api/logs
│   ├── services/
│   │   ├── deezer.py        # DeezerClient — httpx async
│   │   ├── downloader.py    # DownloadEngine + _ProgressListener + download_engine singleton
│   │   ├── library.py       # scan_library() — varre /music recursivamente com mutagen
│   │   ├── scheduler.py     # start_scheduler() — thread daemon com schedule lib
│   │   └── log_buffer.py    # LogBuffer (deque 500) + WebSocketLogHandler
│   ├── middleware/
│   │   └── auth.py          # ApiKeyMiddleware — header X-Melodock-Key
│   ├── ws/
│   │   ├── broadcast.py     # ws_broadcast_queue: asyncio.Queue global + broadcast()
│   │   └── manager.py       # ConnectionManager singleton
│   └── static/              # Frontend multi-página (Tailwind CDN + CSS custom)
│       ├── index.html        # Redireciona para dashboard.html
│       ├── dashboard.html
│       ├── downloads.html
│       ├── explorer.html
│       ├── logs.html
│       ├── search.html
│       ├── settings.html
│       ├── css/style.css
│       └── js/
│           ├── api.js        # Todas as chamadas REST; fallback para MelodockMock se backend offline
│           ├── app.js        # MD.cover(), MD.badge(), sidebar, polling global
│           ├── dashboard.js
│           ├── downloads.js
│           ├── explorer.js
│           ├── logs.js
│           ├── search.js
│           └── settings.js
├── alembic/
│   └── versions/
│       ├── 0001_initial.py
│       ├── 0002_add_drive_fields.py
│       └── 0003_remove_drive_fields.py   # Remove drive_path e uploaded_to_drive
├── alembic.ini
├── audit.py
├── Dockerfile
├── docker-compose.yml
├── portainer-stack.yml
├── requirements.txt
└── run.py
```

---

## Banco de Dados

SQLite em `/config/melodock.db`. Engine async via `sqlite+aiosqlite`.

### Models

**Artist** — `artists`
- `id`, `deezer_id` (unique, indexed), `name`, `picture_url`, `picture_cached`, `followers`, `genres` (JSON), `added_at`, `last_synced`

**Album** — `albums`
- `id`, `deezer_id` (unique, indexed), `artist_id` (FK→artists), `title`, `release_date`, `cover_url`, `cover_cached`, `album_type`, `nb_tracks`
- `status`: `pending | downloading | done | skipped | error`
- `local_path`, `added_at`
- ~~`drive_path`, `uploaded_to_drive`~~ — removidos na migration 0003

**Track** — `tracks`
- `id`, `deezer_id` (unique, indexed), `album_id` (FK→albums), `artist_id` (FK→artists), `title`, `track_number`, `disc_number`, `duration`
- `local_path`, `file_exists` (bool), `quality` (`FLAC | MP3_320 | MP3_128`)
- `added_at`
- ~~`drive_path`, `uploaded_to_drive`~~ — removidos na migration 0003

**DownloadJob** — `download_jobs`
- `id`, `deezer_id`, `job_type` (`album | track | discography`)
- `artist_id` (FK nullable), `album_id` (FK nullable)
- `status`: `queued | running | done | error | skipped`
- `quality`, `progress` (0-100), `error_message`, `started_at`, `finished_at`, `created_at`

---

## Configuração (`app/config.py`)

| Campo | Padrão | Descrição |
|-------|--------|-----------|
| `DEEZER_ARL` | `""` | Cookie de autenticação Deezer |
| `DOWNLOAD_QUALITY` | `"MP3_320"` | Qualidade preferida |
| `MUSIC_DIR` | `"/music"` | Destino final dos arquivos de áudio |
| `DOWNLOADS_DIR` | `"/downloads"` | Diretório temporário do deemix |
| `CONFIG_DIR` | `"/config"` | Local de settings.json + melodock.db + pictures/ |
| `ALLOWED_TYPES` | `["album","ep","single"]` | Filtro de tipo de lançamento |
| `KEYWORD_BLOCKLIST` | `[]` | Palavras proibidas no título do álbum |
| `MAX_TRACKS_PER_ALBUM` | `0` | 0 = sem limite |
| `DOWNLOAD_DELAY_MIN` | `2.0` | Delay mínimo anti-ban (segundos) |
| `DOWNLOAD_DELAY_MAX` | `6.0` | Delay máximo anti-ban (segundos) |
| `PORT` | `9014` | Porta do servidor |
| `ACCESS_PASSWORD` | `""` | Se vazio, sem autenticação |

> Campos rclone (`RCLONE_ENABLED`, `RCLONE_REMOTE`, `RCLONE_FLAGS`) foram **removidos**.

---

## Fluxo de Download

```
POST /api/artists/add  ou  POST /api/downloads/queue
        ↓
  DownloadJob criado (status=queued)
        ↓
  run_queue_worker() pega o próximo job (polling 5s)
        ↓
  _run_deemix() em asyncio.to_thread
    - fallbackBitrate=True → baixa melhor qualidade disponível
    - _ProgressListener captura qualidade real de cada faixa
        ↓
  _finalize_job(listener)
    - Procura pasta em /downloads com padrão "{Artist} - {Album}"
    - Move arquivos para /music/{Artist}/{Album}/
    - Atualiza Album.local_path, Track.local_path, file_exists=True
    - Track.quality = qualidade real do listener ou _detect_file_quality()
        ↓
  job.status = "done"
  broadcast: job_done / job_error / queue_updated
```

**Job status flow:** `queued → running → done` (ou `error`)

---

## API REST

Prefixo `/api`. Erros retornam sempre `{"error": "...", "code": N}`.

### `/api/artists`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/artists` | Lista paginada — params: `page`, `limit`, `search` |
| GET | `/artists/{id}` | Detalhes + `album_count` |
| GET | `/artists/{id}/picture` | Foto do artista (cache local) |
| POST | `/artists/search` | Busca na API Deezer |
| POST | `/artists/add` | Salva artista, busca discografia, cria jobs |
| DELETE | `/artists/{id}` | Remove do banco |
| POST | `/artists/{id}/sync` | Re-busca discografia |

### `/api/library`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/library` | `LibraryStats`: artists, albums, tracks, size_gb, recent_albums, recent_jobs, albums_by_status, tracks_by_quality |
| GET | `/library/albums` | Lista paginada |
| GET | `/library/albums/{id}` | Detalhes + tracks |
| POST | `/library/scan` | Dispara `scan_library()` |
| POST | `/library/audit` | Alias de /scan |

### `/api/downloads`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/downloads` | Lista com `running` primeiro |
| GET | `/downloads/active` | Job em execução atual ou null |
| POST | `/downloads/queue` | Adiciona job manualmente |
| DELETE | `/downloads/{id}` | Cancela job `queued` |
| POST | `/downloads/clear-completed` | Remove jobs `done` |

> Endpoint `retry-upload` foi **removido** junto com o rclone.

### `/api/explorer`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/explorer/related/{deezer_id}` | Artistas relacionados |

### `/api/settings`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/settings` | Config atual |
| PUT | `/settings` | Atualiza e persiste |
| POST | `/settings/test-arl` | Testa ARL |

### `/api/logs`
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/logs` | Últimas 500 entradas |

### Sistema
| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | `{"status": "ok", "version": "2.0.0"}` |
| WS | `/ws` | WebSocket — keep-alive ping 30s |
| GET | `/` | Redireciona para `dashboard.html` |

---

## WebSocket — Eventos do Servidor

```json
{"type": "job_progress",         "data": {"job_id": 1, "progress": 45, "status": "running"}}
{"type": "job_done",             "data": {"job_id": 1, "album_title": "...", "artist_name": "..."}}
{"type": "job_error",            "data": {"job_id": 1, "error": "..."}}
{"type": "queue_updated",        "data": {"pending_count": 3}}
{"type": "sync_complete",        "data": {"new_albums": 2, "new_jobs": 2, "ts": "..."}}
{"type": "library_scan_complete","data": {"scanned": 150, "new_found": 3, "updated": 1}}
{"type": "log",                  "data": {"level": "INFO", "msg": "...", "ts": "..."}}
{"type": "ping"}
```

---

## Frontend

Multi-página com Tailwind CSS (CDN) + CSS custom em `css/style.css`.

- `index.html` → redireciona para `dashboard.html`
- Cada página carrega `js/api.js`, `js/app.js` e o JS específico da página
- `js/api.js` usa `window.location.origin + '/api'` como base URL (relativo — funciona em qualquer domínio)
- Fallback automático para `MelodockMock` quando o backend não responde em 1.5s
- Scripts com `?v=2` em todos os HTML para evitar cache stale

---

## Docker

**Volumes mapeados:**
```
/music       → /mnt/storage/data/media/music
/downloads   → /mnt/storage/data/media/downloads
/config      → /opt/grathus/config
```

**Redes:** container na rede `media` (compartilhada com Nginx Proxy Manager).

**Dockerfile:** `python:3.12-slim` + `ffmpeg` (rclone foi removido).

**Healthcheck:** `curl -f http://localhost:9014/health` a cada 30s.

---

## Scheduler (thread daemon)

| Schedule | Tarefa |
|----------|--------|
| Diário 03:00 | `sync_all_artists_job` — busca novos álbuns |
| Semanal | `library_scan_job` — varre /music |
| Diário 04:00 | `cleanup_old_jobs` — remove jobs `done` > 30 dias |

---

## Autenticação

`ApiKeyMiddleware` — só ativa se `ACCESS_PASSWORD != ""`.
- Header: `X-Melodock-Key: {senha}`
- Livres: `/health`, `/ws`, `/docs`, `/openapi.json`, `/redoc`

---

## Migrations Alembic

Rodar no primeiro deploy após atualização:
```bash
alembic upgrade head
```

| Migration | O que faz |
|-----------|-----------|
| 0001 | Cria tabelas iniciais |
| 0002 | Adiciona drive_path + uploaded_to_drive |
| 0003 | Remove drive_path + uploaded_to_drive (rclone removido) |

---

## Convenções Importantes

- `DownloadJobResponse` tem `artist_name` e `album_title` via JOIN (`_enrich_many`)
- `AlbumDetailResponse` importa `TrackResponse` no final do arquivo (evita import circular) + `model_rebuild()`
- Deemix roda em `asyncio.to_thread`. `_ProgressListener` usa `run_coroutine_threadsafe` para emitir progresso
- Todos os serviços usam `AsyncSessionLocal()` próprio — não dependem do `get_db()` do FastAPI
- `_sanitize(name)` remove caracteres inválidos de nomes de diretório
