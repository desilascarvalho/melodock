import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download_job import DownloadJob
from app.schemas.download_job import DownloadJobCreate, DownloadJobResponse, PaginatedJobs

router = APIRouter(prefix="/downloads", tags=["downloads"])
log = logging.getLogger(__name__)


def _enrich(job: DownloadJob, artist_name: str | None, album_title: str | None) -> DownloadJobResponse:
    r = DownloadJobResponse.model_validate(job)
    r.artist_name = artist_name
    r.album_title = album_title
    return r


async def _enrich_many(db: AsyncSession, jobs: list[DownloadJob]) -> list[DownloadJobResponse]:
    artist_ids = {j.artist_id for j in jobs if j.artist_id}
    album_ids = {j.album_id for j in jobs if j.album_id}

    artists: dict[int, str] = {}
    if artist_ids:
        rows = await db.execute(select(Artist.id, Artist.name).where(Artist.id.in_(artist_ids)))
        artists = {r[0]: r[1] for r in rows.all()}

    albums: dict[int, str] = {}
    if album_ids:
        rows = await db.execute(select(Album.id, Album.title).where(Album.id.in_(album_ids)))
        albums = {r[0]: r[1] for r in rows.all()}

    return [
        _enrich(j, artists.get(j.artist_id), albums.get(j.album_id))
        for j in jobs
    ]


@router.get("", response_model=PaginatedJobs)
async def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(DownloadJob)
    if status:
        q = q.where(DownloadJob.status == status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()

    running_count = (
        await db.execute(
            select(func.count(DownloadJob.id)).where(DownloadJob.status == "running")
        )
    ).scalar_one()
    queued_count = (
        await db.execute(
            select(func.count(DownloadJob.id)).where(DownloadJob.status == "queued")
        )
    ).scalar_one()

    priority = case(
        (DownloadJob.status == "running", 0),
        (DownloadJob.status == "queued", 1),
        else_=2,
    )
    offset = (page - 1) * limit
    result = await db.execute(
        q.order_by(priority, DownloadJob.created_at).offset(offset).limit(limit)
    )
    items = result.scalars().all()
    enriched = await _enrich_many(db, list(items))

    return PaginatedJobs(
        items=enriched,
        total=total,
        running_count=running_count,
        queued_count=queued_count,
    )


@router.get("/active", response_model=DownloadJobResponse | None)
async def active_job(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DownloadJob).where(DownloadJob.status == "running").limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None
    enriched = await _enrich_many(db, [job])
    return enriched[0]


@router.post("/queue", response_model=DownloadJobResponse, status_code=201)
async def queue_job(body: DownloadJobCreate, db: AsyncSession = Depends(get_db)):
    job = DownloadJob(
        deezer_id=body.deezer_id,
        job_type=body.job_type,
        quality=body.quality or settings.DOWNLOAD_QUALITY,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    type_label = {"track": "faixa", "album": "álbum", "discography": "discografia"}.get(body.job_type, body.job_type)
    log.info("➕ Job adicionado à fila: %s deezer_id=%d (qualidade: %s)", type_label, body.deezer_id, job.quality)
    return DownloadJobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=204)
async def cancel_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(DownloadJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status == "running":
        raise HTTPException(409, "Cannot cancel a running job")
    if job.status != "queued":
        raise HTTPException(409, f"Job is already '{job.status}'")
    log.info("🗑️ Job cancelado: id=%d deezer_id=%d (%s)", job_id, job.deezer_id, job.job_type)
    await db.delete(job)
    await db.commit()


@router.post("/clear-completed", status_code=204)
async def clear_completed(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadJob).where(DownloadJob.status == "done"))
    jobs = result.scalars().all()
    for job in jobs:
        await db.delete(job)
    await db.commit()
    if jobs:
        log.info("🧹 %d job(s) concluído(s) removido(s) do histórico", len(jobs))


