from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from firebase_config import db
from middleware.auth_middleware import verify_token, UserIdentity
from models.schemas import RatingCreate, ReviewResponse
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])
security = HTTPBearer()


# ── Helper: Bearer token se uid lo ───────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserIdentity:
    token = credentials.credentials
    user_identity = await verify_token(token)
    return user_identity


# ── Guard: requires verified email, raises 403 if not ────────────
def require_verified_email(uid: UserIdentity = Depends(get_current_user)) -> UserIdentity:
    if not uid.email_verified:
        raise HTTPException(status_code=403, detail="Email verification required")
    return uid


# ── Helper: users collection se user data lo ─────────────────────
def get_user_or_404(uid: str) -> dict:
    user = db.collection("users").document(uid).get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


# ── Helper: Recompute and update average rating ───────────────────
def _recalculate_rating(collection: str, target_uid: str) -> float:
    """
    Reads all reviews for a user from the `reviews` collection,
    computes the new average, and updates the respective
    workers/ or providers/ document.
    Returns the new average rating.
    """
    reviews = (
        db.collection("reviews")
          .where("target_uid", "==", target_uid)
          .stream()
    )
    ratings = [r.to_dict().get("rating", 0) for r in reviews]
    if not ratings:
        return 0.0
    avg = round(sum(ratings) / len(ratings), 2)
    db.collection(collection).document(target_uid).update({"rating": avg})
    return avg


# ════════════════════════════════════════════════════════════════════
# POST /reviews/rate  –  Submit a rating + optional comment
# ════════════════════════════════════════════════════════════════════
@router.post("/rate")
async def submit_rating(data: RatingCreate, uid: UserIdentity = Depends(require_verified_email)):
    """
    Rate and optionally comment on the other party after a job is completed.

    - Provider → rates Worker
    - Worker   → rates Provider

    Rules:
      1. The job (application) must be in `completed` status.
      2. The caller must be a participant in that application.
      3. Each user can only submit ONE review per application.
    """

    # ── 1. Load the application ───────────────────────────────────
    app_ref  = db.collection("applications").document(data.app_id)
    app_snap = app_ref.get()
    if not app_snap.exists:
        raise HTTPException(status_code=404, detail="Application not found")
    app_data = app_snap.to_dict()

    # ── 2. Job must be completed ──────────────────────────────────
    job_snap = db.collection("jobs").document(app_data["job_id"]).get()
    if not job_snap.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    job_data = job_snap.to_dict()

    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Ratings can only be submitted after the job is completed"
        )

    # ── 3. Caller must be a participant ───────────────────────────
    caller_data   = get_user_or_404(uid)
    caller_role   = caller_data.get("role")

    worker_uid   = app_data.get("applicant_uid")
    provider_uid = job_data.get("posted_by_uid")

    if uid not in [worker_uid, provider_uid]:
        raise HTTPException(status_code=403, detail="You are not a participant in this job")

    # ── 4. Determine who is being rated ──────────────────────────
    if caller_role == "provider":
        if uid != provider_uid:
            raise HTTPException(status_code=403, detail="Not your job")
        target_uid        = worker_uid
        target_collection = "workers"
        reviewer_role     = "provider"
    elif caller_role == "worker":
        if uid != worker_uid:
            raise HTTPException(status_code=403, detail="Not your application")
        target_uid        = provider_uid
        target_collection = "providers"
        reviewer_role     = "worker"
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # ── 5. Prevent duplicate review per application ───────────────
    existing = (
        db.collection("reviews")
          .where("app_id",       "==", data.app_id)
          .where("reviewer_uid", "==", uid)
          .stream()
    )
    if any(True for _ in existing):
        raise HTTPException(
            status_code=409,
            detail="You have already submitted a review for this job"
        )

    # ── 6. Save the review ────────────────────────────────────────
    review_id = str(uuid.uuid4())
    db.collection("reviews").document(review_id).set({
        "review_id":     review_id,
        "app_id":        data.app_id,
        "job_id":        app_data["job_id"],
        "reviewer_uid":  uid,
        "reviewer_role": reviewer_role,
        "target_uid":    target_uid,
        "rating":        data.rating,
        "comment":       data.comment,
        "created_at":    SERVER_TIMESTAMP,
    })

    # ── 7. Update the flag on the application ────────────────────
    flag_field = (
        "provider_rated_worker"
        if caller_role == "provider"
        else "worker_rated_provider"
    )
    app_ref.update({flag_field: True})

    # ── 8. Recalculate and persist average rating ─────────────────
    new_avg = _recalculate_rating(target_collection, target_uid)

    return {
        "message":    "Rating submitted successfully ⭐",
        "review_id":  review_id,
        "new_avg_rating": new_avg,
    }


