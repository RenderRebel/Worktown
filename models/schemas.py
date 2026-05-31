from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime


# ── Enums ─────────────────────────────────────────────────────────

class Role(str, Enum):
    worker   = "worker"
    provider = "provider"

class Status(str, Enum):
    active   = "active"
    inactive = "inactive"
    pending  = "pending"

class ApplicationStatus(str, Enum):
    pending   = "pending"
    accepted  = "accepted"
    rejected  = "rejected"
    cancelled = "cancelled"
    completed = "completed"

class ItemType(str, Enum):
    worker   = "worker"
    provider = "provider"

class JobType(str, Enum):
    part_time = "part_time"
    full_time = "full_time"


# ── Worker Models ─────────────────────────────────────────────────

class WorkerCreate(BaseModel):
    name:              str            = Field(..., description="Full name")
    phone:             str            = Field(..., pattern=r"^\d{10}$", description="10 digit phone number")
    pin_code:          str            = Field(..., description="Area pin code")
    skills:            List[str]      = Field(default=[], description="List of skills")
    bio:               Optional[str]  = Field(default=None, description="Short bio")
    profile_image_url: Optional[str]  = Field(default=None, description="Profile image URL")

class WorkerUpdate(BaseModel):
    name:              Optional[str]       = None
    phone:             Optional[str]       = Field(default=None, pattern=r"^\d{10}$")
    pin_code:          Optional[str]       = None
    skills:            Optional[List[str]] = None
    bio:               Optional[str]       = None
    is_available:      Optional[bool]      = None
    profile_image_url: Optional[str]       = None


# ── Provider Models ───────────────────────────────────────────────

class ProviderCreate(BaseModel):
    name:              str           = Field(..., description="Full name")
    phone:             str           = Field(..., pattern=r"^\d{10}$", description="10 digit phone number")
    pin_code:          str           = Field(..., description="Area pin code")
    address:           Optional[str] = Field(default=None, description="Full address")
    bio:               Optional[str] = Field(default=None, description="Short bio")
    profile_image_url: Optional[str] = Field(default=None, description="Profile image URL")

class ProviderUpdate(BaseModel):
    name:              Optional[str] = None
    phone:             Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    pin_code:          Optional[str] = None
    address:           Optional[str] = None
    bio:               Optional[str] = None
    profile_image_url: Optional[str] = None


# ── User Models ───────────────────────────────────────────────────

class UserCreate(BaseModel):
    name:              str           = Field(..., description="Full name")
    phone:             Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    email:             Optional[str] = Field(default=None)
    pin_code:          str           = Field(..., description="Area pin code")
    role:              Role          = Field(..., description="worker or provider")
    address:           Optional[str] = Field(default=None)
    profile_image_url: Optional[str] = Field(default=None)
    rating:            float         = Field(default=0.0, ge=0.0, le=5.0)

    # Worker specific
    skills:            Optional[List[str]] = None
    bio:               Optional[str]       = None
    total_jobs_done:   Optional[int]       = Field(default=None, ge=0)
    is_available:      Optional[bool]      = None

    # Provider specific
    total_jobs_posted: Optional[int] = Field(default=None, ge=0)

class User(UserCreate):
    uid: str = Field(..., description="Firebase UID")


# ── Job Models ────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title:       str           = Field(..., description="Job title")
    description: str           = Field(..., description="Job description")
    category:    str           = Field(..., description="Job category")
    pin_code:    str           = Field(..., description="Area pin code")
    pay:         float         = Field(..., gt=0, description="Pay amount")
    posted_by:   Optional[str] = Field(default=None, description="UID of poster")

    # ───── add these two ─────
    assigned_worker_uid:   Optional[str] = None
    assigned_worker_phone: Optional[str] = None

    job_type:              JobType       = Field(..., description="Job type: part_time or full_time")
    title_hi:              Optional[str] = Field(default=None, description="Job title in Hindi")
    description_hi:        Optional[str] = Field(default=None, description="Job description in Hindi")

class job(JobCreate):
    id: str = Field(..., description="Firestore document ID")




# ── Application Models ────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id:          str           = Field(..., description="Job ID")
    applicant_phone: str           = Field(..., pattern=r"^\d{10}$", description="10 digit phone")
    status:          ApplicationStatus = Field(default=ApplicationStatus.pending)

    # Workflow flags
    worker_arriving:            bool = Field(default=False)
    provider_confirmed_arrival: bool = Field(default=False)
    worker_completed:           bool = Field(default=False)
    provider_confirmed_done:    bool = Field(default=False)

    # Cancellation
    cancelled_by:  Optional[str] = None
    cancel_reason: Optional[str] = None

    # Timestamp
    applied_at: datetime = Field(default_factory=datetime.utcnow)

