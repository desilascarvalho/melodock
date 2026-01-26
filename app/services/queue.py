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
            try:
                # Busca o próximo álbum pendente
                album_row = self.db.query(
                    "SELECT DISTINCT queue_id FROM tracks WHERE status='pending' ORDER BY id ASC LIMIT 1",
                    one=True
                )
                
                if not album_row:
                    time.sleep(5)
                    continue

                qid = album_row['queue_id']
                album_info = self.db.query("SELECT * FROM queue WHERE id=?", (qid,), one=True)
                
                if not album_info:
                    time.sleep(2)
                    continue

                self.db.execute("UPDATE queue SET status='downloading' WHERE id=?", (qid,))
                sys_logger.log("WORKER", f"📥 Iniciando: {album_info['title']}")

                # Sanitização de nomes para criar pastas
                safe_album_artist = self.downloader.sanitize(album_info['artist'])
                safe_album = self.downloader.sanitize(album_info['title'])

                temp_dir = os.path.join("/downloads", safe_album_artist, safe_album)
                final_dir = os.path.join("/music", safe_album_artist, safe_album)

                os.makedirs(temp_dir, exist_ok=True)
                os.makedirs(final_dir, exist_ok=True)

                tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=? AND status='pending'", (qid,))
                track_count_in_this_album = len(tracks)

                for track in tracks:
                    # Verifica se a faixa ainda existe (caso o usuário tenha cancelado)
                    check_exists = self.db.query("SELECT id FROM tracks WHERE id=?", (track['id'],), one=True)
                    if not check_exists:
                        sys_logger.log("WORKER", "🛑 Parando: Removido da fila.")
                        break

                    self.db.execute("UPDATE tracks SET status='downloading' WHERE id=?", (track['id'],))

                    # --- CORREÇÃO CRÍTICA AQUI ---
                    # Convertemos a row do SQLite para dict para poder usar .get()
                    track_dict = dict(track)
                    
                    meta = {
                        "deezer_id": track_dict['deezer_id'],
                        "title": track_dict['title'],
                        # Usa o artista da faixa ou, se falhar, do álbum
                        "artist": track_dict.get('artist') or album_info['artist'],
                        "album_artist": album_info['artist'],
                        "track_num": track_dict.get('track_number')
                    }

                    # Chama o downloader
                    downloaded_files = self.downloader.download_track(meta, temp_dir)

                    if downloaded_files:
                        moved = 0
                        for fp in downloaded_files:
                            try:
                                dest = os.path.join(final_dir, os.path.basename(fp))
                                if os.path.exists(dest):
                                    os.remove(dest) # Sobrescreve se existir
                                shutil.move(fp, dest)
                                moved += 1
                            except Exception as e:
                                sys_logger.log("ERROR", f"Erro ao mover arquivo: {e}")

                        if moved > 0:
                            self.db.execute("UPDATE tracks SET status='completed' WHERE id=?", (track['id'],))
                            sys_logger.log("SUCCESS", f"✅ Baixado: {track['title']}")
                            self.session_downloads += 1
                        else:
                            self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (track['id'],))
                            sys_logger.log("ERROR", f"❌ Falha ao mover: {track['title']}")
                    else:
                        self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (track['id'],))
                        sys_logger.log("ERROR", f"❌ Falha no download: {track['title']}")

                    # Pausa aleatória entre faixas (Stealth)
                    time.sleep(random.uniform(3.0, 6.0))

                # Verifica se o álbum acabou
                remaining = self.db.query(
                    "SELECT count(*) as c FROM tracks WHERE queue_id=? AND status='pending'",
                    (qid,),
                    one=True
                )
                
                if remaining and remaining['c'] == 0:
                    # Se não tem mais pendentes, verifica se houve erros
                    errors = self.db.query(
                        "SELECT count(*) as c FROM tracks WHERE queue_id=? AND status='error'",
                        (qid,),
                        one=True
                    )
                    final_status = 'error' if errors and errors['c'] > 0 else 'completed'
                    self.db.execute("UPDATE queue SET status=? WHERE id=?", (final_status, qid))

                # Limpeza da pasta temporária
                try:
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                except:
                    pass

                # Pausa entre álbuns
                wait = random.randint(20, 40)
                if track_count_in_this_album > 30:
                    wait = random.randint(120, 180)
                    sys_logger.log("WORKER", f"😅 Álbum grande. Pausa longa: {wait}s...")
                elif self.session_downloads > self.max_session:
                    wait = 600
                    self.session_downloads = 0
                    self.max_session = random.randint(40, 60)
                    sys_logger.log("WORKER", "☕ Pausa de sessão (Anti-Ban)...")
                else:
                    sys_logger.log("WORKER", f"💤 Pausa entre álbuns: {wait}s...")

                time.sleep(wait)

            except Exception as e:
                sys_logger.log("ERROR", f"Erro fatal no Worker: {e}")
                time.sleep(30) # Espera um pouco antes de tentar reiniciar o loop