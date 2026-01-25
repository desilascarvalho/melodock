import requests
import time
import re
from difflib import SequenceMatcher
from .logger import sys_logger

class DeezerDataClient:
    BASE_URL = "https://api.deezer.com"

    def _get(self, endpoint, params=None):
        try:
            res = requests.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=15)
            time.sleep(0.2)
            return res.json()
        except: return {}

    def get_artist_by_id(self, artist_id):
        data = self._get(f"/artist/{artist_id}")
        if 'name' in data:
            return {
                'id': str(data['id']),
                'name': data['name'],
                'genre': 'Music',
                'image': data.get('picture_xl', data.get('picture_medium', ''))
            }
        return None

    def search_artist(self, name):
        data = self._get("/search/artist", params={'q': name, 'limit': 1})
        if data.get('data'):
            item = data['data'][0]
            return {
                'id': str(item['id']),
                'name': item['name'],
                'image': item.get('picture_xl')
            }
        return None

    def find_potential_artists(self, name):
        data = self._get("/search/artist", params={'q': name, 'limit': 5})
        results = []
        for item in data.get('data', []):
            results.append({
                'id': str(item['id']),
                'name': item['name'],
                'genre': f"{item.get('nb_fan', 0)} fãs",
                'image': item.get('picture_medium', '')
            })
        return results

    # --- LÓGICA DE FILTRAGEM ---
    def get_discography(self, artist_id, target_artist_id=None, blacklist=None):
        albums = []
        next_url = f"/artist/{artist_id}/albums?limit=100"
        target_norm = target_artist_id.lower().strip() if target_artist_id else ""
        
        # Garante que a blacklist seja uma lista de strings limpas
        if not blacklist: blacklist = []
        # Normaliza a blacklist para lowercase para comparação justa
        blacklist = [b.lower().strip() for b in blacklist if b.strip()]

        while next_url:
            endpoint = next_url.replace(self.BASE_URL, "")
            data = self._get(endpoint)
            
            for item in data.get('data', []):
                title = item['title']
                title_lower = title.lower()

                # 1. FILTRO DE PALAVRAS (O QUE VOCÊ DIGITOU NO SETTINGS)
                # Verifica se QUALQUER palavra da blacklist está contida no título
                blocked_word = next((bad for bad in blacklist if bad in title_lower), None)
                if blocked_word:
                    sys_logger.log("FILTER", f"🚫 Ignorado (Filtro '{blocked_word}'): {title}")
                    continue

                # 2. FILTRO DE TIPO 'COMPILE' (Nativo do Deezer)
                # Mesmo que não esteja na blacklist, se o Deezer disser que é coletânea, ignora.
                rec_type = item.get('record_type', 'album').lower()
                if rec_type == 'compile':
                    sys_logger.log("FILTER", f"🚫 Ignorado (Coletânea): {title}")
                    continue

                # 3. DOUBLE-CHECK DE ARTISTA
                try:
                    album_artist = item.get('artist', {}).get('name', '').lower().strip()
                    if not album_artist:
                        det = self._get(f"/album/{item['id']}")
                        album_artist = det.get('artist', {}).get('name', '').lower().strip()
                    
                    if not album_artist.startswith(target_norm): continue
                    if "various" in album_artist or "vários" in album_artist: continue
                except: continue

                albums.append({
                    'deezer_id': str(item['id']),
                    'title': title,
                    'year': item.get('release_date', '0000')[:4],
                    'track_count': item.get('nb_tracks', 0),
                    'type': rec_type,
                    'cover': item.get('cover_xl', item.get('cover_medium', ''))
                })
            
            next_url = data.get('next')
        return albums

    def get_album_tracks(self, album_id, fallback_artist=""):
        data = self._get(f"/album/{album_id}/tracks?limit=500")
        tracks = []
        main_artist = fallback_artist
        
        for item in data.get('data', []):
            t_title = item['title']
            t_artist = item.get('artist', {}).get('name', main_artist)
            final_artist_tag = main_artist
            
            if t_artist != main_artist:
                guest = t_artist.replace(main_artist, "").strip()
                guest = re.sub(r"^[,&e\s]+", "", guest).strip()
                if guest and len(guest) > 1:
                    if "feat" not in t_title.lower() and "ft." not in t_title.lower():
                        t_title = f"{t_title} (feat. {guest})"

            tracks.append({
                'deezer_id': str(item['id']),
                'title': t_title,
                'artist': final_artist_tag,
                'album_artist': final_artist_tag,
                'track_num': item.get('track_position', 0) or item.get('track_index', 0),
                'duration': item.get('duration', 0)
            })
            
        return tracks