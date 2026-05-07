from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional

from models.schemas import job, jobCreate
from services.job_service import create_job, get_jobs, get_job, update_job, delete_job
from core.security import get_current_user

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/", response_model=job)
async def create_job_route(job_data: jobCreate, current_user: dict = Depends(get_current_user)):
    """Create a new job listing. Auto-assigns the logged-in user as the poster."""
    job_data.posted_by = current_user.get("uid")
    return create_job(job_data)

@router.get("/", response_model=List[job])
async def get_jobs_route(
    pincode:  Optional[str] = Query(None, description="Filter jobs by pincode"),
    category: Optional[str] = Query(None, description="Filter jobs by category"),
    status:   Optional[str] = Query(None, description="Filter jobs by status (active/inactive/pending)"),
):
    """Fetch all jobs, optionally filtered by pincode, category, and/or status."""
    return get_jobs(pincode=pincode, category=category, status=status)

@router.get("/{job_id}", response_model=job)
async def get_job_route(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single job by ID (requires Auth)."""
    return get_job(job_id)

@router.put("/{job_id}", response_model=job)
async def update_job_route(job_id: str, job_data: jobCreate, current_user: dict = Depends(get_current_user)):
    """Update an existing job by ID (requires Auth)."""
    # Force posted_by to be the current user to prevent transferring ownership maliciously
    job_data.posted_by = current_user.get("uid")
    return update_job(job_id, job_data)

@router.delete("/{job_id}")
async def delete_job_route(job_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a job by ID (requires Auth). Note: currently allows any auth user to delete."""
    return delete_job(job_id)