class Application(ApplicationCreate):
    app_id: str = Field(..., description="Firestore document ID")# from pydantic import BaseModel, Field

# models/schemas.py mein yeh 2 models add karo agar nahi hain

class ProfileImageUpdate(BaseModel):
    profile_image_url: str

class RoleSwitch(BaseModel):
    target_role: str  # "worker" or "provider"
# from typing import List, Optional
# from enum import Enum
# from datetime import datetime


# # ── Shared Enums ──────────────────────────────────────────────────────────────

# class Status(str, Enum):
#     active   = "active"
#     inactive = "inactive"
#     pending  = "pending"


# # ── User Schemas ─────────────────────────────────────────────────────────────

# class UserCreate(BaseModel):
#     name: str = Field(..., description="Full name of the user")
#     phone: Optional[str] = Field(
#         default=None,
#         pattern=r"^\d{10}$",
#         description="Phone number must be exactly 10 digits",
#     )
#     email: Optional[str] = Field(default=None, description="Email address of the user")
#     pin_code: str = Field(..., description="Pin code or zip code of the user's location")
#     role: str = Field(..., description="Role of the user (e.g. worker, provider, admin)")
#     address: Optional[str] = Field(default="", description="Address of the user")
#     rating: float = Field(default=0.0, ge=0.0, le=5.0, description="User rating between 0 and 5")
#     profile_image_url: Optional[str] = Field(default=None, description="URL of the user's profile image")

#     # ── Worker-specific fields (populated when role == "worker") ──────────────
#     skills: Optional[List[str]] = Field(default=None, description="List of skills (worker only)")
#     bio: Optional[str] = Field(default=None, description="Short bio or description (worker only)")
#     total_jobs_done: Optional[int] = Field(default=None, ge=0, description="Total jobs completed (worker only)")
#     is_available: Optional[bool] = Field(default=None, description="Whether the worker is currently available")

#     # ── Provider-specific fields (populated when role == "provider") ──────────
#     total_jobs_posted: Optional[int] = Field(default=None, ge=0, description="Total jobs posted (provider only)")

# class User(UserCreate):
#     id: str = Field(..., description="Unique ID of the user")


# # ── Provider Enums ────────────────────────────────────────────────────────────




# # ── Provider Schemas ──────────────────────────────────────────────────────────

# class jobCreate(BaseModel):
#     title: str = Field(..., description="Title / headline of the service offered")
#     description: str = Field(..., description="Detailed description of the service")
#     category: str = Field(..., description="Category of the service")
#     pincode: str = Field(..., min_length=4, max_length=10, description="Area pin / zip code")
#     phone_number: str = Field(..., pattern=r"^\d{10}$", description="Contact phone number of the provider (exactly 10 digits)")
#     pay: float = Field(..., gt=0, description="Expected pay / rate for the service")
#     status: Status = Field(default=Status.active, description="Availability status")
#     posted_by: str = Field(..., description="UID or name of the user who posted this listing")

# class job(jobCreate):
#     id: str = Field(..., description="Unique Firestore document ID")


# # ── Application Enums ─────────────────────────────────────────────────────────

# class ApplicationStatus(str, Enum):
#     pending   = "pending"
#     accepted  = "accepted"
#     rejected  = "rejected"
#     cancelled = "cancelled"
#     completed = "completed"


# # ── Application Schemas ───────────────────────────────────────────────────────

# class ApplicationCreate(BaseModel):
#     job_id:                    str               = Field(..., description="ID of the job being applied to")
#     application_uid:           str               = Field(..., description="UID of the applicant (worker)")
#     applicant_phone:           str               = Field(..., pattern=r"^\d{10}$", description="Phone number of the applicant (exactly 10 digits)")
#     status:                    ApplicationStatus = Field(default=ApplicationStatus.pending, description="Current status of the application")

#     # ── Live workflow flags ────────────────────────────────────────────────────
#     worker_arriving:           bool              = Field(default=False, description="Worker has marked themselves as arriving")
#     provider_confirmed_arrival: bool             = Field(default=False, description="Provider confirmed the worker has arrived")
#     worker_completed:          bool              = Field(default=False, description="Worker marked the job as completed")
#     provider_confirmed_done:   bool              = Field(default=False, description="Provider confirmed the job is done")

#     # ── Cancellation ──────────────────────────────────────────────────────────
#     cancelled_by:              Optional[str]     = Field(default=None, description="UID of whoever cancelled (worker or provider)")
#     cancel_reason:             Optional[str]     = Field(default=None, description="Reason for cancellation")

#     # ── Timestamps ────────────────────────────────────────────────────────────
#     applied_at:                datetime          = Field(default_factory=datetime.utcnow, description="Timestamp when the application was submitted")

# class Application(ApplicationCreate):
#     app_id: str = Field(..., description="Unique Firestore document ID of the application")
