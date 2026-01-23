import threading
import time
import os
import shutil
import random
from .logger import sys_logger

TEMP_ROOT = "/downloads/.processing"
FINAL_ROOT = "/downloads"
MUSIC_LIB_DIR = "/music"

# Nota: MAX_WORKERS removido pois agora é sequencial (1 worker)

class QueueWorker(threading.Thread):
    def __init__(self, db, metadata_provider, downloader):
        super().__init__()
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader
        self.daemon = True
        self.running = True

    def run(self):
        sys_logger.log("WORKER", "⚡ Modo Turbo-Stealth (Otimizado)")
        
        while self.running:
            task_row = self.db.query("""
                SELECT * FROM queue 
                WHERE status IN ('high_priority', 'pending') 
                ORDER BY CASE WHEN status='high_priority' THEN 1 ELSE 2 END, id ASC 
                LIMIT 1
            """, one=True)
            
            if not task_row:
                time.sleep(5)
                continue

            task = dict(task_row)
            self.db.execute("UPDATE queue SET status='downloading' WHERE id=?", (task['id'],))
            sys_logger.log("WORKER", f"📥 Iniciando Álbum: {task['title']}")

            try:
                db_tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=? ORDER BY track_number", (task['id'],))
                
                # (Bloco de busca na API se não tiver tracks no DB - Mantido igual)
                if not db_tracks:
                    if not task.get('deezer_id'): raise Exception("Álbum sem Deezer ID")
                    api_tracks = self.metadata.get_album_tracks(task['deezer_id'], fallback_artist=task['artist'])
                    if not api_tracks: raise Exception("API retornou zero faixas")
                    for t in api_tracks:
                        self.db.execute("INSERT INTO tracks (queue_id, title, artist, track_number, status, duration) VALUES (?, ?, ?, ?, 'pending', ?)", 
                                        (task['id'], t['title'], t['artist'], t['track_num'], t.get('duration', 0)))
                    db_tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=?", (task['id'],))

                if not db_tracks: raise Exception("Álbum vazio")

                safe_artist = self.downloader.sanitize(task['artist'])
                safe_album = self.downloader.sanitize(task['title'])
                download_dir = os.path.join(FINAL_ROOT, safe_artist, safe_album)
                os.makedirs(download_dir, exist_ok=True)

                success_count = 0
                total_tracks = len(db_tracks)
                
                # --- OTIMIZAÇÃO AQUI ---
                for i, track_row in enumerate(db_tracks):
                    row_dict = dict(track_row)
                    
                    if row_dict['status'] == 'completed':
                        success_count += 1
                        continue

                    sys_logger.log("DL", f"({i+1}/{total_tracks}) {row_dict['title']}...")

                    meta = {
                        'title': row_dict['title'], 'artist': row_dict['artist'],
                        'album': task['title'], 'album_artist': task['artist'],
                        'track_num': row_dict['track_number'], 'track_count': total_tracks,
                        'manual_url': row_dict.get('manual_url'), 'cover_url': task.get('cover_url'),
                        'duration': row_dict.get('duration', 0),
                        # Passa ISRC se tiver no banco, senão None
                        'isrc': row_dict.get('isrc') if 'isrc' in row_dict else None 
                    }
                    
                    if self.downloader.download_track(meta, download_dir):
                        self.db.execute("UPDATE tracks SET status='completed', error_msg=NULL WHERE id=?", (row_dict['id'],))
                        success_count += 1
                        
                        # --- PAUSA OTIMIZADA ---
                        # Antes: 15 a 45s (Média 30s)
                        # Agora: 5 a 12s (Média 8s)
                        # Motivo: Um humano pula faixas ou ouve trechos. 8s é suficiente para o YouTube não dar flag imediato no client Web.
                        if i < total_tracks - 1:
                            sleep_time = random.randint(5, 12)
                            # Log menos verboso para não poluir
                            # sys_logger.log("WORKER", f"⏳ {sleep_time}s...") 
                            time.sleep(sleep_time)
                    else:
                        self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (row_dict['id'],))
                        # Reduzido de 60s para 10s. Se falhou, pode ser só aquele vídeo.
                        sys_logger.log("WORKER", "⚠️ Erro. Aguardando 10s...")
                        time.sleep(10)

                # Finalização (Mantido igual)
                if success_count > 0:
                    new_status = 'completed' if success_count == total_tracks else 'partial'
                    try:
                        artist_dest = os.path.join(MUSIC_LIB_DIR, safe_artist)
                        os.makedirs(artist_dest, exist_ok=True)
                        final_dest_dir = os.path.join(artist_dest, safe_album)
                        if os.path.exists(final_dest_dir): shutil.rmtree(final_dest_dir)
                        shutil.move(download_dir, final_dest_dir)
                        sys_logger.log("MOVE", f"🚚 Movido: {final_dest_dir}")
                        try: os.rmdir(os.path.dirname(download_dir))
                        except: pass
                    except Exception as move_err:
                        sys_logger.log("ERROR", f"Move err: {move_err}")
                        new_status = 'error'
                else:
                    new_status = 'error'

                self.db.execute("UPDATE queue SET status=? WHERE id=?", (new_status, task['id']))
                sys_logger.log("SUCCESS", f"🏁 Finalizado: {task['title']}")

            except Exception as e:
                sys_logger.log("ERROR", f"Erro no álbum: {e}")
                self.db.execute("UPDATE queue SET status='error', error_msg=? WHERE id=?", (str(e), task['id']))
            
            # --- PAUSA ENTRE ÁLBUNS OTIMIZADA ---
            # Antes: 120s (Fixo)
            # Agora: 20 a 40s (Dinâmico)
            rest_time = random.randint(20, 40)
            sys_logger.log("WORKER", f"💤 Pausa entre álbuns ({rest_time}s)...")
            time.sleep(rest_time)