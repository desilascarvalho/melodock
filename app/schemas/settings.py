from typing import Optional

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    arl: str = ""
    arl_configured: bool = False
    quality: str = "MP3_320"
    release_types: list[str] = []
    blocklist: list[str] = []
    max_tracks: int = 0
    delay_min: float = 2.0
    delay_max: float = 6.0
    password: str = ""
    access_password_configured: bool = False
    # paths (read-only info)
    MUSIC_DIR: str = "/music"
    DOWNLOADS_DIR: str = "/downloads"
    CONFIG_DIR: str = "/config"
    PORT: int = 9014


class SettingsUpdate(BaseModel):
    arl: Optional[str] = None
    quality: Optional[str] = None
    release_types: Optional[list[str]] = None
    blocklist: Optional[list[str]] = None
    max_tracks: Optional[int] = None
    delay_min: Optional[float] = None
    delay_max: Optional[float] = None
    password: Optional[str] = None


class TestArlRequest(BaseModel):
    arl: str


class TestArlResponse(BaseModel):
    valid: bool
    username: Optional[str] = None
