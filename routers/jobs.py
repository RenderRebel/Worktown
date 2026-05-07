from fastapi import APIRouter, Depends, HTTPException
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.job import JobCreate
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

router = APIRouter(prefix="/jobs-v2", tags=["Jobs V2"])

# ── Post a Job (Provider only) ───────────────────────────────────
@router.post("/")
async def post_job(data: JobCreate, uid: str = Depends(verify_token)):

    # Only providers can post jobs
    provider = db.collection("providers").document(uid).get()
    if not provider.exists:
        raise HTTPException(status_code=403, detail="Only providers can post jobs")

    provider_data = provider.to_dict()
    job_id = str(uuid.uuid4())   # generates a unique ID like "abc-123-xyz"

    db.collection("jobs").document(job_id).set({
        "job_id": job_id,
        "posted_by_uid": uid,
        "provider_phone": provider_data["phone"],
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "pin_code": data.pin_code,
        "pay": data.pay,
        "status": "open",
        "assigned_worker_uid": None,
        "assigned_worker_phone": None,
        "created_at": SERVER_TIMESTAMP
    })
    return {"message": "Job posted", "job_id": job_id}


# ── Get Jobs by Pin Code (Worker sees these) ─────────────────────
@router.get("/pin/{pin_code}")
async def get_jobs_by_pin(pin_code: str, uid: str = Depends(verify_token)):

    jobs = db.collection("jobs")\
             .where("pin_code", "==", pin_code)\
             .where("status", "==", "open")\
             .stream()

    return {"jobs": [job.to_dict() for job in jobs]}


# ── Get My Posted Jobs (Provider sees these) ─────────────────────
@router.get("/my-posted")
async def get_my_posted_jobs(uid: str = Depends(verify_token)):

    jobs = db.collection("jobs")\
             .where("posted_by_uid", "==", uid)\
             .stream()

    return {"jobs": [job.to_dict() for job in jobs]}
