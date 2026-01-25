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
        # Limpeza segura para nomes de pastas
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
        """Baixa a imagem do artista para a pasta de config"""
        try:
            if not url: return False
            safe_name = self.sanitize(artist_name)
            save_path = f"/config/artist_images/{safe_name}.jpg"
            
            # Se já existe, não baixa de novo
            if os.path.exists(save_path): return True
            
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Baixa
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
            # O 'title' e 'track_num' aqui são usados apenas para log/display se necessário,
            # o Deemix vai pegar os dados reais da API.
            
            # No entanto, para garantir que o PLEX não fique louco, 
            # precisamos que o artista principal seja passado corretamente se formos usar templates customizados.
            # Mas o Deemix lida bem com isso se usarmos a opção featuredToTitle correta.

            qual_setting = self.db.get_setting('download_quality') or '3'
            
            # =========================================================
            # CONFIGURAÇÃO DEEMIX (CORRIGIDA PARA PLEX)
            # =========================================================
            settings = {
                "downloadLocation": target_folder,
                "tracknameTemplate": "%tracknumber% - %title%",
                "albumTracknameTemplate": "%tracknumber% - %title%",
                "playlistTracknameTemplate": "%position% - %artist% - %title%",
                "createPlaylistFolder": True,
                "playlistNameTemplate": "%playlist%",
                "createArtistFolder": False, # Melodock gerencia
                "createAlbumFolder": False,  # Melodock gerencia
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
                "saveArtworkArtist": True, # Nós salvamos manualmente
                "jpegImageQuality": 100,
                "dateFormat": "Y-M-D",
                "albumVariousArtists": True,
                "removeAlbumVersion": False,
                "removeDuplicateArtists": True,
                
                # --- AQUI ESTÁ O SEGREDO DO PLEX ---
                # "2" move o feat para o título E remove da tag artist
                "featuredToTitle": "2", 
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
            
            # Listener Mudo
            class Listener:
                def send(self, k, v=None): pass
                def sendError(self, e, v=None): pass

            # Inicia Download
            dmx = DeemixDownloader(self.dz, download_obj, settings, Listener())
            dmx.start()

            # Verificação de arquivo (Timeout 45s para FLAC)
            for _ in range(45):
                time.sleep(1)
                # Verifica se existe algum arquivo de áudio na pasta
                if os.path.exists(target_folder):
                    files = [f for f in os.listdir(target_folder) if f.endswith(('.mp3', '.flac', '.m4a'))]
                    if files:
                        return True
            
            return False

        except Exception as e:
            sys_logger.log("ERROR", f"Erro Deemix: {e}")
            return False