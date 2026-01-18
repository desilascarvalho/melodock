import threading
import time
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from .logger import sys_logger

TEMP_ROOT = "/downloads/.processing"
FINAL_ROOT = "/downloads"
MUSIC_LIB_DIR = "/music"
MAX_WORKERS = 2 

class QueueWorker(threading.Thread):
    def __init__(self, db, metadata_provider, downloader):
        super().__init__()
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader
        self.daemon = True
        self.running = True

    def run(self):
        sys_logger.log("WORKER", f"🚀 Iniciado (Threads: {MAX_WORKERS})")
        
        while self.running:
            task_row = self.db.query("""
                SELECT * FROM queue 
                WHERE status IN ('high_priority', 'pending') 
                ORDER BY CASE WHEN status='high_priority' THEN 1 ELSE 2 END, id ASC 
                LIMIT 1
            """, one=True)
            
            if not task_row:
                time.sleep(2)
                continue

            task = dict(task_row)
            self.db.execute("UPDATE queue SET status='downloading' WHERE id=?", (task['id'],))
            sys_logger.log("WORKER", f"📥 Iniciando Álbum: {task['title']}")

            try:
                # Busca faixas no DB
                db_tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=? ORDER BY track_number", (task['id'],))
                
                # Se não tiver faixas, busca na API
                if not db_tracks:
                    if not task.get('deezer_id'): raise Exception("Álbum sem Deezer ID")

                    api_tracks = self.metadata.get_album_tracks(task['deezer_id'], fallback_artist=task['artist'])
                    if not api_tracks: 
                        sys_logger.log("WORKER", "⚠️ Nenhuma faixa encontrada na API.")
                    
                    for t in api_tracks:
                        # --- MUDANÇA: Salvando duration ---
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
                
                def process_track(track_row):
                    row_dict = dict(track_row)
                    
                    meta = {
                        'title': row_dict['title'],
                        'artist': row_dict['artist'],
                        'album': task['title'],
                        'album_artist': task['artist'],
                        'track_num': row_dict['track_number'],
                        'track_count': total_tracks,
                        'manual_url': row_dict.get('manual_url'),
                        'cover_url': task.get('cover_url'),
                        # --- MUDANÇA: Passando duration para o downloader ---
                        'duration': row_dict.get('duration', 0)
                    }
                    
                    if self.downloader.download_track(meta, download_dir):
                        self.db.execute("UPDATE tracks SET status='completed', error_msg=NULL WHERE id=?", (row_dict['id'],))
                        return True
                    else:
                        self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (row_dict['id'],))
                        return False

                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_track = {executor.submit(process_track, t): t for t in db_tracks}
                    for future in as_completed(future_to_track):
                        if future.result(): success_count += 1

                # Finalização e Movimentação
                if success_count > 0:
                    new_status = 'completed'
                    try:
                        artist_dest = os.path.join(MUSIC_LIB_DIR, safe_artist)
                        os.makedirs(artist_dest, exist_ok=True)
                        final_dest_dir = os.path.join(artist_dest, safe_album)
                        
                        if os.path.exists(final_dest_dir): shutil.rmtree(final_dest_dir)
                        shutil.move(download_dir, final_dest_dir)
                        sys_logger.log("MOVE", f"🚚 Movido para biblioteca: {final_dest_dir}")
                        try: os.rmdir(os.path.dirname(download_dir))
                        except: pass
                    except Exception as move_err:
                        sys_logger.log("ERROR", f"Falha ao mover arquivos: {move_err}")
                else:
                    new_status = 'error'

                self.db.execute("UPDATE queue SET status=? WHERE id=?", (new_status, task['id']))
                sys_logger.log("SUCCESS", f"🏁 Finalizado: {task['title']} ({success_count}/{total_tracks})")

            except Exception as e:
                sys_logger.log("ERROR", f"Falha no álbum {task['title']}: {e}")
                self.db.execute("UPDATE queue SET status='error', error_msg=? WHERE id=?", (str(e), task['id']))
            
            sys_logger.log("WORKER", "💤 Pausa entre álbuns...")
            time.sleep(5)