from flask import Flask
import os
from .database import Database
from .services.deezer_data import DeezerDataClient
from .services.downloader import Downloader
from .routes import main_bp, start_queue_worker
from .services.deezer import DeezerClient as DeezerExplorer
from .services.logger import sys_logger

def create_app():
    app = Flask(__name__)
    
    # 1. Recupera a Versão (MANTIDO DO SEU CÓDIGO)
    try:
        with open("version.txt", "r") as f:
            version = f.read().strip()
    except:
        version = os.getenv("APP_VERSION", "vDev")

    # Log Inicial
    sys_logger.log("SYSTEM", f"🎵 Melodock Iniciado {version}")
    
    # 2. Inicialização do Banco e Serviços
    db = Database("/config/melodock.db")
    db.init_db()
    
    metadata = DeezerDataClient()
    downloader = Downloader(db)
    explorer = DeezerExplorer()
    
    app.config['DB'] = db
    app.config['METADATA'] = metadata
    app.config['DOWNLOADER'] = downloader
    app.config['EXPLORER'] = explorer
    
    # 3. Injeta a versão E o resumo em todos os templates
    @app.context_processor
    def inject_vars():
        return dict(
            system_version=version, # Lê a variável dinâmica que pegamos lá em cima
            update_summary="Correção crítica: Botão 'Limpar Fila' interrompe downloads imediatamente. Importação corrigida para não baixar arquivos existentes."
        )
    
    app.register_blueprint(main_bp)
    
    start_queue_worker(app)
    
    return app