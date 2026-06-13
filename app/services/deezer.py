from typing import Optional

import httpx

_TIMEOUT = 15.0


def _artist_dict(raw: dict) -> dict:
    return {
        "deezer_id": raw["id"],
        "name": raw.get("name", ""),
        "picture_url": raw.get("picture_xl") or raw.get("picture_big") or raw.get("picture"),
        "followers": raw.get("nb_fan"),
        "nb_album": raw.get("nb_album"),
    }


def _album_dict(raw: dict) -> dict:
    return {
        "deezer_id": raw["id"],
        "title": raw.get("title", ""),
        "release_date": raw.get("release_date"),
        "cover_url": raw.get("cover_xl") or raw.get("cover_big") or raw.get("cover"),
        "album_type": raw.get("record_type"),
        "nb_tracks": raw.get("nb_tracks"),
    }


class DeezerClient:
    BASE_URL = "https://api.deezer.com"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=_TIMEOUT, base_url=self.BASE_URL)

    async def search_artist(self, query: str, limit: int = 10) -> list[dict]:
        async with self._client() as client:
            resp = await client.get("/search/artist", params={"q": query, "limit": limit})
            resp.raise_for_status()
            return [_artist_dict(a) for a in resp.json().get("data", [])]

    async def get_artist(self, deezer_id: int) -> dict:
        async with self._client() as client:
            resp = await client.get(f"/artist/{deezer_id}")
            resp.raise_for_status()
            return _artist_dict(resp.json())

    async def get_artist_albums(self, deezer_id: int) -> list[dict]:
        albums: list[dict] = []
        url = f"/artist/{deezer_id}/albums"
        params: dict = {"limit": 200, "index": 0}

        async with self._client() as client:
            while True:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                body = resp.json()
                page = body.get("data", [])
                albums.extend(_album_dict(a) for a in page)

                next_url = body.get("next")
                if not next_url or len(page) == 0:
                    break
                params["index"] = params["index"] + len(page)

        return albums

    async def get_album(self, deezer_id: int) -> dict:
        async with self._client() as client:
            resp = await client.get(f"/album/{deezer_id}")
            resp.raise_for_status()
            raw = resp.json()
            result = _album_dict(raw)
            result["tracks"] = [
                {
                    "deezer_id": t["id"],
                    "title": t.get("title", ""),
                    "track_number": t.get("track_position"),
                    "disc_number": t.get("disk_number"),
                    "duration": t.get("duration"),
                }
                for t in raw.get("tracks", {}).get("data", [])
            ]
            result["artist"] = _artist_dict(raw["artist"]) if raw.get("artist") else None
            return result

    async def get_related_artists(self, deezer_id: int, limit: int = 20) -> list[dict]:
        async with self._client() as client:
            resp = await client.get(f"/artist/{deezer_id}/related", params={"limit": limit})
            resp.raise_for_status()
            return [_artist_dict(a) for a in resp.json().get("data", [])]
