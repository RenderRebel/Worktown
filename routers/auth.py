from fastapi import APIRouter, Depends, HTTPException
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.worker import WorkerCreate
from models.provider import ProviderCreate
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Register as Worker ──────────────────────────────────────────
# Flutter calls this after Firebase sign-in, when user picks "Worker"
@router.post("/register/worker")
async def register_worker(data: WorkerCreate, uid: str = Depends(verify_token)):

    # Check if this UID already registered
    existing = db.collection("workers").document(uid).get()
    if existing.exists:
        raise HTTPException(status_code=400, detail="Worker already registered")

    # Save to Firestore under workers/{uid}
    db.collection("workers").document(uid).set({
        "uid": uid,
        "name": data.name,
        "phone": data.phone,
        "pin_code": data.pin_code,
        "skills": data.skills,
        "bio": data.bio,
        "rating": 0.0,
        "total_jobs_done": 0,
        "is_available": True,
        "created_at": SERVER_TIMESTAMP
    })
    return {"message": "Worker registered successfully", "uid": uid}


# ── Register as Provider ─────────────────────────────────────────
# Flutter calls this when user picks "Provider"
@router.post("/register/provider")
async def register_provider(data: ProviderCreate, uid: str = Depends(verify_token)):

    existing = db.collection("providers").document(uid).get()
    if existing.exists:
        raise HTTPException(status_code=400, detail="Provider already registered")

    db.collection("providers").document(uid).set({
        "uid": uid,
        "name": data.name,
        "phone": data.phone,
        "pin_code": data.pin_code,
        "address": data.address,
        "rating": 0.0,
        "total_jobs_posted": 0,
        "created_at": SERVER_TIMESTAMP
    })
    return {"message": "Provider registered successfully", "uid": uid}


# ── Get My Profile ───────────────────────────────────────────────
@router.get("/me")
async def get_my_profile(uid: str = Depends(verify_token)):

    # Check workers first, then providers
    worker = db.collection("workers").document(uid).get()
    if worker.exists:
        return {"role": "worker", "profile": worker.to_dict()}

    provider = db.collection("providers").document(uid).get()
    if provider.exists:
        return {"role": "provider", "profile": provider.to_dict()}

    raise HTTPException(status_code=404, detail="Profile not found")
