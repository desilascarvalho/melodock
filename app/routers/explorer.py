from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.artist import Artist
from app.schemas.artist import ArtistSearchResult
from app.services.deezer import DeezerClient

router = APIRouter(prefix="/explorer", tags=["explorer"])
_deezer = DeezerClient()


class RelatedResponse(BaseModel):
    artist: ArtistSearchResult | None = None
    related: list[ArtistSearchResult] = []


@router.get("/related/{artist_deezer_id}", response_model=RelatedResponse)
async def related_artists(artist_deezer_id: int, db: AsyncSession = Depends(get_db)):
    related_raw = await _deezer.get_related_artists(artist_deezer_id)

    deezer_ids = [r["deezer_id"] for r in related_raw] + [artist_deezer_id]
    db_map: dict[int, int] = {}
    if deezer_ids:
        rows = await db.execute(
            select(Artist.deezer_id, Artist.id).where(Artist.deezer_id.in_(deezer_ids))
        )
        db_map = {row[0]: row[1] for row in rows.all()}

    related = [
        ArtistSearchResult(**r, in_library=r["deezer_id"] in db_map, library_id=db_map.get(r["deezer_id"]))
        for r in related_raw
    ]

    center_row = await db.execute(select(Artist).where(Artist.deezer_id == artist_deezer_id))
    center_orm = center_row.scalar_one_or_none()
    center: ArtistSearchResult | None = None
    if center_orm:
        center = ArtistSearchResult(
            deezer_id=center_orm.deezer_id,
            name=center_orm.name,
            picture_url=center_orm.picture_url,
            followers=center_orm.followers,
            in_library=True,
            library_id=center_orm.id,
        )

    return RelatedResponse(artist=center, related=related)
