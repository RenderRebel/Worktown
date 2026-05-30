from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.schemas import JobCreate
from services.job_service import get_jobs, get_job, update_job, delete_job
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

router = APIRouter(prefix="/jobs", tags=["Jobs"])
security = HTTPBearer()


# ── Helper: Bearer token se uid lo ───────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    uid = await verify_token(token)
    return uid


# ── Helper: users collection se user data lo ─────────────────────
def get_user_or_404(uid: str) -> dict:
    user = db.collection("users").document(uid).get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


# ── Post a Job (Provider only) ───────────────────────────────────
@router.post("/")
async def post_job(data: JobCreate, uid: str = Depends(get_current_user)):
    """Create a new job listing. Only providers can post jobs."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can post jobs")

    job_id = str(uuid.uuid4())
    db.collection("jobs").document(job_id).set({
        "job_id":                job_id,
        "posted_by_uid":         uid,
        "provider_phone":        user_data["phone"],
        "title":                 data.title,
        "description":           data.description,
        "category":              data.category,
        "pin_code":              data.pin_code,
        "pay":                   data.pay,
        "job_type":              data.job_type,
        "part_time_type":        data.part_time_type,
        "hours":                 data.hours,
        "pay_basis":             data.pay_basis,
        "status":                "open",
        "assigned_worker_uid":   None,
        "assigned_worker_phone": None,
        "created_at":            SERVER_TIMESTAMP,
    })
    return {"message": "Job posted", "job_id": job_id}


# ── Get All Jobs (with optional filters) ─────────────────────────
@router.get("/")
async def get_jobs_route(

):
    """Fetch all jobs, optionally filtered by pincode, category, and/or status."""
    return get_jobs()


# ── Get Jobs by Pin Code (Worker view) ───────────────────────────
@router.get("/pin/{pin_code}")
async def get_jobs_by_pin(pin_code: str, uid: str = Depends(get_current_user)):
    """Workers browse open jobs in their area by pin code."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Only workers can browse jobs")

    jobs = (
        db.collection("jobs")
          .where("pin_code", "==", pin_code)
          .where("status",   "==", "open")
          .stream()
    )
    return {"jobs": [j.to_dict() for j in jobs]}


# ── Get My Posted Jobs (Provider view) ───────────────────────────
@router.get("/my-posted")
async def get_my_posted_jobs(uid: str = Depends(get_current_user)):
    """Returns all jobs posted by the currently authenticated provider."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can view posted jobs")

    jobs = (
        db.collection("jobs")
          .where("posted_by_uid", "==", uid)
          .stream()
    )
    return {"jobs": [j.to_dict() for j in jobs]}


# ── Get Single Job ────────────────────────────────────────────────
@router.get("/{job_id}")
async def get_job_route(job_id: str, uid: str = Depends(get_current_user)):
    """Get a single job by ID (requires auth)."""
    return get_job(job_id)


# ── Update a Job ──────────────────────────────────────────────────
@router.put("/{job_id}")
async def update_job_route(job_id: str, job_data: JobCreate, uid: str = Depends(get_current_user)):
    """Update an existing job by ID. Only the original poster can update."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can update jobs")

    job_data.posted_by = uid
    return update_job(job_id, job_data)


# ── Delete a Job ──────────────────────────────────────────────────
@router.delete("/{job_id}")
async def delete_job_route(job_id: str, uid: str = Depends(get_current_user)):
    """Delete a job by ID. Only the original poster can delete."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can delete jobs")

    return delete_job(job_id)# from fastapi import APIRouter, Depends, HTTPException, Query
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from typing import List, Optional
# from firebase_config import db
# from middleware.auth_middleware import verify_token
# from models.job import JobCreate
# from models.schemas import job
# from services.job_service import get_jobs, get_job, update_job, delete_job
# from google.cloud.firestore_v1 import SERVER_TIMESTAMP
# import uuid

# router = APIRouter(prefix="/jobs", tags=["Jobs"])

# security = HTTPBearer()


# # ── Helper: Bearer token se uid lo ───────────────────────────────
# async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     token = credentials.credentials
#     uid = await verify_token(token)
#     return uid


# # ── Post a Job (Provider only) ───────────────────────────────────
# @router.post("/")
# async def post_job(data: JobCreate, uid: str = Depends(get_current_user)):
#     """Create a new job listing. Only providers can post jobs."""

#     provider = db.collection("providers").document(uid).get()
#     if not provider.exists:
#         raise HTTPException(status_code=403, detail="Only providers can post jobs")

#     provider_data = provider.to_dict()
#     job_id = str(uuid.uuid4())

#     db.collection("jobs").document(job_id).set({
#         "job_id":                job_id,
#         "posted_by_uid":         uid,
#         "provider_phone":        provider_data["phone"],
#         "title":                 data.title,
#         "description":           data.description,
#         "category":              data.category,
#         "pin_code":              data.pin_code,
#         "pay":                   data.pay,
#         "status":                "open",
#         "assigned_worker_uid":   None,
#         "assigned_worker_phone": None,
#         "created_at":            SERVER_TIMESTAMP,
#     })
#     return {"message": "Job posted", "job_id": job_id}


# # ── Get All Jobs (with optional filters) ─────────────────────────
# @router.get("/")
# async def get_jobs_route(
#     pincode:  Optional[str] = Query(None, description="Filter jobs by pincode"),
#     category: Optional[str] = Query(None, description="Filter jobs by category"),
#     status:   Optional[str] = Query(None, description="Filter jobs by status"),
# ):
#     """Fetch all jobs, optionally filtered by pincode, category, and/or status."""
#     return get_jobs(pincode=pincode, category=category, status=status)


# # ── Get Jobs by Pin Code (Worker view) ───────────────────────────
# @router.get("/pin/{pin_code}")
# async def get_jobs_by_pin(pin_code: str, uid: str = Depends(get_current_user)):
#     """Workers browse open jobs in their area by pin code."""

#     jobs = (
#         db.collection("jobs")
#           .where("pin_code", "==", pin_code)
#           .where("status",   "==", "open")
#           .stream()
#     )
#     return {"jobs": [j.to_dict() for j in jobs]}


# # ── Get My Posted Jobs (Provider view) ───────────────────────────
# @router.get("/my-posted")
# async def get_my_posted_jobs(uid: str = Depends(get_current_user)):
#     """Returns all jobs posted by the currently authenticated provider."""

#     jobs = (
#         db.collection("jobs")
#           .where("posted_by_uid", "==", uid)
#           .stream()
#     )
#     return {"jobs": [j.to_dict() for j in jobs]}


# # ── Get Single Job ────────────────────────────────────────────────
# @router.get("/{job_id}")
# async def get_job_route(job_id: str, uid: str = Depends(get_current_user)):
#     """Get a single job by ID (requires auth)."""
#     return get_job(job_id)


# # ── Update a Job ──────────────────────────────────────────────────
# @router.put("/{job_id}")
# async def update_job_route(job_id: str, job_data: JobCreate, uid: str = Depends(get_current_user)):
#     """Update an existing job by ID."""
#     job_data.posted_by = uid
#     return update_job(job_id, job_data)


# # ── Delete a Job ──────────────────────────────────────────────────
# @router.delete("/{job_id}")
# async def delete_job_route(job_id: str, uid: str = Depends(get_current_user)):
#     """Delete a job by ID (requires auth)."""
#     return delete_job(job_id)