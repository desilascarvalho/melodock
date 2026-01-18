import os
import time
import random
import requests
import yt_dlp
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCON, ID3NoHeaderError
from mutagen.mp3 import MP3
from .logger import sys_logger

FINAL_ROOT = "/downloads"

class Downloader:
    def __init__(self):
        # --- CONFIGURAÇÃO CORRIGIDA E MAIS ROBUSTA ---
        self.base_opts = {
            # Tenta pegar qualquer melhor áudio disponível
            'format': 'bestaudio/best',
            
            # Converte tudo para MP3 192kbps (Equilíbrio ideal e compatível)
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata',
            }],
            
            # Configurações de Silêncio e Erros
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'ignoreerrors': True, # Ignora vídeos com erro para não travar o álbum
            'no_check_certificate': True,
            
            # Evita baixar playlists inteiras se o link for uma
            'noplaylist': True,
        }

    def sanitize(self, name):
        if not name: return "Unknown"
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

    def filter_video(self, video_entry, track_meta):
        # Lógica de filtro (mantida igual)
        title = video_entry.get('title', '').lower()
        original_title = track_meta['title'].lower()
        album_title = track_meta.get('album', '').lower()
        
        BAD_KEYWORDS = ['live', 'ao vivo', 'concert', 'show', 'reaction', 'cover', 'remix']
        is_live_album = 'live' in album_title or 'ao vivo' in album_title
        
        if not is_live_album:
            for bad in BAD_KEYWORDS:
                if bad in title and bad not in original_title: return False

        deezer_duration = track_meta.get('duration', 0)
        video_duration = video_entry.get('duration', 0)
        
        if deezer_duration > 0 and video_duration > 0:
            if abs(deezer_duration - video_duration) > 8: return False

        return True

    def download_track(self, track_meta, target_folder):
        try:
            # Pausa tática para evitar bloqueio
            time.sleep(random.randint(2, 5))

            safe_title = self.sanitize(track_meta['title'])
            filename = f"{str(track_meta.get('track_num', 0)).zfill(2)} - {safe_title}"
            output_template = os.path.join(target_folder, filename)
            
            # Se já existe o MP3, pula
            if os.path.exists(output_template + ".mp3"): return True

            opts = self.base_opts.copy()
            opts['outtmpl'] = output_template

            # 1. Link Manual (Prioridade)
            if track_meta.get('manual_url'):
                sys_logger.log("DL", f"🔗 Link manual: {track_meta['title']}")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([track_meta['manual_url']])
                return self._apply_tags(output_template + ".mp3", track_meta)

            # 2. Busca Inteligente (com Álbum)
            query_specific = f"{track_meta['artist']} - {track_meta['title']} {track_meta['album']} Audio"
            
            search_opts = {
                'quiet': True, 'extract_flat': True, 'noplaylist': True,
                'no_check_certificate': True
            }

            video_id = None

            # Tenta busca específica
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                try:
                    results = ydl.extract_info(f"ytsearch5:{query_specific}", download=False)
                    if 'entries' in results:
                        for entry in results['entries']:
                            if self.filter_video(entry, track_meta):
                                video_id = entry['id']
                                break
                except: pass
            
            # 3. Fallback (Busca Genérica se a específica falhar)
            if not video_id:
                query_generic = f"{track_meta['artist']} - {track_meta['title']} Audio"
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    try:
                        results = ydl.extract_info(f"ytsearch5:{query_generic}", download=False)
                        if 'entries' in results:
                            for entry in results['entries']:
                                if self.filter_video(entry, track_meta):
                                    video_id = entry['id']
                                    break
                            # Se filtro for muito rígido, pega o primeiro
                            if not video_id and results['entries']:
                                video_id = results['entries'][0]['id']
                    except: pass

            # 4. Realiza o Download
            if video_id:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([video_id])
                return self._apply_tags(output_template + ".mp3", track_meta)
            
            return False

        except Exception as e:
            sys_logger.log("ERROR", f"Falha DL {track_meta['title']}: {e}")
            return False

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
            # Remove tags antigas se existirem
            try: 
                audio = MP3(path, ID3=ID3)
                audio.delete()
                audio.save()
            except ID3NoHeaderError: pass
            except: pass # Arquivo pode não existir se o download falhou silenciosamente

            if not os.path.exists(path): return False

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
        except Exception as e:
            sys_logger.log("ERROR", f"Erro Tagging: {e}")
            return True # Retorna True pois o audio foi baixado, só a tag falhou