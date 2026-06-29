from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from firebase_config import db
from middleware.auth_middleware import verify_token, UserIdentity
from models.schemas import ApplicationCreate, Application
from services.application_service import get_applications, get_application, update_application, delete_application
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

router = APIRouter(prefix="/applications", tags=["Applications"])
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


# ── Submit Application (Worker only) ─────────────────────────────
@router.post("/")
async def apply_for_job(data: ApplicationCreate, uid: UserIdentity = Depends(require_verified_email)):
    """Submit a new job application. Only workers can apply."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Only workers can apply")

    job = db.collection("jobs").document(data.job_id).get()
    if not job.exists or job.to_dict()["status"] != "open":
        raise HTTPException(status_code=400, detail="Job not available")

    app_id = str(uuid.uuid4())
    db.collection("applications").document(app_id).set({
        "app_id":                     app_id,
        "job_id":                     data.job_id,
        "applicant_uid":              uid,
        "applicant_phone":            user_data["phone"],
        "status":                     "pending",
        "worker_arriving":            False,
        "provider_confirmed_arrival": False,
        "worker_completed":           False,
        "provider_confirmed_done":    False,
        "cancelled_by":               None,
        "cancel_reason":              None,
        "applied_at":                 SERVER_TIMESTAMP,
    })
    return {"message": "Application submitted", "app_id": app_id}


# ── Get All Applications (with optional filters) ──────────────────
@router.get("/")
async def get_applications_route(
    job_id:          Optional[str] = Query(None, description="Filter by job ID"),
    application_uid: Optional[str] = Query(None, description="Filter by applicant UID"),
    status:          Optional[str] = Query(None, description="Filter by status"),
    uid: str = Depends(get_current_user),
):
    """Fetch all applications, optionally filtered by job_id, applicant UID, or status."""
    return get_applications(job_id=job_id, application_uid=application_uid, status=status)


# ── Get Single Application ────────────────────────────────────────
@router.get("/{app_id}")
async def get_application_route(app_id: str, uid: str = Depends(get_current_user)):
    """Get a single application by its ID."""
    return get_application(app_id)


# ── Approve Application (Provider) ───────────────────────────────
@router.patch("/{app_id}/approve")
async def approve_application(app_id: str, uid: str = Depends(get_current_user)):
    """Provider approves a pending application and assigns the worker."""

    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can approve applications")

    app = db.collection("applications").document(app_id).get()
    if not app.exists:
        raise HTTPException(status_code=404, detail="Application not found")

    app_data = app.to_dict()
    job      = db.collection("jobs").document(app_data["job_id"]).get()
    job_data = job.to_dict()

    if job_data["posted_by_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your job")

    # Worker phone users collection se lo
    worker_data  = db.collection("users").document(app_data["applicant_uid"]).get().to_dict()
    worker_phone = worker_data["phone"]

    db.collection("applications").document(app_id).update({"status": "accepted"})
    db.collection("jobs").document(app_data["job_id"]).update({
        "status":                "assigned",
        "assigned_worker_uid":   app_data["applicant_uid"],
        "assigned_worker_phone": worker_phone,
    })

    return {
        "message":        "Application approved",
        "worker_phone":   worker_phone,
        "provider_phone": job_data["provider_phone"],
    }


# ── Worker: I Am Arriving ─────────────────────────────────────────
@router.patch("/{app_id}/worker-arriving")
async def worker_arriving(app_id: str, uid: str = Depends(get_current_user)):
    """Worker marks themselves as arriving. Job status → arriving."""

    # Sirf worker call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Only workers can mark arriving")

    # Sirf apni application pe
    app_ref  = db.collection("applications").document(app_id)
    app_data = app_ref.get().to_dict()
    if app_data["applicant_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your application")

    app_ref.update({"worker_arriving": True})
    db.collection("jobs").document(app_data["job_id"]).update({"status": "arriving"})
    return {"message": "Provider will be notified"}


# ── Provider: Confirm Worker Arrived ─────────────────────────────
@router.patch("/{app_id}/confirm-arrival")
async def confirm_arrival(app_id: str, uid: str = Depends(get_current_user)):
    """Provider confirms worker has arrived. Job status → in_progress."""

    # Sirf provider call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can confirm arrival")

    # Application fetch karo
    app_ref  = db.collection("applications").document(app_id)
    app_data = app_ref.get().to_dict()

    # Sirf us job ka provider confirm kar sake
    job_data = db.collection("jobs").document(app_data["job_id"]).get().to_dict()
    if job_data["posted_by_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your job")

    app_ref.update({"provider_confirmed_arrival": True})
    db.collection("jobs").document(app_data["job_id"]).update({"status": "in_progress"})
    return {"message": "Job is now in progress"}

# ── Provider: Worker Did NOT Arrive → Cancel & Reopen ────────────
@router.patch("/{app_id}/cancel-reopen")
async def cancel_and_reopen(app_id: str, uid: str = Depends(get_current_user)):
    """Provider cancels because worker didn't arrive. Job reopens."""

    # Sirf provider call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can cancel and reopen")

    app_ref  = db.collection("applications").document(app_id)
    app_data = app_ref.get().to_dict()

    # Sirf apni job ka provider cancel kar sake
    job_ref  = db.collection("jobs").document(app_data["job_id"])
    job_data = job_ref.get().to_dict()
    if job_data["posted_by_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your job")

    app_ref.update({
        "status":        "rejected",
        "cancelled_by":  "provider",
        "cancel_reason": "no_arrival",
    })
    job_ref.update({
        "status":                "open",
        "assigned_worker_uid":   None,
        "assigned_worker_phone": None,
    })
    return {"message": "Job reopened"}


