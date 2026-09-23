from fastapi import APIRouter, Depends, File, UploadFile

from app.models.api import UploadResult
from app.security import require_hr
from app.state import store

router = APIRouter(prefix="/api/dataset", tags=["dataset"], dependencies=[Depends(require_hr)])


@router.post("/upload", response_model=UploadResult)
async def upload(files: list[UploadFile] = File(...)):
    """Dataset-format files: employees.json, activity_history.csv, events.json, skills.json (any subset)."""
    payload = [(f.filename or "upload.json", await f.read()) for f in files]
    return store.ingest_files(payload)


@router.post("/reset")
def reset():
    store.reset()
    return {"status": "reset", "employees": len(store.employees), "history": len(store.history)}
