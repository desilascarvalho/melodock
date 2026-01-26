import requests

class DeezerClient:
    def get_recommendations(self, artist_name):
        """Busca artistas similares usando a API pública do Deezer."""
        try:

            search_url = f"https://api.deezer.com/search/artist?q={artist_name}&limit=1"
            res = requests.get(search_url, timeout=10).json()
            
            if not res.get('data'):
                return []
            
            artist_id = res['data'][0]['id']
            
            related_url = f"https://api.deezer.com/artist/{artist_id}/related&limit=12"
            res_related = requests.get(related_url, timeout=10).json()
            
            results = []
            for item in res_related.get('data', []):
                results.append({
                    'name': item['name'],

                    'image': item.get('picture_medium', ''), 
                    'nb_fan': item.get('nb_fan', 0)
                })
            
            return results

        except Exception as e:
            print(f"Erro Deezer: {e}")
            return []