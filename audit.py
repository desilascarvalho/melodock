"""
Standalone audit script — checks every Track in the database and marks
file_exists=False for records whose local_path no longer exists on disk.

Usage:
    python audit.py

Expects the same /config/melodock.db that the FastAPI app uses.
"""

import asyncio
import sys
from pathlib import Path

# ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal, async_engine, Base
from app.models.track import Track  # noqa: F401 — registers model


async def run_audit() -> dict:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    checked = 0
    missing = 0
    ok = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Track))
        tracks = result.scalars().all()

        for track in tracks:
            checked += 1
            if not track.local_path:
                if track.file_exists:
                    track.file_exists = False
                    missing += 1
                continue

            exists = Path(track.local_path).is_file()
            if exists:
                if not track.file_exists:
                    track.file_exists = True
                ok += 1
            else:
                if track.file_exists:
                    track.file_exists = False
                missing += 1

        await db.commit()

    return {"checked": checked, "missing": missing, "ok": ok}


if __name__ == "__main__":
    report = asyncio.run(run_audit())
    print(
        f"Audit complete — checked: {report['checked']}, "
        f"ok: {report['ok']}, missing: {report['missing']}"
    )
