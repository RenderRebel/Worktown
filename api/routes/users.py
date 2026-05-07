from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional

from models.schemas import User, UserCreate
from services.user_service import create_user, get_users, get_user, update_user, delete_user
from core.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

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
