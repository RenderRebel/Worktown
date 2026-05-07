from fastapi import APIRouter, Query, Depends
from typing import List, Optional

from models.schemas import Application, ApplicationCreate
from services.application_service import create_application, get_applications, get_application, update_application, delete_application
from core.security import get_current_user

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("/", response_model=Application)
async def create_application_route(application: ApplicationCreate, current_user: dict = Depends(get_current_user)):
    """Submit a new job application."""
    application.application_uid = current_user.get("uid")
    # optionally also assign phone if present in token:
    if current_user.get("phone_number"):
        application.applicant_phone = current_user.get("phone_number")
    return create_application(application)

@router.get("/", response_model=List[Application])
async def get_applications_route(
    job_id:          Optional[str] = Query(None, description="Filter by job ID"),
    application_uid: Optional[str] = Query(None, description="Filter by applicant UID"),
    status:          Optional[str] = Query(None, description="Filter by status (pending/accepted/rejected/cancelled/completed)"),
    current_user: dict = Depends(get_current_user)
):
    """Fetch all applications, optionally filtered by job_id, applicant UID, or status."""
    return get_applications(job_id=job_id, application_uid=application_uid, status=status)

@router.get("/{app_id}", response_model=Application)
async def get_application_route(app_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single application by its ID."""
    return get_application(app_id)

@router.patch("/{app_id}", response_model=Application)
async def update_application_route(app_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    """Partially update an application (status, workflow flags, cancellation)."""
    # Example logic to attach cancelled_by if the status changes to cancelled:
    if updates.get("status") == "cancelled" and not updates.get("cancelled_by"):
        updates["cancelled_by"] = current_user.get("uid")
        
    return update_application(app_id, updates)

@router.delete("/{app_id}")
async def delete_application_route(app_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an application by its ID."""
    return delete_application(app_id)
