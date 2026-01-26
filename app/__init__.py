from flask import Flask
import os
import re

from .database import Database
from .services.deezer_data import DeezerDataClient
from .services.downloader import Downloader
from .routes import main_bp, start_queue_worker
from .services.deezer import DeezerClient as DeezerExplorer
from .services.logger import sys_logger


def get_changelog_summary(version_tag):
    """Lê o CHANGELOG.md e retorna o resumo da versão atual."""
    try:
        if not os.path.exists("CHANGELOG.md"):
            return "Notas de atualização não encontradas."

        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            r"^##\s+.*?" + re.escape(version_tag) + r"(.*?)(^##|\Z)",
            re.MULTILINE | re.DOTALL
        )
        match = pattern.search(content)

        if not match:
            pattern = re.compile(r"^##\s+.*?(.*?)(^##|\Z)", re.MULTILINE | re.DOTALL)
            match = pattern.search(content)

        if match:
            summary = match.group(1).strip()
            return summary if len(summary) < 300 else summary[:297] + "..."

        return "Sistema atualizado."

    except Exception as e:
        return f"Erro ao ler changelog: {e}"


def create_app():
    app = Flask(__name__)

    try:
        with open("version.txt", "r") as f:
            version = f.read().strip()
    except Exception:
        version = os.getenv("APP_VERSION", "vDev")

    clean_ver = version.replace("v", "")
    changelog_text = get_changelog_summary(clean_ver)

    sys_logger.log("SYSTEM", f"🎵 Melodock Iniciado {version}")
    sys_logger.log("SYSTEM", f"📝 Update: {changelog_text}")

    db = Database("/config/melodock.db")
    db.init_db()

    metadata = DeezerDataClient()

    # Downloader aplica patch do deemix no __init__
    downloader = Downloader(db)

    explorer = DeezerExplorer()

    app.config['DB'] = db
    app.config['METADATA'] = metadata
    app.config['DOWNLOADER'] = downloader
    app.config['EXPLORER'] = explorer

    @app.context_processor
    def inject_vars():
        return dict(
            system_version=version,
            update_summary=changelog_text
        )

    app.register_blueprint(main_bp)

    start_queue_worker(app)

    return app
