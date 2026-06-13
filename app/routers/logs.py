from fastapi import APIRouter
from pydantic import BaseModel

from app.services.log_buffer import log_buffer

router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    level: str
    msg: str
    ts: str


class LogsResponse(BaseModel):
    lines: list[LogEntry]


@router.get("", response_model=LogsResponse)
async def get_logs():
    return LogsResponse(lines=list(log_buffer.entries))
