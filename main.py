from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from core.database import initialize_firebase
from fastapi.security import HTTPBearer
from api.routes import users, jobs, applications, reviews  # sirf yeh rakho
import json
from utils.translation import translate_fields_recursively

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_firebase()
    yield
security = HTTPBearer()

app = FastAPI()

@app.middleware("http")
async def translation_middleware(request: Request, call_next):
    response = await call_next(request)
    lang = request.query_params.get("lang")
    if lang == "hi":
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = b""
            try:
                async for chunk in response.body_iterator:
                    body += chunk
                
                data = json.loads(body.decode("utf-8"))
                translated_data = translate_fields_recursively(data)
                new_body = json.dumps(translated_data).encode("utf-8")
                
                headers = dict(response.headers)
                headers["content-length"] = str(len(new_body))
                return Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/json"
                )
            except Exception as e:
                # If reading/decoding body failed and we already read it, re-serve the original body
                if body:
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type="application/json"
                    )
    return response

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
app.include_router(applications.router)
app.include_router(reviews.router)

# ── Include New NearHelp Routers ──────────────────────────────────────────────

