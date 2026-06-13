import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdate,
    TestArlRequest,
    TestArlResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])
log = logging.getLogger(__name__)


def _to_response() -> SettingsResponse:
    return SettingsResponse(
        arl=settings.DEEZER_ARL,
        arl_configured=bool(settings.DEEZER_ARL),
        quality=settings.DOWNLOAD_QUALITY,
        release_types=settings.ALLOWED_TYPES,
        blocklist=settings.KEYWORD_BLOCKLIST,
        max_tracks=settings.MAX_TRACKS_PER_ALBUM,
        delay_min=settings.DOWNLOAD_DELAY_MIN,
        delay_max=settings.DOWNLOAD_DELAY_MAX,
        password=settings.ACCESS_PASSWORD,
        access_password_configured=bool(settings.ACCESS_PASSWORD),
        MUSIC_DIR=settings.MUSIC_DIR,
        DOWNLOADS_DIR=settings.DOWNLOADS_DIR,
        CONFIG_DIR=settings.CONFIG_DIR,
        PORT=settings.PORT,
    )


@router.get("", response_model=SettingsResponse)
async def get_settings():
    return _to_response()


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate):
    mapping = {
        "arl": "DEEZER_ARL",
        "quality": "DOWNLOAD_QUALITY",
        "release_types": "ALLOWED_TYPES",
        "blocklist": "KEYWORD_BLOCKLIST",
        "max_tracks": "MAX_TRACKS_PER_ALBUM",
        "delay_min": "DOWNLOAD_DELAY_MIN",
        "delay_max": "DOWNLOAD_DELAY_MAX",
        "password": "ACCESS_PASSWORD",
    }
    patch = body.model_dump(exclude_none=True)
    changed = []
    for frontend_key, value in patch.items():
        backend_key = mapping.get(frontend_key, frontend_key)
        if hasattr(settings, backend_key):
            old = getattr(settings, backend_key)
            if old != value:
                if frontend_key == "arl":
                    changed.append("ARL atualizado")
                elif frontend_key == "password":
                    changed.append("senha de acesso atualizada")
                elif frontend_key == "quality":
                    changed.append(f"qualidade → {value}")
                elif frontend_key == "release_types":
                    changed.append(f"tipos de release → {', '.join(value)}")
                elif frontend_key == "blocklist":
                    changed.append(f"blocklist → {value}")
                elif frontend_key == "delay_min":
                    changed.append(f"delay mínimo → {value}s")
                elif frontend_key == "delay_max":
                    changed.append(f"delay máximo → {value}s")
                elif frontend_key == "max_tracks":
                    changed.append(f"max faixas/álbum → {value or 'sem limite'}")
                else:
                    changed.append(f"{frontend_key}={value!r}")
                object.__setattr__(settings, backend_key, value)
    settings.save()
    if changed:
        log.info("⚙️ Configurações salvas: %s", " | ".join(changed))
    return _to_response()


@router.get("/deemix")
async def get_deemix_settings():
    try:
        from deemix.settings import load as dz_load
        cfg = dz_load(settings.CONFIG_DIR)
        return cfg
    except Exception as exc:
        log.warning("Erro ao ler config deemix: %s", exc)
        raise HTTPException(500, "Não foi possível ler o config do deemix")


@router.put("/deemix")
async def update_deemix_settings(body: dict):
    try:
        from deemix.settings import load as dz_load, save as dz_save
        cfg = dz_load(settings.CONFIG_DIR)
        cfg.update(body)
        dz_save(cfg, settings.CONFIG_DIR)
        changed = list(body.keys())
        log.info("⚙️ Config deemix atualizado: %s", ", ".join(changed))
        return cfg
    except Exception as exc:
        log.warning("Erro ao salvar config deemix: %s", exc)
        raise HTTPException(500, "Não foi possível salvar o config do deemix")


@router.post("/test-arl", response_model=TestArlResponse)
async def test_arl(body: TestArlRequest):
    try:
        import asyncio
        result = await asyncio.to_thread(_check_arl, body.arl)
        if result.valid:
            log.info("🔑 ARL testado com sucesso — usuário: %s", result.username or "desconhecido")
        else:
            log.warning("🔑 ARL inválido ou expirado")
        return result
    except Exception as exc:
        log.warning("ARL test failed: %s", exc)
        return TestArlResponse(valid=False)


def _check_arl(arl: str) -> TestArlResponse:
    try:
        from deezer import Deezer
        dz = Deezer()
        logged_in = dz.login_via_arl(arl)
        if logged_in:
            username = getattr(dz.current_user, "name", None) or str(dz.current_user.get("name", ""))
            return TestArlResponse(valid=True, username=username or None)
        return TestArlResponse(valid=False)
    except Exception as exc:
        log.debug("_check_arl error: %s", exc)
        return TestArlResponse(valid=False)
