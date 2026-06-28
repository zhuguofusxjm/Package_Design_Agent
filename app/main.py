from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.chat import router as chat_router
from app.api.cases import router as cases_router
from app.config import settings
import os

app = FastAPI(title="Operator Package Design Assistant")
app.include_router(chat_router)
app.include_router(cases_router)

# Static dir is mounted only if it exists (frontend task creates it later).
if os.path.isdir(settings.static_dir):
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

@app.get("/")
def root():
    index = os.path.join(settings.static_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "ok", "note": "frontend not yet built; POST /api/chat to use API"}
