import threading
import time
import os
import shutil
import random
from .logger import sys_logger

class QueueWorker(threading.Thread):
    def __init__(self, db, metadata_provider, downloader):
        super().__init__()
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader
        self.daemon = True
        self.session_downloads = 0
        self.max_session = random.randint(40, 60)

    def run(self):
        sys_logger.log("WORKER", "⚡ Modo Turbo-Stealth (Deemix) Iniciado")
        
        while True:
            album_row = self.db.query("SELECT DISTINCT queue_id FROM tracks WHERE status='pending' ORDER BY id ASC LIMIT 1", one=True)
            if not album_row:
                time.sleep(5)
                continue

            qid = album_row['queue_id']
            album_info = self.db.query("SELECT * FROM queue WHERE id=?", (qid,), one=True)
            if not album_info: continue

            self.db.execute("UPDATE queue SET status='downloading' WHERE id=?", (qid,))
            sys_logger.log("WORKER", f"📥 Iniciando: {album_info['title']}")

            safe_artist = self.downloader.sanitize(album_info['artist'])
            safe_album = self.downloader.sanitize(album_info['title'])
            temp_dir = os.path.join("/downloads", safe_artist, safe_album)
            final_dir = os.path.join("/music", safe_artist, safe_album)
            os.makedirs(temp_dir, exist_ok=True)
            os.makedirs(final_dir, exist_ok=True)

            tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=? AND status='pending'", (qid,))
            track_count_in_this_album = len(tracks)

            for track in tracks:
                check_exists = self.db.query("SELECT id FROM tracks WHERE id=?", (track['id'],), one=True)
                if not check_exists:
                    sys_logger.log("WORKER", "🛑 Parando: Removido da fila.")
                    break

                self.db.execute("UPDATE tracks SET status='downloading' WHERE id=?", (track['id'],))
                
                meta = {'deezer_id': track['deezer_id'], 'title': track['title'], 'track_num': track['track_number']}

                if self.downloader.download_track(meta, temp_dir):
                    for f in os.listdir(temp_dir):
                        if f.endswith(('.mp3', '.flac', '.m4a')):
                            try: shutil.move(os.path.join(temp_dir, f), os.path.join(final_dir, f))
                            except: pass
                    self.db.execute("UPDATE tracks SET status='completed' WHERE id=?", (track['id'],))
                    sys_logger.log("SUCCESS", f"✅ Baixado: {track['title']}")
                    self.session_downloads += 1
                else:
                    self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (track['id'],))
                    sys_logger.log("ERROR", f"❌ Falha: {track['title']}")

                time.sleep(random.uniform(3.0, 6.0))

            remaining = self.db.query("SELECT count(*) as c FROM tracks WHERE queue_id=? AND status='pending'", (qid,), one=True)
            if remaining and remaining['c'] == 0:
                check_alb = self.db.query("SELECT id FROM queue WHERE id=?", (qid,), one=True)
                if check_alb:
                    self.db.execute("UPDATE queue SET status='completed' WHERE id=?", (qid,))
            
            try: os.rmdir(temp_dir)
            except: pass

            # --- LÓGICA DE PAUSA INTELIGENTE ---
            wait = random.randint(20, 40)
            
            # Se foi um álbum gigante (>30 faixas), descansa mais
            if track_count_in_this_album > 30:
                wait = random.randint(120, 180) # 2 a 3 minutos
                sys_logger.log("WORKER", f"😅 Álbum grande finalizado. Pausa de recuperação: {wait}s...")
            
            # Se atingiu o limite da sessão
            elif self.session_downloads > self.max_session:
                wait = 600
                self.session_downloads = 0
                self.max_session = random.randint(40, 60)
                sys_logger.log("WORKER", f"☕ Pausa longa de sessão (Anti-Ban)...")
            else:
                sys_logger.log("WORKER", f"💤 Pausa Stealth: {wait}s...")
            
            time.sleep(wait)