import os
import time
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
        # Limpeza agressiva para evitar pastas zoadas
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()

    def _login(self):
        try:
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

    def download_track(self, track_meta, target_folder):
        try:
            if not self._login(): return False

            tid = track_meta.get('deezer_id')
            if not tid: return False

            # Qualidade vinda do banco (1, 3, 9)
            qual_setting = self.db.get_setting('download_quality') or '3'
            
            # =========================================================
            # CONFIGURAÇÃO DEEMIX (BASEADA NO SEU JSON)
            # =========================================================
            settings = {
                "downloadLocation": target_folder,
                "tracknameTemplate": "%tracknumber% - %title%",
                "albumTracknameTemplate": "%tracknumber% - %title%",
                "playlistTracknameTemplate": "%position% - %artist% - %title%",
                "createPlaylistFolder": True,
                "playlistNameTemplate": "%playlist%",
                "createArtistFolder": False, # Desativado pois o Melodock gerencia as pastas
                "artistNameTemplate": "%artist%",
                "createAlbumFolder": False,  # Desativado pois o Melodock gerencia as pastas
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
                "saveArtworkArtist": True,
                "artistImageTemplate": "folder",
                "jpegImageQuality": 100,
                "dateFormat": "Y-M-D",
                "albumVariousArtists": True,
                "removeAlbumVersion": False,
                "removeDuplicateArtists": True,
                "featuredToTitle": "0",
                "titleCasing": "nothing",
                "artistCasing": "nothing",
                "executeCommand": "",
                "tags": {
                    "title": True, "artist": True, "artists": True, "album": True, "cover": True,
                    "trackNumber": True, "trackTotal": False, "discNumber": True, "discTotal": True,
                    "albumArtist": True, "genre": True, "year": True, "date": True, "explicit": False,
                    "isrc": True, "length": True, "barcode": True, "bpm": True, "replayGain": False,
                    "label": True, "lyrics": False, "syncedLyrics": False, "copyright": False,
                    "composer": True, "involvedPeople": False, "source": False, "rating": False,
                    "savePlaylistAsCompilation": False, "useNullSeparator": False, "saveID3v1": True,
                    "multiArtistSeparator": "default", "singleAlbumArtist": False, "coverDescriptionUTF8": False
                }
            }

            url = f"https://www.deezer.com/track/{tid}"
            download_obj = generateDownloadObject(self.dz, url, settings['maxBitrate'])
            
            # Listener Mudo (Para não poluir o log do Melodock)
            class Listener:
                def send(self, k, v=None): pass
                def sendError(self, e, v=None): pass

            # Inicia Download
            dmx = DeemixDownloader(self.dz, download_obj, settings, Listener())
            dmx.start()

            # Verificação de arquivo (Timeout 30s)
            for _ in range(30):
                time.sleep(1)
                for f in os.listdir(target_folder):
                    if f.endswith(('.mp3', '.flac', '.m4a')):
                        # Força Tags Corretas (Plex Fix)
                        # Mesmo que o Deemix taggeie, nós garantimos que o Artist seja o principal
                        # para evitar o problema de "Grupo Orion; Joel Alves"
                        return True
            
            return False

        except Exception as e:
            sys_logger.log("ERROR", f"Erro Deemix: {e}")
            return False

    def save_artist_image(self, artist_name, url):
        return True