import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.routers import dataset, employees, hr, meta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Career Quest API",
    description="AI-навигатор развития сотрудника · HackAlem AI · Halyk Bank, кейс 1",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

for r in (meta.router, employees.router, hr.router, dataset.router):
    app.include_router(r)

# Production / docker: FastAPI also serves the built frontend, so one process = one command = one URL.
dist = settings.frontend_dist
if (dist / "index.html").exists():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (dist / path).resolve()
        if path and file.is_file() and dist.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(dist / "index.html")