# ── Worker: I Completed the Work ─────────────────────────────────
@router.patch("/{app_id}/worker-done")
async def worker_done(app_id: str, uid: str = Depends(get_current_user)):
    """Worker marks job as done. Job status → pending_confirm."""

    # Sirf worker call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Only workers can mark job as done")

    app_ref  = db.collection("applications").document(app_id)
    app_data = app_ref.get().to_dict()

    # Sirf apni application pe
    if app_data["applicant_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your application")

    app_ref.update({"worker_completed": True})
    db.collection("jobs").document(app_data["job_id"]).update({"status": "pending_confirm"})
    return {"message": "Waiting for provider to confirm"}


# ── Provider: Confirm Job Done ────────────────────────────────────
@router.patch("/{app_id}/confirm-done")
async def confirm_done(app_id: str, uid: str = Depends(get_current_user)):
    """Provider confirms job is fully completed. Job status → completed."""

    # Sirf provider call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers can confirm job done")

    app_ref  = db.collection("applications").document(app_id)
    app_data = app_ref.get().to_dict()

    # Sirf apni job ka provider confirm kar sake
    job_ref  = db.collection("jobs").document(app_data["job_id"])
    job_data = job_ref.get().to_dict()
    if job_data["posted_by_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your job")

    app_ref.update({"provider_confirmed_done": True})
    job_ref.update({"status": "completed"})

    # Initialize rating flags — both parties can now rate each other
    app_ref.update({
        "provider_rated_worker": False,
        "worker_rated_provider": False,
    })

    return {"message": "Job completed! Both can now rate each other ⭐"}


