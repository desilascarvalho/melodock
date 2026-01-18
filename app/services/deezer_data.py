import requests
import time
import re
from difflib import SequenceMatcher
from .logger import sys_logger 

class DeezerDataClient:
    BASE_URL = "https://api.deezer.com"

    def _get(self, endpoint, params=None):
        try:
            url = f"{self.BASE_URL}{endpoint}"
            res = requests.get(url, params=params, timeout=15)
            time.sleep(0.2) 
            return res.json()
        except: return {}

    def _similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def get_artist_by_id(self, artist_id):
        data = self._get(f"/artist/{artist_id}")
        if data and 'name' in data:
            return {
                'id': str(data['id']),
                'name': data['name'],
                'genre': 'Music',
                'image': data.get('picture_xl', data.get('picture_medium', '')),
                'link': data.get('link', '')
            }
        return None

    def search_artist(self, name):
        data = self._get("/search/artist", params={'q': name, 'limit': 5})
        if not data.get('data'): return None

        best_match = None; best_score = 0.0
        for item in data['data']:
            score = self._similarity(name, item['name'])
            if name.lower() == item['name'].lower(): score = 1.0
            if score > best_score: best_score = score; best_match = item

        if best_score < 0.6: return None

        if best_match:
            return {
                'id': str(best_match['id']),
                'name': best_match['name'],
                'genre': 'Music',
                'image': best_match.get('picture_xl', best_match.get('picture_medium', '')),
                'link': best_match['link']
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

    def get_discography(self, artist_id, target_artist_id=None):
        """
        LÓGICA AUTOGRATHUS (RESTAURADA):
        Usa verificação dupla e 'startswith' para garantir a posse do álbum.
        """
        albums = []
        next_url = f"/artist/{artist_id}/albums?limit=100"
        
        # Normaliza o nome do alvo (ex: "bruno mars") para comparação segura
        target_name_norm = target_artist_id.lower().strip() if target_artist_id else ""
        
        while next_url:
            if self.BASE_URL in next_url: endpoint = next_url.replace(self.BASE_URL, "")
            else: endpoint = next_url

            data = self._get(endpoint)
            
            for item in data.get('data', []):
                
                # --- LÓGICA DO AUTOGRATHUS ---
                
                # 1. Tenta pegar o nome direto da lista
                artist_obj = item.get('artist', {})
                album_artist_name_raw = artist_obj.get('name')
                
                real_owner_norm = ""

                # Cenário 1: A lista já diz quem é o dono (Rápido)
                if album_artist_name_raw:
                    real_owner_norm = album_artist_name_raw.lower().strip()
                
                # Cenário 2: A lista veio vazia -> Chama API Extra (Preciso)
                # O Autograthus fazia isso para garantir que não era erro de API
                else:
                    try:
                        # Busca detalhes do álbum individualmente
                        details = self._get(f"/album/{item['id']}")
                        if 'artist' in details and 'name' in details['artist']:
                            real_owner_norm = details['artist']['name'].lower().strip()
                    except:
                        continue # Se falhar, ignora por segurança

                # --- DECISÃO FINAL (A REGRA DE OURO) ---
                is_official = False
                
                # O dono TEM que começar com o nome do artista alvo
                # Ex: "Bruno Mars & Cardi B" começa com "Bruno Mars"? SIM -> Passa
                # Ex: "ROSÉ" começa com "Bruno Mars"? NÃO -> Bloqueia
                if real_owner_norm.startswith(target_name_norm):
                    is_official = True
                
                # Rejeita "Various Artists" (Segurança Extra)
                if "various artists" in real_owner_norm or "vários artistas" in real_owner_norm:
                    is_official = False

                if not is_official:
                    # Pula para o próximo loop se não for oficial
                    continue

                # --- MONTAGEM DO ÁLBUM ---
                title = item['title']
                rec_type = item.get('record_type', 'album').lower()
                
                if rec_type == 'single' and 'single' not in title.lower(): title = f"{title} - Single"
                elif rec_type == 'ep' and 'ep' not in title.lower(): title = f"{title} - EP"

                albums.append({
                    'deezer_id': str(item['id']),
                    'title': title,
                    'artist': target_artist_id, # Mantém consistência
                    'year': item.get('release_date', '0000')[:4],
                    'track_count': item.get('nb_tracks', 0),
                    'type': rec_type,
                    'cover': item.get('cover_xl', item.get('cover_medium', ''))
                })
            
            next_url = data.get('next')
            if not next_url: break
            
        return albums
    # Adicione este método dentro da classe DeezerDataClient
    def get_related_artists(self, artist_id):
        """Busca artistas similares (Fans also like)"""
        try:
            url = f"{self.BASE_URL}/artist/{artist_id}/related?limit=20"
            res = requests.get(url, timeout=10).json()
            return res.get('data', [])
        except: 
            return []

    def get_album_tracks(self, album_id, fallback_title=None, fallback_artist=None):
        """
        LÓGICA MOVE FEAT (Mantida como você pediu):
        Organiza as faixas para ficarem na pasta correta.
        """
        tracks = []
        next_url = f"/album/{album_id}/tracks?limit=100"
        
        album_info = self._get(f"/album/{album_id}")
        if not album_info or 'error' in album_info: return []

        main_artist = fallback_artist if fallback_artist else album_info.get('artist', {}).get('name', 'Unknown')
        
        album_cover = album_info.get('cover_xl', '')
        album_genre = 'Music'
        if album_info.get('genres', {}).get('data'): album_genre = album_info['genres']['data'][0]['name']

        while next_url:
            if self.BASE_URL in next_url: endpoint = next_url.replace(self.BASE_URL, "")
            else: endpoint = next_url
            
            data = self._get(endpoint)
            for item in data.get('data', []):
                track_title = item['title']
                track_artist = item.get('artist', {}).get('name', main_artist)
                
                # Se o artista da faixa não for o dono (ex: feat)
                if track_artist != main_artist:
                    if main_artist in track_artist:
                        # Remove o dono, sobra o convidado
                        feat = track_artist.replace(main_artist, "")
                        feat = re.sub(r"^[\s&,]+", "", feat).strip()
                        feat = re.sub(r"[\s&,]+$", "", feat).strip()

                        if feat:
                            if "feat" not in track_title.lower() and "ft." not in track_title.lower():
                                track_title = f"{track_title} (feat. {feat})"
                
                final_artist = main_artist 

                tracks.append({
                    'title': track_title,
                    'artist': final_artist,
                    'album_artist': final_artist,
                    'album': album_info.get('title'),
                    'track_num': item.get('track_position', 0),
                    'track_count': album_info.get('nb_tracks'),
                    'disc_num': item.get('disk_number', 1),
                    'disc_count': 1,
                    'year': album_info.get('release_date', '0000')[:4],
                    'genre': album_genre,
                    'cover_url': album_cover
                })
            next_url = data.get('next')
            if not next_url: break
        return tracks