# ════════════════════════════════════════════════════════════════════
# GET /reviews/worker/{worker_uid}  –  All reviews for a worker
# ════════════════════════════════════════════════════════════════════
@router.get("/worker/{worker_uid}")
async def get_worker_reviews(worker_uid: str):
    """Fetch all reviews received by a specific worker."""
    reviews = (
        db.collection("reviews")
          .where("target_uid", "==", worker_uid)
          .stream()
    )
    result = []
    for r in reviews:
        d = r.to_dict()
        # Attach reviewer name for display
        reviewer_snap = db.collection("users").document(d.get("reviewer_uid", "")).get()
        d["reviewer_name"] = reviewer_snap.to_dict().get("name", "Unknown") if reviewer_snap.exists else "Unknown"
        result.append(d)

    return {"reviews": result, "total": len(result)}


# ════════════════════════════════════════════════════════════════════
# GET /reviews/provider/{provider_uid}  –  All reviews for a provider
# ════════════════════════════════════════════════════════════════════
@router.get("/provider/{provider_uid}")
async def get_provider_reviews(provider_uid: str):
    """Fetch all reviews received by a specific provider."""
    reviews = (
        db.collection("reviews")
          .where("target_uid", "==", provider_uid)
          .stream()
    )
    result = []
    for r in reviews:
        d = r.to_dict()
        reviewer_snap = db.collection("users").document(d.get("reviewer_uid", "")).get()
        d["reviewer_name"] = reviewer_snap.to_dict().get("name", "Unknown") if reviewer_snap.exists else "Unknown"
        result.append(d)

    return {"reviews": result, "total": len(result)}


# ════════════════════════════════════════════════════════════════════
# GET /reviews/stats/worker/{worker_uid}  –  Jobs done count
# ════════════════════════════════════════════════════════════════════
@router.get("/stats/worker/{worker_uid}")
async def get_worker_stats(worker_uid: str):
    """
    Returns the number of jobs completed by a worker and their average rating.
    'Jobs done' = applications with status == 'accepted' AND job status == 'completed'.
    """
    # Count from the applications collection (most accurate source)
    completed_apps = (
        db.collection("applications")
          .where("applicant_uid", "==", worker_uid)
          .stream()
    )

    total_jobs_done = 0
    for app in completed_apps:
        app_data = app.to_dict()
        if app_data.get("status") == "accepted":
            job_snap = db.collection("jobs").document(app_data.get("job_id", "")).get()
            if job_snap.exists and job_snap.to_dict().get("status") == "completed":
                total_jobs_done += 1

    # Also sync to workers collection
    db.collection("workers").document(worker_uid).update(
        {"total_jobs_done": total_jobs_done}
    )

    # Get rating from workers collection
    worker_snap = db.collection("workers").document(worker_uid).get()
    rating = worker_snap.to_dict().get("rating", 0.0) if worker_snap.exists else 0.0

    return {
        "worker_uid":     worker_uid,
        "total_jobs_done": total_jobs_done,
        "average_rating": rating,
    }


# ════════════════════════════════════════════════════════════════════
# GET /reviews/stats/provider/{provider_uid}  –  Jobs posted count
# ════════════════════════════════════════════════════════════════════
@router.get("/stats/provider/{provider_uid}")
async def get_provider_stats(provider_uid: str):
    """
    Returns the number of jobs posted by a provider and their average rating.
    """
    jobs = (
        db.collection("jobs")
          .where("posted_by_uid", "==", provider_uid)
          .stream()
    )

    job_list = [j.to_dict() for j in jobs]
    total_jobs_posted    = len(job_list)
    total_jobs_completed = sum(1 for j in job_list if j.get("status") == "completed")

    # Sync to providers collection
    db.collection("providers").document(provider_uid).update(
        {"total_jobs_posted": total_jobs_posted}
    )

    # Get rating
    provider_snap = db.collection("providers").document(provider_uid).get()
    rating = provider_snap.to_dict().get("rating", 0.0) if provider_snap.exists else 0.0

    return {
        "provider_uid":       provider_uid,
        "total_jobs_posted":  total_jobs_posted,
        "total_jobs_completed": total_jobs_completed,
        "average_rating":     rating,
    }


# ════════════════════════════════════════════════════════════════════
# GET /reviews/my-reviews  –  My received reviews
# ════════════════════════════════════════════════════════════════════
@router.get("/my-reviews")
async def get_my_reviews(uid: str = Depends(get_current_user)):
    """Fetch all reviews that I (the logged-in user) have received."""
    reviews = (
        db.collection("reviews")
          .where("target_uid", "==", uid)
          .stream()
    )
    result = []
    for r in reviews:
        d = r.to_dict()
        reviewer_snap = db.collection("users").document(d.get("reviewer_uid", "")).get()
        d["reviewer_name"] = reviewer_snap.to_dict().get("name", "Unknown") if reviewer_snap.exists else "Unknown"
        result.append(d)

    return {"reviews": result, "total": len(result)}
