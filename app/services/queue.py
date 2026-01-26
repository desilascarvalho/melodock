import threading
import time
import os
import shutil
import random
from collections import defaultdict
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
        self.last_artist = None # Memória para o rodízio

    def _get_next_smart_album(self):
        """
        Lógica de Rodízio:
        1. Pega todos os álbuns pendentes.
        2. Agrupa por artista.
        3. Tenta escolher um artista diferente do anterior.
        4. Retorna o primeiro álbum pendente desse artista.
        """
        pending_albums = self.db.query("SELECT * FROM queue WHERE status='pending' ORDER BY id ASC")
        
        if not pending_albums:
            return None

        # Agrupa
        groups = defaultdict(list)
        for alb in pending_albums:
            groups[alb['artist']].append(alb)
        
        candidates = list(groups.keys())
        
        # Tenta mudar de artista
        chosen_artist = candidates[0]
        if len(candidates) > 1 and self.last_artist in candidates:
            others = [a for a in candidates if a != self.last_artist]
            if others:
                chosen_artist = random.choice(others)
        
        self.last_artist = chosen_artist
        
        # Retorna o primeiro álbum da fila deste artista
        return groups[chosen_artist][0]

    def run(self):
        sys_logger.log("WORKER", "⚡ Modo Turbo-Stealth (Smart Shuffle) Iniciado")

        while True:
            try:
                # 1. Escolhe o próximo álbum usando a lógica inteligente
                album_info = self._get_next_smart_album()
                
                if not album_info:
                    time.sleep(5)
                    continue

                qid = album_info['id']
                
                # Marca álbum como baixando
                self.db.execute("UPDATE queue SET status='downloading' WHERE id=?", (qid,))
                sys_logger.log("WORKER", f"🎲 Sorteado: {album_info['artist']}")
                sys_logger.log("WORKER", f"📥 Iniciando: {album_info['title']}")

                # 2. Prepara pastas
                safe_album_artist = self.downloader.sanitize(album_info['artist'])
                safe_album = self.downloader.sanitize(album_info['title'])

                temp_dir = os.path.join("/downloads", safe_album_artist, safe_album)
                final_dir = os.path.join("/music", safe_album_artist, safe_album)

                os.makedirs(temp_dir, exist_ok=True)
                os.makedirs(final_dir, exist_ok=True)

                # 3. Pega faixas
                tracks = self.db.query("SELECT * FROM tracks WHERE queue_id=? AND status='pending'", (qid,))
                track_count = len(tracks)

                for track in tracks:
                    # Verifica cancelamento
                    if not self.db.query("SELECT id FROM tracks WHERE id=?", (track['id'],), one=True):
                        break

                    self.db.execute("UPDATE tracks SET status='downloading' WHERE id=?", (track['id'],))

                    # --- CORREÇÃO DO CRASH (dict) ---
                    t_data = dict(track)
                    
                    meta = {
                        "deezer_id": t_data['deezer_id'],
                        "title": t_data['title'],
                        "artist": t_data.get('artist') or album_info['artist'], # Artista da faixa ou do álbum
                        "album_artist": album_info['artist'],
                        "track_num": t_data.get('track_number')
                    }

                    # Download
                    downloaded_files = self.downloader.download_track(meta, temp_dir)

                    if downloaded_files:
                        moved = 0
                        for fp in downloaded_files:
                            try:
                                dest = os.path.join(final_dir, os.path.basename(fp))
                                if os.path.exists(dest): os.remove(dest)
                                shutil.move(fp, dest)
                                moved += 1
                            except: pass

                        status = 'completed' if moved > 0 else 'error'
                        self.db.execute("UPDATE tracks SET status=? WHERE id=?", (status, t_data['id']))
                        
                        if status == 'completed':
                            sys_logger.log("SUCCESS", f"✅ Baixado: {t_data['title']}")
                            self.session_downloads += 1
                        else:
                            sys_logger.log("ERROR", f"❌ Falha ao mover: {t_data['title']}")
                    else:
                        self.db.execute("UPDATE tracks SET status='error' WHERE id=?", (t_data['id'],))
                        sys_logger.log("ERROR", f"❌ Falha no download: {t_data['title']}")

                    # Pausa entre faixas
                    time.sleep(random.uniform(3.0, 6.0))

                # 4. Finaliza Álbum
                remaining = self.db.query("SELECT count(*) as c FROM tracks WHERE queue_id=? AND status='pending'", (qid,), one=True)
                if remaining['c'] == 0:
                    errs = self.db.query("SELECT count(*) as c FROM tracks WHERE queue_id=? AND status='error'", (qid,), one=True)
                    f_status = 'error' if errs['c'] > 0 else 'completed'
                    self.db.execute("UPDATE queue SET status=? WHERE id=?", (f_status, qid))

                # Limpa temp
                try: os.rmdir(temp_dir)
                except: pass

                # 5. Pausa Inteligente entre Álbuns (Troca de Artista)
                wait = random.randint(15, 30)
                if self.session_downloads > self.max_session:
                    wait = 600
                    self.session_downloads = 0
                    self.max_session = random.randint(40, 60)
                    sys_logger.log("WORKER", "☕ Pausa longa (Anti-Ban)...")
                
                sys_logger.log("WORKER", f"🔄 Trocando artista em {wait}s...")
                time.sleep(wait)

            except Exception as e:
                sys_logger.log("ERROR", f"Worker Crash: {e}")
                time.sleep(10)