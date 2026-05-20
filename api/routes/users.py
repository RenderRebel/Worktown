from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional

from models.schemas import User, UserCreate
from models.worker import WorkerCreate
from models.provider import ProviderCreate
from services.user_service import (
    create_user, get_users, get_user, update_user, delete_user,
    register_worker, register_provider, get_my_profile, update_profile_image
)
from core.security import get_current_user
from pydantic import BaseModel

class ProfileImageUpdate(BaseModel):
    profile_image_url: str

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register/worker")
async def register_worker_route(data: WorkerCreate, current_user: dict = Depends(get_current_user)):
    """Register a new worker."""
    return register_worker(data, current_user)

@router.post("/register/provider")
async def register_provider_route(data: ProviderCreate, current_user: dict = Depends(get_current_user)):
    """Register a new service provider."""
    return register_provider(data, current_user)

@router.get("/me")
async def get_my_profile_route(current_user: dict = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return get_my_profile(current_user)

@router.post("/", response_model=User)
async def create_user_route(user: UserCreate, current_user: dict = Depends(get_current_user)):
    """Create a new user (requires Auth)."""
    return create_user(user, current_user)

@router.get("/", response_model=List[User])
async def get_users_route(
    pin_code: Optional[str] = Query(None, description="Filter users by pin code"),
    role:     Optional[str] = Query(None, description="Filter users by role (e.g. worker, provider, admin)"),
):
    """Fetch all users, optionally filtered by pin_code and/or role."""
    return get_users(pin_code=pin_code, role=role)

@router.get("/workers", response_model=List[User])
async def get_workers_route():
    """Fetch all workers."""
    return get_users(role="worker")

@router.get("/providers", response_model=List[User])
async def get_providers_route():
    """Fetch all providers."""
    return get_users(role="provider")

@router.get("/workers/{pin_code}", response_model=List[User])
async def get_workers_by_pin_route(pin_code: str):
    """Fetch all workers for a specific pin code."""
    return get_users(role="worker", pin_code=pin_code)

@router.get("/providers/{pin_code}", response_model=List[User])
async def get_providers_by_pin_route(pin_code: str):
    """Fetch all providers for a specific pin code."""
    return get_users(role="provider", pin_code=pin_code)

@router.get("/{user_id}", response_model=User)
async def get_user_route(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single user by ID (requires Auth)."""
    return get_user(user_id)

@router.put("/{user_id}", response_model=User)
async def update_user_route(user_id: str, user: UserCreate, current_user: dict = Depends(get_current_user)):
    """Update an existing user by ID. You can only update your own profile."""
    if user_id != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    return update_user(user_id, user, current_user)

@router.delete("/{user_id}")
async def delete_user_route(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a user by ID. You can only delete your own profile."""
    if user_id != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    return delete_user(user_id)

@router.patch("/{user_id}/profile-image")
async def update_profile_image_route(user_id: str, data: ProfileImageUpdate, current_user: dict = Depends(get_current_user)):
    """Update only the profile image URL for a user."""
    if user_id != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to update this user's profile image")
    return update_profile_image(user_id, data.profile_image_url)
