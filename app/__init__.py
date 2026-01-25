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
            
        # Procura pelo cabeçalho da versão atual ou o primeiro que achar
        # Ex: ## v5.2.9 ou ## 🚀 v5.2.9
        # Pega tudo até o próximo ##
        pattern = re.compile(r"^##\s+.*?" + re.escape(version_tag) + r"(.*?)(^##|\Z)", re.MULTILINE | re.DOTALL)
        match = pattern.search(content)
        
        if not match:
            # Fallback: pega o primeiro bloco ## qualquer
            pattern = re.compile(r"^##\s+.*?(.*?)(^##|\Z)", re.MULTILINE | re.DOTALL)
            match = pattern.search(content)
            
        if match:
            summary = match.group(1).strip()
            # Limita tamanho para não quebrar o layout
            return summary if len(summary) < 300 else summary[:297] + "..."
            
        return "Sistema atualizado."
    except Exception as e:
        return f"Erro ao ler changelog: {e}"

def create_app():
    app = Flask(__name__)
    
    # 1. Recupera a Versão
    try:
        with open("version.txt", "r") as f:
            version = f.read().strip()
    except:
        version = os.getenv("APP_VERSION", "vDev")

    # 2. Recupera o Changelog
    # Remove o 'v' para buscar no markdown se necessário
    clean_ver = version.replace("v", "")
    changelog_text = get_changelog_summary(clean_ver)

    sys_logger.log("SYSTEM", f"🎵 Melodock Iniciado {version}")
    
    db = Database("/config/melodock.db")
    db.init_db()
    
    metadata = DeezerDataClient()
    downloader = Downloader(db)
    explorer = DeezerExplorer()
    
    app.config['DB'] = db
    app.config['METADATA'] = metadata
    app.config['DOWNLOADER'] = downloader
    app.config['EXPLORER'] = explorer
    
    # 3. Injeta variáveis globais
    @app.context_processor
    def inject_vars():
        return dict(
            system_version=version,
            update_summary=changelog_text
        )
    
    app.register_blueprint(main_bp)
    
    start_queue_worker(app)
    
    return app