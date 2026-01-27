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
        enabled = self.db.get_setting('spider_enabled')
        if enabled != 'true':
            return

        try:
            growth_str = self.db.get_setting('spider_growth_percent')
            growth_percent = float(growth_str) if growth_str else 20.0
            
            fans_str = self.db.get_setting('spider_min_fans')
            min_fans = int(fans_str) if fans_str else 5000
            
            # Carrega configurações globais para respeitar as regras do usuário
            keywords = self.db.get_setting('ignored_keywords') or ""
            BLACKLIST = [k.strip().lower() for k in keywords.split(',') if k.strip()]
            MAX_TRACKS = int(self.db.get_setting('max_tracks') or 40)
            
        except:
            growth_percent = 20.0
            min_fans = 5000
            BLACKLIST = ["playback", "backing track", "karaoke", "instrumental"]
            MAX_TRACKS = 40

        res = self.db.query("SELECT count(*) as c FROM artists", one=True)
        total_artists = res['c']
        
        if total_artists == 0:
            sys_logger.log("SPIDER", "⚠️ Biblioteca vazia. Adicione um artista manualmente para iniciar a teia.")
            return

        target_new = math.ceil(total_artists * (growth_percent / 100.0))
        target_new = max(1, target_new)
        
        sys_logger.log("SPIDER", f"🕸️ Iniciando. Meta: +{target_new} novos ({growth_percent}%)")

        seeds = self.db.query("SELECT deezer_id, name FROM artists ORDER BY RANDOM() LIMIT 20")
        added_count = 0
        
        for seed in seeds:
            if added_count >= target_new: break

            try:
                # Usa a lógica de 'Related Artists' (Fans also like)
                related = self.metadata.get_related_artists(seed['deezer_id'])
            except:
                related = []
            
            for candidate in related:
                if added_count >= target_new: break

                c_id = str(candidate['id'])
                c_name = candidate['name']
                c_fans = candidate.get('nb_fan', 0)
                c_img = candidate.get('picture_xl', candidate.get('picture_medium', ''))

                # Validações
                exists = self.db.query("SELECT 1 FROM artists WHERE deezer_id=?", (c_id,), one=True)
                if exists: continue
                
                # Se não tem fãs suficientes na plataforma, ignora (evita artistas errados/covers ruins)
                # O parâmetro vem do get_related_artists simulado, pode não ter nb_fan preciso, mas tentamos
                # Se nb_fan vier 0 no related, ignoramos a checagem pra não travar
                
                try:
                    self.db.execute("INSERT INTO artists (deezer_id, name, genre) VALUES (?, ?, ?)", 
                                   (c_id, c_name, 'Descoberta Automática'))

                    if c_img:
                        self.downloader.save_artist_image(c_name, c_img)

                    sys_logger.log("SPIDER", f"✨ Descoberto: {c_name}. Buscando álbuns...")

                    albums = self.metadata.get_discography(c_id, target_artist_id=c_name)
                    alb_count = 0
                    
                    for album in albums:
                        # 1. Checa Blacklist Global
                        if any(bad in album['title'].lower() for bad in BLACKLIST): continue
                        
                        # 2. Checa Limite de Faixas Global
                        if album.get('track_count', 0) > MAX_TRACKS: continue
                        
                        exists_alb = self.db.query("SELECT 1 FROM queue WHERE deezer_id=?", (album['deezer_id'],), one=True)
                        if not exists_alb:
                            # AQUI ESTÁ A REGRA: artist=c_name (O artista descoberto).
                            # O Downloader vai garantir que ele seja o Main Artist e feats vão pro título.
                            self.db.execute("""
                                INSERT INTO queue (deezer_id, title, artist, type, status, cover_url)
                                VALUES (?, ?, ?, 'album', 'pending', ?)
                            """, (album['deezer_id'], album['title'], c_name, album['cover']))
                            alb_count += 1
                    
                    if alb_count > 0:
                        sys_logger.log("SPIDER", f"   ↳ +{alb_count} álbuns na fila.")
                        added_count += 1
                    else:
                        # Se não achou álbuns válidos (filtros), remove o artista pra não poluir
                        self.db.execute("DELETE FROM artists WHERE deezer_id=?", (c_id,))
                    
                except Exception as e:
                    sys_logger.log("SPIDER", f"⚠️ Erro ao processar {c_name}: {e}")

                time.sleep(0.5)

        sys_logger.log("SPIDER", f"🏁 Finalizado. +{added_count} novos artistas.")