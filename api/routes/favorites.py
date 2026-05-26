from fastapi import APIRouter, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.schemas import Favorite, FavoriteCreate
from services.favorite_service import add_favorite, get_favorites, get_favorite, remove_favorite

router = APIRouter(prefix="/favorites", tags=["Favorites"])
security = HTTPBearer()


# ── Helper: Bearer token se uid lo ───────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    uid = await verify_token(token)
    return uid


# ── Add Favorite ──────────────────────────────────────────────────
@router.post("/", response_model=Favorite)
async def add_favorite_route(favorite: FavoriteCreate, uid: str = Depends(get_current_user)):
    """Save a worker or provider to favourites."""
    favorite.user_id = uid
    return add_favorite(favorite)


# ── Get All Favorites ─────────────────────────────────────────────
@router.get("/", response_model=List[Favorite])
async def get_favorites_route(
    item_type: Optional[str] = Query(None, description="Filter by item type: 'worker' or 'provider'"),
    uid: str = Depends(get_current_user),
):
    """Fetch all favourites for the logged in user."""
    return get_favorites(user_id=uid, item_type=item_type)


# ── Get Single Favorite ───────────────────────────────────────────
@router.get("/{favorite_id}", response_model=Favorite)
async def get_favorite_route(favorite_id: str, uid: str = Depends(get_current_user)):
    """Get a single favourite entry by ID."""
    return get_favorite(favorite_id)


# ── Remove Favorite ───────────────────────────────────────────────
@router.delete("/{favorite_id}")
async def remove_favorite_route(favorite_id: str, uid: str = Depends(get_current_user)):
    """Remove a favourite by its document ID."""
    return remove_favorite(favorite_id)



# from fastapi import APIRouter, Query, Depends
# from typing import List, Optional

# from models.schemas import Favorite, FavoriteCreate
# from services.favorite_service import add_favorite, get_favorites, get_favorite, remove_favorite
# from core.security import get_current_user

# router = APIRouter(prefix="/favorites", tags=["Favorites"])

# @router.post("/", response_model=Favorite)
# async def add_favorite_route(favorite: FavoriteCreate, current_user: dict = Depends(get_current_user)):
#     """Save a worker or provider to a user's favourites."""
#     favorite.user_id = current_user.get("uid")
#     return add_favorite(favorite)

# @router.get("/", response_model=List[Favorite])
# async def get_favorites_route(
#     item_type: Optional[str] = Query(None, description="Filter by item type: 'worker' or 'provider'"),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Fetch all favourites for the logged in user, optionally filtered by item_type."""
#     return get_favorites(user_id=current_user.get("uid"), item_type=item_type)

# @router.get("/{favorite_id}", response_model=Favorite)
# async def get_favorite_route(favorite_id: str, current_user: dict = Depends(get_current_user)):
#     """Get a single favourite entry by ID."""
#     return get_favorite(favorite_id)

# @router.delete("/{favorite_id}")
# async def remove_favorite_route(favorite_id: str, current_user: dict = Depends(get_current_user)):
#     """Remove a favourite by its document ID."""
#     return remove_favorite(favorite_id)
