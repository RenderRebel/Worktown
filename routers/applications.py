from fastapi import APIRouter, Depends, HTTPException
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.application import ApplicationCreate
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import uuid

router = APIRouter(prefix="/applications-v2", tags=["Applications V2"])

# ── Apply for a Job (Worker) ─────────────────────────────────────
@router.post("/")
async def apply_for_job(data: ApplicationCreate, uid: str = Depends(verify_token)):

    # Only workers can apply
    worker = db.collection("workers").document(uid).get()
    if not worker.exists:
        raise HTTPException(status_code=403, detail="Only workers can apply")

    # Check job exists and is open
    job = db.collection("jobs").document(data.job_id).get()
    if not job.exists or job.to_dict()["status"] != "open":
        raise HTTPException(status_code=400, detail="Job not available")

    app_id = str(uuid.uuid4())
    db.collection("applications").document(app_id).set({
        "app_id": app_id,
        "job_id": data.job_id,
        "applicant_uid": uid,
        "applicant_phone": data.applicant_phone,
        "status": "pending",
        "worker_arriving": False,
        "provider_confirmed_arrival": False,
        "worker_completed": False,
        "provider_confirmed_done": False,
        "cancelled_by": None,
        "cancel_reason": None,
        "applied_at": SERVER_TIMESTAMP
    })
    return {"message": "Application submitted", "app_id": app_id}


# ── Approve Application (Provider) ──────────────────────────────
@router.patch("/{app_id}/approve")
async def approve_application(app_id: str, uid: str = Depends(verify_token)):

    app = db.collection("applications").document(app_id).get()
    if not app.exists:
        raise HTTPException(status_code=404, detail="Application not found")

    app_data = app.to_dict()
    job = db.collection("jobs").document(app_data["job_id"]).get()
    job_data = job.to_dict()

    # Make sure this provider owns the job
    if job_data["posted_by_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your job")

    worker = db.collection("workers").document(app_data["applicant_uid"]).get()
    worker_phone = worker.to_dict()["phone"]

    # Update application status
    db.collection("applications").document(app_id).update({
        "status": "accepted"
    })

    # Update job — assign the worker, share phone numbers
    db.collection("jobs").document(app_data["job_id"]).update({
        "status": "assigned",
        "assigned_worker_uid": app_data["applicant_uid"],
        "assigned_worker_phone": worker_phone
    })

    # Return both phone numbers to Flutter
    return {
        "message": "Application approved",
        "worker_phone": worker_phone,
        "provider_phone": job_data["provider_phone"]
    }


# ── Worker: I Am Arriving ────────────────────────────────────────
@router.patch("/{app_id}/worker-arriving")
async def worker_arriving(app_id: str, uid: str = Depends(verify_token)):
    db.collection("applications").document(app_id).update({
        "worker_arriving": True
    })
    db.collection("jobs").document(
        db.collection("applications").document(app_id).get().to_dict()["job_id"]
    ).update({"status": "arriving"})
    return {"message": "Provider will be notified"}


# ── Provider: Confirm Worker Arrived ────────────────────────────
@router.patch("/{app_id}/confirm-arrival")
async def confirm_arrival(app_id: str, uid: str = Depends(verify_token)):
    db.collection("applications").document(app_id).update({
        "provider_confirmed_arrival": True
    })
    db.collection("jobs").document(
        db.collection("applications").document(app_id).get().to_dict()["job_id"]
    ).update({"status": "in_progress"})
    return {"message": "Job is now in progress"}


# ── Provider: Worker Did NOT Arrive → Cancel & Reopen ───────────
@router.patch("/{app_id}/cancel-reopen")
async def cancel_and_reopen(app_id: str, uid: str = Depends(verify_token)):
    app_data = db.collection("applications").document(app_id).get().to_dict()

    db.collection("applications").document(app_id).update({
        "status": "rejected",
        "cancelled_by": "provider",
        "cancel_reason": "no_arrival"
    })
    db.collection("jobs").document(app_data["job_id"]).update({
        "status": "open",           # job reopens!
        "assigned_worker_uid": None,
        "assigned_worker_phone": None
    })
    return {"message": "Job reopened"}


# ── Worker: I Completed the Work ────────────────────────────────
@router.patch("/{app_id}/worker-done")
async def worker_done(app_id: str, uid: str = Depends(verify_token)):
    app_data = db.collection("applications").document(app_id).get().to_dict()
    db.collection("applications").document(app_id).update({
        "worker_completed": True
    })
    db.collection("jobs").document(app_data["job_id"]).update({
        "status": "pending_confirm"
    })
    return {"message": "Waiting for provider to confirm"}


# ── Provider: Confirm Job Done ───────────────────────────────────
@router.patch("/{app_id}/confirm-done")
async def confirm_done(app_id: str, uid: str = Depends(verify_token)):
    app_data = db.collection("applications").document(app_id).get().to_dict()
    db.collection("applications").document(app_id).update({
        "provider_confirmed_done": True
    })
    db.collection("jobs").document(app_data["job_id"]).update({
        "status": "completed"
    })
    return {"message": "Job completed! Both can now rate each other ⭐"}


# ── Worker: Cancel Application ───────────────────────────────────
@router.patch("/{app_id}/cancel")
async def cancel_application_by_worker(app_id: str, uid: str = Depends(verify_token)):
    app_ref = db.collection("applications").document(app_id)
    app = app_ref.get()
    
    if not app.exists:
        raise HTTPException(status_code=404, detail="Application not found")
        
    app_data = app.to_dict()
    
    # Ensure only the applicant can cancel their application
    if app_data["applicant_uid"] != uid:
        raise HTTPException(status_code=403, detail="Not your application")
        
    # Prevent cancelling completed or already cancelled jobs
    if app_data.get("status") in ["completed", "cancelled", "rejected"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel application with status: {app_data.get('status')}")

    # 1. Update the application document
    app_ref.update({
        "status": "cancelled",
        "cancelled_by": "worker",
        "cancel_reason": "cancelled_by_worker"
    })
    
    # 2. If the job was already assigned to this worker, we must reopen the job
    job_ref = db.collection("jobs").document(app_data["job_id"])
    job = job_ref.get()
    
    if job.exists:
        job_data = job.to_dict()
        if job_data.get("assigned_worker_uid") == uid:
            job_ref.update({
                "status": "open",
                "assigned_worker_uid": None,
                "assigned_worker_phone": None
            })
            
    return {"message": "Application cancelled successfully"}

