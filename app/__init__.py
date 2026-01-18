from flask import Flask, jsonify
from .database import Database
from .services.deezer_data import DeezerDataClient 
from .services.downloader import Downloader
from .services.queue import QueueWorker
from .services.scheduler import DailyScheduler
from .services.deezer import DeezerClient as DeezerExplorer

DB_PATH = "/config/melodock.db"

def create_app():
    app = Flask(__name__)
    
    # 1. INICIALIZAÇÃO CRÍTICA DO BANCO
    db = Database(DB_PATH)
    db.init_db() 
    
    # 2. Serviços
    metadata_provider = DeezerDataClient()
    downloader = Downloader()
    explorer = DeezerExplorer()
    
    # 3. Workers
    worker = QueueWorker(db, metadata_provider, downloader)
    worker.start()
    
    # Passamos 'downloader' para o Scheduler
    scheduler = DailyScheduler(db, metadata_provider, downloader)
    scheduler.start()
    
    # 4. Configuração do Flask
    app.config['DB'] = db
    app.config['METADATA'] = metadata_provider
    app.config['DOWNLOADER'] = downloader
    app.config['EXPLORER'] = explorer
    
    # --- VERSÃO DINÂMICA (Lê do arquivo gerado pelo Docker) ---
    try:
        with open("version.txt", "r") as f:
            version_str = f.read().strip()
    except FileNotFoundError:
        version_str = "Dev Mode (Sem version.txt)"

    # Injeta a variável 'system_version' em TODOS os templates automaticamente
    @app.context_processor
    def inject_version():
        return dict(system_version=version_str)
    # ----------------------------------------------------------
    
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    return app