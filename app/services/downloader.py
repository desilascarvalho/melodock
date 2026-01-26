import os
import time
import requests
import traceback
import re
from typing import List, Tuple, Optional

from deezer import Deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader as DeemixDownloader

from .logger import sys_logger

# --- PATCHES DE CORREÇÃO PARA A BIBLIOTECA DEEMIX ---
def apply_patches():
    """Aplica correções em tempo de execução na biblioteca deemix."""
    applied = []
    
    # 1. Patch MEDIA (Evita crash quando a API retorna media vazia - você já tinha este)
    try:
        import deemix.types.Track as track_mod
        original_map_track = track_mod.map_track

        def safe_map_track(track):
            try:
                if isinstance(track, dict):
                    media = track.get("MEDIA")
                    if not media:
                        track["MEDIA"] = [{"HREF": None}]
                    elif isinstance(media, list):
                        if len(media) == 0:
                            track["MEDIA"] = [{"HREF": None}]
                        elif not isinstance(media[0], dict):
                            media[0] = {"HREF": None}
                        else:
                            media[0].setdefault("HREF", None)
                return original_map_track(track)
            except Exception:
                return original_map_track(track)

        track_mod.map_track = safe_map_track
        applied.append("Media Fix")
    except Exception as e:
        sys_logger.log("ERROR", f"Patch Media falhou: {e}")

    # 2. Patch BARCODE/UPC (NOVO: Evita crash quando o álbum não tem código de barras)
    try:
        import deemix.utils.pathtemplates as templates_mod
        original_generate = templates_mod.generateTrackName

        def safe_generate_track_name(template, track, settings):
            # Se o barcode for None, força string vazia para o replace não quebrar
            if hasattr(track, 'album') and track.album:
                if track.album.barcode is None:
                    track.album.barcode = ""
            return original_generate(template, track, settings)

        templates_mod.generateTrackName = safe_generate_track_name
        applied.append("Barcode Fix")
    except Exception as e:
        sys_logger.log("ERROR", f"Patch Barcode falhou: {e}")

    if applied:
        sys_logger.log("SYSTEM", f"🩹 Patches aplicados: {', '.join(applied)}")


