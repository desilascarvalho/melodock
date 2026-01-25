import os
import time
import requests
from deezer import Deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader as DeemixDownloader
from .logger import sys_logger

class Downloader:
    def __init__(self, db):
        self.db = db
        self.dz = Deezer()
        self.logged_in = False

    def sanitize(self, name):
        if not name: return "Unknown"
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

    def _login(self):
        try:
            if self.logged_in: return True
            arl = self.db.get_setting('deezer_arl')
            if not arl:
                sys_logger.log("DL", "⚠️ ARL ausente. Configure em Ajustes.")
                return False
            self.dz.login_via_arl(arl)
            self.logged_in = True
            return True
        except Exception as e:
            sys_logger.log("ERROR", f"Login Deezer falhou: {e}")
            return False

    def save_artist_image(self, artist_name, url):
        try:
            if not url: return False
            safe_name = self.sanitize(artist_name)
            save_path = f"/config/artist_images/{safe_name}.jpg"
            if os.path.exists(save_path): return True
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            res = requests.get(url, stream=True, timeout=10)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in res.iter_content(1024):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            sys_logger.log("ERROR", f"Erro ao salvar imagem de {artist_name}: {e}")
            return False

    def download_track(self, track_meta, target_folder):
        try:
            if not self._login(): return False

            tid = track_meta.get('deezer_id')
            qual_setting = self.db.get_setting('download_quality') or '3'
            
            # =========================================================
            # CONFIGURAÇÃO DEEMIX (MODO SINGLE ARTIST RIGOROSO)
            # =========================================================
            settings = {
                "downloadLocation": target_folder,
                "tracknameTemplate": "%tracknumber% - %title%",
                "albumTracknameTemplate": "%tracknumber% - %title%",
                "playlistTracknameTemplate": "%position% - %artist% - %title%",
                "createPlaylistFolder": True,
                "playlistNameTemplate": "%playlist%",
                "createArtistFolder": False, 
                "createAlbumFolder": False,
                "albumNameTemplate": "%artist% - %album%",
                "createCDFolder": True,
                "createStructurePlaylist": False,
                "createSingleFolder": True,
                "padTracks": True,
                "padSingleDigit": True,
                "paddingSize": "0",
                "illegalCharacterReplacer": "_",
                "queueConcurrency": 1,
                "maxBitrate": int(qual_setting),
                "feelingLucky": False,
                "fallbackBitrate": True, 
                "fallbackSearch": False,
                "fallbackISRC": False,
                "logErrors": True,
                "logSearched": True,
                "overwriteFile": "n",
                "createM3U8File": False,
                "playlistFilenameTemplate": "playlist",
                "syncedLyrics": True,
                "embeddedArtworkSize": 800,
                "embeddedArtworkPNG": False,
                "localArtworkSize": 1200,
                "localArtworkFormat": "jpg",
                "saveArtwork": True,
                "coverImageTemplate": "cover",
                "saveArtworkArtist": False, 
                "jpegImageQuality": 100,
                "dateFormat": "Y-M-D",
                "albumVariousArtists": True,
                "removeAlbumVersion": False,
                "removeDuplicateArtists": True,
                
                # --- CORREÇÃO DE TAGS ---
                # Move feat para o título
                "featuredToTitle": "2", 
                "titleCasing": "nothing",
                "artistCasing": "nothing",
                
                # IMPORTANTE: Força um separador de texto simples.
                # Isso impede que o Plex veja ";" e separe os artistas.
                # O resultado será "Artista A & Artista B" em um único campo, 
                # evitando duplicidade na biblioteca.
                "multiArtistSeparator": " & ",
                
                "tags": {
                    "title": True, 
                    "artist": True, 
                    "album": True, 
                    "cover": True,
                    "trackNumber": True, 
                    "trackTotal": False, 
                    "discNumber": True, 
                    "discTotal": True,
                    "albumArtist": True, 
                    "genre": True, 
                    "year": True, 
                    "date": True, 
                    "explicit": False,
                    "isrc": True, 
                    "length": True, 
                    "barcode": True, 
                    "bpm": True, 
                    "replayGain": False,
                    "label": True, 
                    "lyrics": False, 
                    "syncedLyrics": False, 
                    "copyright": False,
                    
                    # DESATIVANDO TUDO QUE PODE CAUSAR DUPLICIDADE
                    "composer": False, 
                    "involvedPeople": False, 
                    "source": False, 
                    "rating": False,
                    "savePlaylistAsCompilation": False, 
                    "useNullSeparator": False, 
                    "saveID3v1": True,
                    
                    # Reforça o separador visual
                    "multiArtistSeparator": " & ", 
                    "singleAlbumArtist": True, 
                    "coverDescriptionUTF8": False,
                    
                    # Oculta tag plural
                    "artists": False 
                }
            }

            url = f"https://www.deezer.com/track/{tid}"
            download_obj = generateDownloadObject(self.dz, url, settings['maxBitrate'])
            
            class Listener:
                def send(self, k, v=None): pass
                def sendError(self, e, v=None): pass

            dmx = DeemixDownloader(self.dz, download_obj, settings, Listener())
            dmx.start()

            for _ in range(45):
                time.sleep(1)
                if os.path.exists(target_folder):
                    files = [f for f in os.listdir(target_folder) if f.endswith(('.mp3', '.flac', '.m4a'))]
                    if files:
                        return True
            
            return False

        except Exception as e:
            sys_logger.log("ERROR", f"Erro Deemix: {e}")
            return False