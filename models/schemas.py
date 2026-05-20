from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


# ── Shared Enums ──────────────────────────────────────────────────────────────

class Status(str, Enum):
    active   = "active"
    inactive = "inactive"
    pending  = "pending"


# ── User Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., description="Full name of the user")
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+\d{1,3}\d{10}$",
        description="Phone number with country code followed by exactly 10 digits (e.g. +919876543210)",
    )
    email: Optional[str] = Field(default=None, description="Email address of the user")
    pin_code: str = Field(..., description="Pin code or zip code of the user's location")
    role: str = Field(..., description="Role of the user (e.g. worker, provider, admin)")
    address: Optional[str] = Field(default="", description="Address of the user")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="User rating between 0 and 5")
    profile_image_url: Optional[str] = Field(default=None, description="URL of the user's profile image")

    # ── Worker-specific fields (populated when role == "worker") ──────────────
    skills: Optional[List[str]] = Field(default=None, description="List of skills (worker only)")
    bio: Optional[str] = Field(default=None, description="Short bio or description (worker only)")
    total_jobs_done: Optional[int] = Field(default=None, ge=0, description="Total jobs completed (worker only)")
    is_available: Optional[bool] = Field(default=None, description="Whether the worker is currently available")

    # ── Provider-specific fields (populated when role == "provider") ──────────
    total_jobs_posted: Optional[int] = Field(default=None, ge=0, description="Total jobs posted (provider only)")

class User(UserCreate):
    id: str = Field(..., description="Unique ID of the user")


# ── Provider Enums ────────────────────────────────────────────────────────────




# ── Provider Schemas ──────────────────────────────────────────────────────────

class jobCreate(BaseModel):
    title: str = Field(..., description="Title / headline of the service offered")
    description: str = Field(..., description="Detailed description of the service")
    category: str = Field(..., description="Category of the service")
    pincode: str = Field(..., min_length=4, max_length=10, description="Area pin / zip code")
    phone_number: str = Field(..., description="Contact phone number of the provider")
    pay: float = Field(..., gt=0, description="Expected pay / rate for the service")
    status: Status = Field(default=Status.active, description="Availability status")
    posted_by: str = Field(..., description="UID or name of the user who posted this listing")

class job(jobCreate):
    id: str = Field(..., description="Unique Firestore document ID")


# ── Favorites ─────────────────────────────────────────────────────────────────

class ItemType(str, Enum):
    worker   = "worker"
    provider = "provider"

class FavoriteCreate(BaseModel):
    user_id:   str      = Field(..., description="UID of the user who saved this favourite")
    item_type: ItemType = Field(..., description="Type of item: 'worker' or 'provider'")
    item_id:   str      = Field(..., description="Firestore document ID of the saved item")

class Favorite(FavoriteCreate):
    id: str = Field(..., description="Unique Firestore document ID of the favourite entry")


# ── Application Enums ─────────────────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    pending   = "pending"
    accepted  = "accepted"
    rejected  = "rejected"
    cancelled = "cancelled"
    completed = "completed"


# ── Application Schemas ───────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id:                    str               = Field(..., description="ID of the job being applied to")
    application_uid:           str               = Field(..., description="UID of the applicant (worker)")
    applicant_phone:           str               = Field(..., description="Phone number of the applicant")
    status:                    ApplicationStatus = Field(default=ApplicationStatus.pending, description="Current status of the application")

    # ── Live workflow flags ────────────────────────────────────────────────────
    worker_arriving:           bool              = Field(default=False, description="Worker has marked themselves as arriving")
    provider_confirmed_arrival: bool             = Field(default=False, description="Provider confirmed the worker has arrived")
    worker_completed:          bool              = Field(default=False, description="Worker marked the job as completed")
    provider_confirmed_done:   bool              = Field(default=False, description="Provider confirmed the job is done")

    # ── Cancellation ──────────────────────────────────────────────────────────
    cancelled_by:              Optional[str]     = Field(default=None, description="UID of whoever cancelled (worker or provider)")
    cancel_reason:             Optional[str]     = Field(default=None, description="Reason for cancellation")

    # ── Timestamps ────────────────────────────────────────────────────────────
    applied_at:                datetime          = Field(default_factory=datetime.utcnow, description="Timestamp when the application was submitted")

class Application(ApplicationCreate):
    app_id: str = Field(..., description="Unique Firestore document ID of the application")
