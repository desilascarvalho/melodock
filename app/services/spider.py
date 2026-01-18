import math
import time
import random
from .logger import sys_logger

class SpiderService:
    def __init__(self, db, metadata_provider, downloader):
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader

    def run(self):
        # Lê configurações direto do DB existente
        enabled = self.db.get_setting('spider_enabled')
        if enabled != 'true':
            return

        # Defaults definidos aqui no código
        try:
            growth_str = self.db.get_setting('spider_growth_percent')
            growth_percent = float(growth_str) if growth_str else 20.0
            
            fans_str = self.db.get_setting('spider_min_fans')
            min_fans = int(fans_str) if fans_str else 5000
        except:
            growth_percent = 20.0
            min_fans = 5000

        # Conta artistas
        res = self.db.query("SELECT count(*) as c FROM artists", one=True)
        total_artists = res['c']
        
        if total_artists == 0:
            sys_logger.log("SPIDER", "⚠️ Biblioteca vazia. Adicione um artista manualmente.")
            return

        target_new = math.ceil(total_artists * (growth_percent / 100.0))
        target_new = max(1, target_new)
        
        sys_logger.log("SPIDER", f"🕸️ Iniciando. Meta: +{target_new} novos ({growth_percent}%)")

        seeds = self.db.query("SELECT deezer_id, name FROM artists ORDER BY RANDOM() LIMIT 20")
        added_count = 0
        
        for seed in seeds:
            if added_count >= target_new: break
            
            # Pega método que criamos no deezer_data.py
            # Se der erro aqui, certifique-se que atualizou o deezer_data.py com get_related_artists
            try:
                related = self.metadata.get_related_artists(seed['deezer_id'])
            except:
                related = []
            
            for candidate in related:
                if added_count >= target_new: break

                c_id = str(candidate['id'])
                c_name = candidate['name']
                c_fans = candidate.get('nb_fan', 0)
                c_img = candidate.get('picture_xl', candidate.get('picture_medium', ''))

                exists = self.db.query("SELECT 1 FROM artists WHERE deezer_id=?", (c_id,), one=True)
                if exists: continue
                if c_fans < min_fans: continue
                
                try:
                    # 1. Salva Artista
                    self.db.execute("INSERT INTO artists (deezer_id, name, genre) VALUES (?, ?, ?)", 
                                   (c_id, c_name, 'Descoberta Automática'))
                    
                    # 2. Baixa Imagem
                    if c_img:
                        self.downloader.save_artist_image(c_name, c_img)

                    sys_logger.log("SPIDER", f"✨ Descoberto: {c_name} ({c_fans} fãs). Buscando álbuns...")
                    
                    # 3. Busca Discografia
                    albums = self.metadata.get_discography(c_id, target_artist_id=c_name)
                    BLACKLIST = ["playback", "backing track", "karaoke", "instrumental"]
                    alb_count = 0
                    
                    for album in albums:
                        if any(bad in album['title'].lower() for bad in BLACKLIST): continue
                        
                        exists_alb = self.db.query("SELECT 1 FROM queue WHERE deezer_id=?", (album['deezer_id'],), one=True)
                        if not exists_alb:
                            self.db.execute("""
                                INSERT INTO queue (deezer_id, title, artist, type, status, cover_url)
                                VALUES (?, ?, ?, 'album', 'pending', ?)
                            """, (album['deezer_id'], album['title'], c_name, album['cover']))
                            alb_count += 1
                    
                    sys_logger.log("SPIDER", f"   ↳ +{alb_count} álbuns na fila.")
                    added_count += 1
                    
                except Exception as e:
                    sys_logger.log("SPIDER", f"⚠️ Erro ao processar {c_name}: {e}")

                time.sleep(0.5)

        sys_logger.log("SPIDER", f"🏁 Finalizado. +{added_count} novos artistas.")