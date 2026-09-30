from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.config import ROOT
from app.core.database import initialize

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title='Lingua API', version='1.0.0', lifespan=lifespan)
app.include_router(router)
app.mount('/static', StaticFiles(directory=ROOT / 'web'), name='static')

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(ROOT / 'web/index.html')
