import os
import time
import random
import requests
import yt_dlp
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCON, ID3NoHeaderError
from mutagen.mp3 import MP3
from .logger import sys_logger

FINAL_ROOT = "/downloads"

class SilentLogger:
    """Engole logs inúteis, mas permite erros críticos"""
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): 
        # Filtra erros de "Video unavailable" que são comuns
        if "Video unavailable" not in msg:
            print(f"[YTDLP ERROR] {msg}")

class Downloader:
    def __init__(self):
        self.base_opts = {
            'format': 'ba/b',
            'source_address': '0.0.0.0',
            'extractor_args': {'youtube': {'player_client': ['web', 'android']}},
            'cachedir': False,
            'sleep_interval': 2,      
            'max_sleep_interval': 5,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            },
            {
                'key': 'FFmpegMetadata',
            }],
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'logger': SilentLogger(),
        }

    def sanitize(self, name):
        if not name: return "Unknown"
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

    def filter_video_keywords(self, video_entry, track_meta):
        title = video_entry.get('title', '').lower()
        original_title = track_meta['title'].lower()
        album_title = track_meta.get('album', '').lower()
        
        BAD_KEYWORDS = ['live', 'ao vivo', 'concert', 'show', 'reaction', 'cover', 'remix']
        is_live_album = 'live' in album_title or 'ao vivo' in album_title
        
        if not is_live_album:
            for bad in BAD_KEYWORDS:
                if bad in title and bad not in original_title: return False

        if 'full album' in title or 'completo' in title: return False

        deezer_duration = track_meta.get('duration', 0)
        video_duration = video_entry.get('duration', 0)
        
        if deezer_duration > 0 and video_duration > 0:
            if abs(deezer_duration - video_duration) > 15: return False

        return True

    def download_track(self, track_meta, target_folder):
        try:
            time.sleep(random.randint(3, 8))
            
            safe_title = self.sanitize(track_meta['title'])
            filename = f"{str(track_meta.get('track_num', 0)).zfill(2)} - {safe_title}"
            output_template = os.path.join(target_folder, filename)
            
            if os.path.exists(output_template + ".mp3"): return True

            opts = self.base_opts.copy()
            opts['outtmpl'] = output_template

            # 1. Link Manual
            if track_meta.get('manual_url'):
                sys_logger.log("DL", f"🔗 Link manual: {track_meta['title']}")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([track_meta['manual_url']])
                return self._apply_tags(output_template + ".mp3", track_meta)

            video_id = None
            
            # 2. Busca ISRC
            if not video_id and track_meta.get('isrc'):
                video_id = self._search_candidate(f"\"{track_meta['isrc']}\"", track_meta, strict_duration=2)

            # 3. Busca Topic
            if not video_id:
                query = f"{track_meta['artist']} - {track_meta['title']} Topic"
                video_id = self._search_candidate(query, track_meta, strict_duration=3, prefer_topic=True)

            # 4. Busca Genérica
            if not video_id:
                query = f"{track_meta['artist']} - {track_meta['title']} Audio Lyrics"
                video_id = self._search_candidate(query, track_meta, strict_duration=8)

            if video_id:
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([video_id])
                    
                    if os.path.exists(output_template + ".mp3"):
                        return self._apply_tags(output_template + ".mp3", track_meta)
                except yt_dlp.utils.DownloadError as de:
                    # --- DETECÇÃO DE BLOQUEIO ---
                    msg = str(de).lower()
                    if "429" in msg or "too many requests" in msg:
                        sys_logger.log("CRITICAL", "⛔ BLOQUEIO 429 DETECTADO! Troque a VPN.")
                        raise Exception("IP Blocked") # Força parada do worker
                    if "sign in" in msg or "bot" in msg:
                        sys_logger.log("CRITICAL", "⛔ BLOQUEIO DE BOT DETECTADO! Troque a VPN.")
                        raise Exception("Bot Blocked")
            
            sys_logger.log("DL", f"❌ Falha: Não encontrado ({track_meta['title']})")
            return False

        except Exception as e:
            if "Blocked" in str(e): raise e # Repassa erro crítico pro Worker
            # sys_logger.log("ERROR", f"Erro interno DL: {e}") 
            return False

    def _search_candidate(self, query, meta, strict_duration=5, prefer_topic=False):
        search_opts = {
            'quiet': True, 'extract_flat': True, 'noplaylist': True, 'limit': 5,
            'source_address': '0.0.0.0', 'cachedir': False,
            'logger': SilentLogger(),
            'extractor_args': {'youtube': {'player_client': ['web']}}
        }
        
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            try:
                results = ydl.extract_info(f"ytsearch5:{query}", download=False)
            except Exception as e:
                # Se der erro na BUSCA, também pode ser bloqueio
                if "429" in str(e) or "Sign in" in str(e):
                    sys_logger.log("CRITICAL", "⛔ ERRO NA BUSCA (BLOQUEIO)!")
                return None

            if 'entries' in results:
                for entry in results['entries']:
                    if not entry: continue

                    if not self.filter_video_keywords(entry, meta):
                        continue

                    vid_duration = entry.get('duration', 0)
                    if meta.get('duration') and vid_duration:
                        diff = abs(meta['duration'] - vid_duration)
                        if diff > strict_duration:
                            continue 

                    if prefer_topic:
                        channel = entry.get('uploader', '').lower()
                        is_topic = 'topic' in channel or 'tópico' in channel or 'release' in channel
                        if not is_topic:
                            if abs(meta['duration'] - vid_duration) > 1:
                                continue

                    return entry['id']
        return None

    def save_artist_image(self, artist_name, url):
        try:
            if not url: return False
            hq_url = url.replace('100x100', '1000x1000')
            safe_artist = self.sanitize(artist_name)
            artist_folder = os.path.join(FINAL_ROOT, safe_artist)
            os.makedirs(artist_folder, exist_ok=True)
            img_data = requests.get(hq_url, timeout=10).content
            with open(os.path.join(artist_folder, "poster.jpg"), 'wb') as f: f.write(img_data)
            with open(os.path.join(artist_folder, "cover.jpg"), 'wb') as f: f.write(img_data)
            return True
        except: return False

    def _apply_tags(self, path, meta):
        try:
            try: 
                audio = MP3(path, ID3=ID3)
                audio.delete()
                audio.save()
            except ID3NoHeaderError: pass

            audio = ID3(path, v2_version=3)
            audio.add(TIT2(encoding=3, text=meta['title']))
            audio.add(TPE1(encoding=3, text=meta['artist']))
            album_artist = meta.get('album_artist', meta['artist'])
            audio.add(TPE2(encoding=3, text=album_artist))
            audio.add(TALB(encoding=3, text=meta['album']))
            if meta.get('track_num'):
                track_str = str(meta['track_num'])
                if meta.get('track_count'): track_str += f"/{meta['track_count']}"
                audio.add(TRCK(encoding=3, text=track_str))
            if meta.get('cover_url'):
                try:
                    img_data = requests.get(meta['cover_url'], timeout=10).content
                    audio.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=img_data))
                except: pass
            audio.save(v2_version=3)
            return True
        except: return True