class Downloader:
    def __init__(self, db):
        self.db = db
        self.dz = Deezer()
        self.logged_in = False
        
        # Aplica os curativos ao iniciar
        apply_patches()

    def sanitize(self, name):
        if not name: return "Unknown"
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in " .-_()"]).strip()

    def _login(self):
        try:
            if self.logged_in: return True
            arl = self.db.get_setting("deezer_arl")
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
            res = requests.get(url, stream=True, timeout=15)
            if res.status_code == 200:
                with open(save_path, "wb") as f:
                    for chunk in res.iter_content(1024):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            sys_logger.log("ERROR", f"Erro img {artist_name}: {e}")
            return False

    def split_main_and_features(self, artist_str: str) -> Tuple[str, List[str]]:
        if not artist_str: return ("Unknown", [])
        s = artist_str.strip()
        s = re.sub(r"\s+", " ", s)
        
        feat_match = re.split(r"\s+(?:feat\.?|ft\.?|featuring)\s+", s, flags=re.IGNORECASE)
        if len(feat_match) > 1:
            main = re.split(r",|&|;|/|\+", feat_match[0])[0].strip()
            feats = [x.strip() for x in re.split(r",|&|;|/|\+", feat_match[1]) if x.strip()]
            return (main or "Unknown", feats)

        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return (parts[0], parts[1:]) if parts else ("Unknown", [])

        parts = [p.strip() for p in re.split(r"&|;|/|\+", s) if p.strip()]
        if len(parts) > 1: return (parts[0], parts[1:])
        
        return (s, [])

    def apply_feat_to_title(self, title: str, feats: List[str]) -> str:
        if not title: title = "Unknown"
        if not feats: return title
        low = title.lower()
        if "feat" in low or "ft." in low or "featuring" in low: return title
        return f"{title} (feat. {', '.join(feats)})"

    def _tag_file(self, file_path: str, main_artist: str, album_artist: str, new_title: Optional[str] = None) -> bool:
        """
        Força ARTIST e ALBUMARTIST = main_artist (primeiro artista),
        e opcionalmente ajusta TITLE com feat.
        """
        try:
            from mutagen import File as MutagenFile
            from mutagen.id3 import ID3, TPE1, TPE2, TIT2
            
            audio = MutagenFile(file_path, easy=False)
            if not audio: return False
            
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".mp3":
                if audio.tags is None: audio.add_tags()
                audio.tags.delall("TPE1")
                audio.tags.add(TPE1(encoding=3, text=[main_artist]))
                audio.tags.delall("TPE2")
                audio.tags.add(TPE2(encoding=3, text=[album_artist]))
                if new_title:
                    audio.tags.delall("TIT2")
                    audio.tags.add(TIT2(encoding=3, text=[new_title]))
                audio.save()
                return True
                
            if ext in (".flac", ".ogg"):
                audio["ARTIST"] = [main_artist]
                audio["ALBUMARTIST"] = [album_artist]
                if new_title: audio["TITLE"] = [new_title]
                audio.save()
                return True
                
            return False
        except: return False

    def _list_audio_files(self, folder: str) -> List[str]:
        if not os.path.exists(folder): return []
        return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".mp3", ".flac", ".m4a"))]

    def _newest_file(self, folder: str) -> Optional[str]:
        files = self._list_audio_files(folder)
        if not files: return None
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[0]

    def download_track(self, track_meta, target_folder):
        try:
            if not self._login(): return []
            tid = track_meta.get("deezer_id")
            if not tid: return []

            # Prepara pastas e nomes
            raw_artist = (track_meta.get("artist") or "").strip()
            main_artist, feats = self.split_main_and_features(raw_artist)
            album_artist = (track_meta.get("album_artist") or main_artist).strip()
            new_title = self.apply_feat_to_title(track_meta.get("title"), feats)
            
            qual_setting = self.db.get_setting("download_quality") or "3"
            
            # --- CONFIGURAÇÃO BLINDADA ---
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
                
                "featuredToTitle": "2",
                "titleCasing": "nothing",
                "artistCasing": "nothing",
                "multiArtistSeparator": " & ",
                
                # CHAVE OBRIGATÓRIA (Evita KeyError)
                "executeCommand": "",
                
                "tags": {
                    "title": True, "artist": True, "album": True, "cover": True,
                    "trackNumber": True, "trackTotal": False, "discNumber": True, "discTotal": True,
                    "albumArtist": True, "genre": True, "year": True, "date": True,
                    "explicit": False,
                    
                    # DESATIVADOS (Evita crashes com dados faltantes)
                    "isrc": False,
                    "length": False,
                    "barcode": False,
                    "bpm": False,
                    
                    "replayGain": False, "label": True, "lyrics": False, "syncedLyrics": False,
                    "copyright": False, "composer": False, "involvedPeople": False, "source": False,
                    "rating": False, "savePlaylistAsCompilation": False, "useNullSeparator": False,
                    "saveID3v1": True, "multiArtistSeparator": " & ", "singleAlbumArtist": True,
                    "coverDescriptionUTF8": False, "artists": False
                }
            }

            before = set(self._list_audio_files(target_folder))

            url = f"https://www.deezer.com/track/{tid}"
            download_obj = generateDownloadObject(self.dz, url, settings["maxBitrate"])
            
            class Listener:
                def send(self, k, v=None): pass
                def sendError(self, e, v=None): pass

            dmx = DeemixDownloader(self.dz, download_obj, settings, Listener())
            dmx.start()

            # Aguarda e verifica o arquivo
            new_files = []
            for _ in range(45):
                time.sleep(1)
                now = set(self._list_audio_files(target_folder))
                diff = list(now - before)
                if diff:
                    new_files = diff
                    break
            
            # Fallback
            if not new_files:
                nf = self._newest_file(target_folder)
                if nf: new_files = [nf]

            if not new_files: return []

            # Retagging final para garantir limpeza
            for fp in new_files:
                self._tag_file(fp, main_artist=main_artist, album_artist=album_artist, new_title=new_title)

            return new_files

        except Exception as e:
            sys_logger.log("ERROR", f"Erro Deemix: {e}")
            return []