# ── Worker: Cancel Application ────────────────────────────────────
@router.patch("/{app_id}/cancel")
async def cancel_application(app_id: str, uid: str = Depends(get_current_user)):
    """Worker cancels their own application. Reopens job if already assigned."""

    # Sirf worker call kar sake
    user_data = get_user_or_404(uid)
    if user_data.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Only workers can cancel applications")

    app_ref = db.collection("applications").document(app_id)
    app     = app_ref.get()
    if not app.exists:
        raise HTTPException(status_code=404, detail="Application not found")

    app_data = app.to_dict()
    if app_data["applicant_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your application")

    if app_data.get("status") in ["completed", "cancelled", "rejected"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel with status: {app_data.get('status')}")

    app_ref.update({
        "status":        "cancelled",
        "cancelled_by":  "worker",
        "cancel_reason": "cancelled_by_worker",
    })

    job_ref = db.collection("jobs").document(app_data["job_id"])
    job     = job_ref.get()
    if job.exists and job.to_dict().get("assigned_worker_uid") == uid:
        job_ref.update({
            "status":                "open",
            "assigned_worker_uid":   None,
            "assigned_worker_phone": None,
        })
    return {"message": "Application cancelled successfully"}


# ── Generic Partial Update ────────────────────────────────────────
@router.patch("/{app_id}")
async def update_application_route(app_id: str, updates: dict, uid: str = Depends(get_current_user)):
    """Generic partial update for an application (admin/internal use)."""

    if updates.get("status") == "cancelled" and not updates.get("cancelled_by"):
        updates["cancelled_by"] = uid
    return update_application(app_id, updates)


# ── Delete Application ────────────────────────────────────────────
@router.delete("/{app_id}")
async def delete_application_route(app_id: str, uid: str = Depends(get_current_user)):
    """Delete an application by its ID."""
    return delete_application(app_id)

# from fastapi import APIRouter, Depends, HTTPException, Query
# from typing import List, Optional
# from firebase_config import db
# from middleware.auth_middleware import verify_token
# from models.schemas import ApplicationCreate, Application
# from services.application_service import get_applications, get_application, update_application, delete_application
# from google.cloud.firestore_v1 import SERVER_TIMESTAMP
# import uuid

# router = APIRouter(prefix="/applications", tags=["Applications"])


# # ── Submit Application (Worker only) ─────────────────────────────
# @router.post("/", response_model=Application)
# async def apply_for_job(data: ApplicationCreate, uid: str = Depends(verify_token)):
#     """Submit a new job application. Only workers can apply."""

#     worker = db.collection("workers").document(uid).get()
#     if not worker.exists:
#         raise HTTPException(status_code=403, detail="Only workers can apply")

#     job = db.collection("jobs").document(data.job_id).get()
#     if not job.exists or job.to_dict()["status"] != "open":
#         raise HTTPException(status_code=400, detail="Job not available")

#     app_id = str(uuid.uuid4())
#     db.collection("applications").document(app_id).set({
#         "app_id":                    app_id,
#         "job_id":                    data.job_id,
#         "applicant_uid":             uid,
#         "applicant_phone":           data.applicant_phone,
#         "status":                    "pending",
#         "worker_arriving":           False,
#         "provider_confirmed_arrival": False,
#         "worker_completed":          False,
#         "provider_confirmed_done":   False,
#         "cancelled_by":              None,
#         "cancel_reason":             None,
#         "applied_at":                SERVER_TIMESTAMP,
#     })
#     return {"message": "Application submitted", "app_id": app_id}


# # ── Get All Applications (with optional filters) ──────────────────
# @router.get("/", response_model=List[Application])
# async def get_applications_route(
#     job_id:          Optional[str] = Query(None, description="Filter by job ID"),
#     application_uid: Optional[str] = Query(None, description="Filter by applicant UID"),
#     status:          Optional[str] = Query(None, description="Filter by status (pending/accepted/rejected/cancelled/completed)"),
#     uid: str = Depends(verify_token),
# ):
#     """Fetch all applications, optionally filtered by job_id, applicant UID, or status."""
#     return get_applications(job_id=job_id, application_uid=application_uid, status=status)


# # ── Get Single Application ────────────────────────────────────────
# @router.get("/{app_id}", response_model=Application)
# async def get_application_route(app_id: str, uid: str = Depends(verify_token)):
#     """Get a single application by its ID."""
#     return get_application(app_id)


# # ── Approve Application (Provider) ───────────────────────────────
# @router.patch("/{app_id}/approve")
# async def approve_application(app_id: str, uid: str = Depends(verify_token)):
#     """Provider approves a pending application and assigns the worker."""

#     app = db.collection("applications").document(app_id).get()
#     if not app.exists:
#         raise HTTPException(status_code=404, detail="Application not found")

#     app_data = app.to_dict()
#     job = db.collection("jobs").document(app_data["job_id"]).get()
#     job_data = job.to_dict()

#     if job_data["posted_by_uid"] != uid:
#         raise HTTPException(status_code=403, detail="Not your job")

#     worker_phone = db.collection("workers").document(app_data["applicant_uid"]).get().to_dict()["phone"]

#     db.collection("applications").document(app_id).update({"status": "accepted"})
#     db.collection("jobs").document(app_data["job_id"]).update({
#         "status":                "assigned",
#         "assigned_worker_uid":   app_data["applicant_uid"],
#         "assigned_worker_phone": worker_phone,
#     })

#     return {
#         "message":       "Application approved",
#         "worker_phone":  worker_phone,
#         "provider_phone": job_data["provider_phone"],
#     }


# # ── Worker: I Am Arriving ─────────────────────────────────────────
# @router.patch("/{app_id}/worker-arriving")
# async def worker_arriving(app_id: str, uid: str = Depends(verify_token)):
#     """Worker marks themselves as arriving. Job status → arriving."""

#     app_data = db.collection("applications").document(app_id).get().to_dict()
#     db.collection("applications").document(app_id).update({"worker_arriving": True})
#     db.collection("jobs").document(app_data["job_id"]).update({"status": "arriving"})
#     return {"message": "Provider will be notified"}


# # ── Provider: Confirm Worker Arrived ─────────────────────────────
# @router.patch("/{app_id}/confirm-arrival")
# async def confirm_arrival(app_id: str, uid: str = Depends(verify_token)):
#     """Provider confirms worker has arrived. Job status → in_progress."""

#     app_data = db.collection("applications").document(app_id).get().to_dict()
#     db.collection("applications").document(app_id).update({"provider_confirmed_arrival": True})
#     db.collection("jobs").document(app_data["job_id"]).update({"status": "in_progress"})
#     return {"message": "Job is now in progress"}


# # ── Provider: Worker Did NOT Arrive → Cancel & Reopen ────────────
# @router.patch("/{app_id}/cancel-reopen")
# async def cancel_and_reopen(app_id: str, uid: str = Depends(verify_token)):
#     """Provider cancels because worker didn't arrive. Job reopens."""

#     app_data = db.collection("applications").document(app_id).get().to_dict()
#     db.collection("applications").document(app_id).update({
#         "status":        "rejected",
#         "cancelled_by":  "provider",
#         "cancel_reason": "no_arrival",
#     })
#     db.collection("jobs").document(app_data["job_id"]).update({
#         "status":                "open",
#         "assigned_worker_uid":   None,
#         "assigned_worker_phone": None,
#     })
#     return {"message": "Job reopened"}


# # ── Worker: I Completed the Work ─────────────────────────────────
# @router.patch("/{app_id}/worker-done")
# async def worker_done(app_id: str, uid: str = Depends(verify_token)):
#     """Worker marks job as done. Job status → pending_confirm."""

#     app_data = db.collection("applications").document(app_id).get().to_dict()
#     db.collection("applications").document(app_id).update({"worker_completed": True})
#     db.collection("jobs").document(app_data["job_id"]).update({"status": "pending_confirm"})
#     return {"message": "Waiting for provider to confirm"}


# # ── Provider: Confirm Job Done ────────────────────────────────────
# @router.patch("/{app_id}/confirm-done")
# async def confirm_done(app_id: str, uid: str = Depends(verify_token)):
#     """Provider confirms job is fully completed. Job status → completed."""

#     app_data = db.collection("applications").document(app_id).get().to_dict()
#     db.collection("applications").document(app_id).update({"provider_confirmed_done": True})
#     db.collection("jobs").document(app_data["job_id"]).update({"status": "completed"})
#     return {"message": "Job completed! Both can now rate each other ⭐"}


# # ── Worker: Cancel Application ────────────────────────────────────
# @router.patch("/{app_id}/cancel")
# async def cancel_application(app_id: str, uid: str = Depends(verify_token)):
#     """Worker cancels their own application. Reopens job if already assigned."""

#     app_ref = db.collection("applications").document(app_id)
#     app = app_ref.get()
#     if not app.exists:
#         raise HTTPException(status_code=404, detail="Application not found")

#     app_data = app.to_dict()
#     if app_data["applicant_uid"] != uid:
#         raise HTTPException(status_code=403, detail="Not your application")

#     if app_data.get("status") in ["completed", "cancelled", "rejected"]:
#         raise HTTPException(status_code=400, detail=f"Cannot cancel application with status: {app_data.get('status')}")

#     app_ref.update({
#         "status":        "cancelled",
#         "cancelled_by":  "worker",
#         "cancel_reason": "cancelled_by_worker",
#     })

#     job_ref = db.collection("jobs").document(app_data["job_id"])
#     job = job_ref.get()
#     if job.exists and job.to_dict().get("assigned_worker_uid") == uid:
#         job_ref.update({
#             "status":                "open",
#             "assigned_worker_uid":   None,
#             "assigned_worker_phone": None,
#         })

#     return {"message": "Application cancelled successfully"}


# # ── Generic Partial Update ────────────────────────────────────────
# @router.patch("/{app_id}", response_model=Application)
# async def update_application_route(app_id: str, updates: dict, uid: str = Depends(verify_token)):
#     """Generic partial update for an application (admin/internal use)."""

#     if updates.get("status") == "cancelled" and not updates.get("cancelled_by"):
#         updates["cancelled_by"] = uid

#     return update_application(app_id, updates)


# # ── Delete Application ────────────────────────────────────────────
# @router.delete("/{app_id}")
# async def delete_application_route(app_id: str, uid: str = Depends(verify_token)):
#     """Delete an application by its ID."""
#     return delete_application(app_id)



# # from fastapi import APIRouter, Query, Depends
# # from typing import List, Optional

# # from models.schemas import Application, ApplicationCreate
# # from services.application_service import create_application, get_applications, get_application, update_application, delete_application
# # from core.security import get_current_user

# # router = APIRouter(prefix="/applications", tags=["Applications"])

# # @router.post("/", response_model=Application)
# # async def create_application_route(application: ApplicationCreate, current_user: dict = Depends(get_current_user)):
# #     """Submit a new job application."""
# #     application.application_uid = current_user.get("uid")
# #     # optionally also assign phone if present in token:
# #     if current_user.get("phone_number"):
# #         application.applicant_phone = current_user.get("phone_number")
# #     return create_application(application)

# # @router.get("/", response_model=List[Application])
# # async def get_applications_route(
# #     job_id:          Optional[str] = Query(None, description="Filter by job ID"),
# #     application_uid: Optional[str] = Query(None, description="Filter by applicant UID"),
# #     status:          Optional[str] = Query(None, description="Filter by status (pending/accepted/rejected/cancelled/completed)"),
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     """Fetch all applications, optionally filtered by job_id, applicant UID, or status."""
# #     return get_applications(job_id=job_id, application_uid=application_uid, status=status)

# # @router.get("/{app_id}", response_model=Application)
# # async def get_application_route(app_id: str, current_user: dict = Depends(get_current_user)):
# #     """Get a single application by its ID."""
# #     return get_application(app_id)

# # @router.patch("/{app_id}", response_model=Application)
# # async def update_application_route(app_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
# #     """Partially update an application (status, workflow flags, cancellation)."""
# #     # Example logic to attach cancelled_by if the status changes to cancelled:
# #     if updates.get("status") == "cancelled" and not updates.get("cancelled_by"):
# #         updates["cancelled_by"] = current_user.get("uid")
        
# #     return update_application(app_id, updates)

# # @router.delete("/{app_id}")
# # async def delete_application_route(app_id: str, current_user: dict = Depends(get_current_user)):
# #     """Delete an application by its ID."""
# #     return delete_application(app_id)
