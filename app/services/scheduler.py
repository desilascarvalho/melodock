import threading
import time
import datetime
import os
from .logger import sys_logger
from .spider import SpiderService 
from .maintenance import LibraryMaintenance

MUSIC_LIB_DIR = "/music"

class DailyScheduler(threading.Thread):
    def __init__(self, db, metadata_provider, downloader):
        super().__init__()
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader
        self.daemon = True
        self.last_scan_run = None
        self.last_spider_run = None
        self.last_maint_run = None

    def check_new_releases(self):
        sys_logger.log("SCHEDULER", "⏰ Varredura de lançamentos iniciada...")
        
        artists = self.db.query("SELECT * FROM artists")

        keywords_str = self.db.get_setting('ignored_keywords') or "playback,karaoke,instrumental,backing track"
        BLACKLIST = [k.strip() for k in keywords_str.split(',')]
        max_tracks_val = int(self.db.get_setting('max_tracks') or 40)
        # -----------------------------
        
        count_new = 0
        count_synced = 0
        
        for art in artists:
            try:
                discography = self.metadata.get_discography(art['deezer_id'], target_artist_id=art['name'])
                
                for item in discography:
                    title_lower = item['title'].lower()

                    if any(bad in title_lower for bad in BLACKLIST): continue
                    if item.get('nb_tracks', 0) > max_tracks_val: continue

                    exists = self.db.query("SELECT id FROM queue WHERE deezer_id=?", (item['deezer_id'],), one=True)
                    
                    if not exists:
                        safe_artist = self.downloader.sanitize(art['name'])
                        safe_album = self.downloader.sanitize(item['title'])
                        album_path = os.path.join(MUSIC_LIB_DIR, safe_artist, safe_album)
                        
                        initial_status = 'pending'
                        log_prefix = "✨ Novo"
                        
                        if os.path.exists(album_path):
                            local_files = [f for f in os.listdir(album_path) if f.endswith(('.mp3', '.flac', '.m4a', '.wav'))]
                            local_count = len(local_files)
                            api_total = item.get('nb_tracks', 0)
                            
                            if api_total > 0 and local_count >= api_total:
                                initial_status = 'completed'
                                log_prefix = "📚 Sincronizado"
                                count_synced += 1
                            else:
                                initial_status = 'pending'
                                log_prefix = f"⚠️ Incompleto ({local_count}/{api_total})"
                                count_new += 1
                        else:
                            count_new += 1

                        sys_logger.log("NEW", f"{log_prefix}: {item['title']} - {art['name']}")
                        
                        cur = self.db.execute(
                            "INSERT INTO queue (deezer_id, title, artist, type, status, cover_url) VALUES (?, ?, ?, ?, ?, ?)",
                            (item['deezer_id'], item['title'], art['name'], 'album', initial_status, item['cover'])
                        )
                        queue_id = cur.lastrowid
                        
                        tracks = self.metadata.get_album_tracks(item['deezer_id'], fallback_artist=art['name'])
                        for t in tracks:
                            self.db.execute(
                                "INSERT INTO tracks (queue_id, title, artist, track_number, status) VALUES (?, ?, ?, ?, ?)", 
                                (queue_id, t['title'], t['artist'], t['track_num'], initial_status)
                            )

                time.sleep(1.0)
            except Exception:
                pass
                
        sys_logger.log("SCHEDULER", f"✅ Varredura finalizada. {count_new} enviados para download, {count_synced} já existiam.")

    def run_spider(self):
        try:
            spider = SpiderService(self.db, self.metadata, self.downloader)
            spider.run()
        except Exception as e:
            sys_logger.log("ERROR", f"Falha no Spider: {e}")

    def run_maintenance(self):
        try:
            maint = LibraryMaintenance(self.db, self.metadata, self.downloader)
            maint.run()
        except Exception as e:
            sys_logger.log("ERROR", f"Falha na Manutenção: {e}")

    def run(self):
        sys_logger.log("SCHEDULER", "🕒 Serviço de Agendamento Iniciado.")
        
        while True:
            try:
                now = datetime.datetime.now()
                current_hm = now.strftime("%H:%M")
                today = now.strftime("%Y-%m-%d")

                scan_time = self.db.get_setting('scan_time') or '03:00'
                if current_hm == scan_time and self.last_scan_run != today:
                    self.check_new_releases()
                    self.last_scan_run = today

                if current_hm == "04:00" and self.last_maint_run != today:
                    self.run_maintenance()
                    self.last_maint_run = today

                spider_time = self.db.get_setting('spider_schedule_time') or '12:00'
                if current_hm == spider_time and self.last_spider_run != today:
                    if self.db.get_setting('spider_enabled') == 'true':
                        sys_logger.log("SCHEDULER", f"🤖 Hora do Spider ({spider_time})...")
                        threading.Thread(target=self.run_spider).start()
                    self.last_spider_run = today

                time.sleep(30)

            except Exception as e:
                sys_logger.log("ERROR", f"Erro no Scheduler: {e}")
                time.sleep(30)