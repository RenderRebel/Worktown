from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.database import initialize_firebase
from fastapi.security import HTTPBearer
from api.routes import users, jobs, favorites, applications  # sirf yeh rakho



@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_firebase()
    yield
security = HTTPBearer()

app = FastAPI()

# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"server_status": "running", "message": "Service Marketplace API is live!"}

@app.get("/healthz")
def health():
    return {"ok": True}

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(favorites.router)
app.include_router(applications.router)

# ── Include New NearHelp Routers ──────────────────────────────────────────────

