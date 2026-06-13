import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DEEZER_ARL: str = ""
    DOWNLOAD_QUALITY: str = "MP3_320"
    MUSIC_DIR: str = "/music"
    DOWNLOADS_DIR: str = "/downloads"
    CONFIG_DIR: str = "/config"
    ALLOWED_TYPES: List[str] = ["album", "ep", "single"]
    KEYWORD_BLOCKLIST: List[str] = []
    MAX_TRACKS_PER_ALBUM: int = 0
    DOWNLOAD_DELAY_MIN: float = 2.0
    DOWNLOAD_DELAY_MAX: float = 6.0
    PORT: int = 9014
    ACCESS_PASSWORD: str = ""

    @property
    def _settings_path(self) -> Path:
        return Path(self.CONFIG_DIR) / "settings.json"

    def save(self) -> None:
        path = self._settings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "Settings":
        config_dir = cls.model_fields["CONFIG_DIR"].default
        path = Path(config_dir) / "settings.json"
        if path.exists():
            data = json.loads(path.read_text())
            return cls(**data)
        return cls()


settings = Settings.load()
