from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_config import db
from middleware.auth_middleware import verify_token
from models.schemas import WorkerCreate, ProviderCreate, ProfileImageUpdate, RoleSwitch
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def delete_old_cloudinary_image(image_url: str):
    if not image_url or "res.cloudinary.com" not in image_url:
        return
    try:
        parts = image_url.split("/upload/")
        if len(parts) < 2:
            return
        path_part = parts[1]
        subparts = path_part.split("/")
        if len(subparts) > 0 and subparts[0].startswith("v") and subparts[0][1:].isdigit():
            subparts = subparts[1:]
        public_id = "/".join(subparts)
        if "." in public_id:
            public_id = public_id.rsplit(".", 1)[0]
        
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Failed to delete old Cloudinary image: {e}")




router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()


# ── Helper: Bearer token se uid lo ───────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    uid = await verify_token(token)
    return uid


# ── Helper: users collection se user data lo ─────────────────────
def get_user_or_404(uid: str) -> dict:
    user = db.collection("users").document(uid).get()
    if not user.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()




# ── Register as Worker ────────────────────────────────────────────
@router.post("/register/worker")
async def register_worker(data: WorkerCreate, uid: str = Depends(get_current_user)):
    """
    Register user as worker.
    users/     ← role, common data
    workers/   ← worker specific data
    """

    # 1. users collection mein common data + role
    db.collection("users").document(uid).set({
        "uid":               uid,
        "name":              data.name,
        "phone":             data.phone,
        "pin_code":          data.pin_code,
        "profile_image_url": data.profile_image_url,
        "role":              "worker",
        "created_at":        SERVER_TIMESTAMP,
    }, merge=True)

    # 2. workers collection mein worker specific data
    db.collection("workers").document(uid).set({
        "uid":            uid,
        "skills":         data.skills,
        "bio":            data.bio,
        "is_available":   True,
        "total_jobs_done": 0,
        "rating":         0,
    }, merge=True)

    return {"message": "Registered as worker", "role": "worker"}


# ── Register as Provider ──────────────────────────────────────────
@router.post("/register/provider")
async def register_provider(data: ProviderCreate, uid: str = Depends(get_current_user)):
    """
    Register user as provider.
    users/     ← role, common data
    providers/ ← provider specific data
    """

    # 1. users collection mein common data + role
    db.collection("users").document(uid).set({
        "uid":               uid,
        "name":              data.name,
        "phone":             data.phone,
        "pin_code":          data.pin_code,
        "profile_image_url": data.profile_image_url,
        "role":              "provider",
        "created_at":        SERVER_TIMESTAMP,
    }, merge=True)

    # 2. providers collection mein provider specific data
    db.collection("providers").document(uid).set({
        "uid":               uid,
        "bio":               data.bio,
        "address":           data.address,
        "total_jobs_posted": 0,
        "rating":            0,
    }, merge=True)

    return {"message": "Registered as provider", "role": "provider"}


# ── Switch Role ───────────────────────────────────────────────────
@router.post("/switch-role")
async def switch_role(data: RoleSwitch, uid: str = Depends(get_current_user)):
    """
    Role switch karo — data dono collections mein safe rahega.
    Sirf users/ mein role field update hoga.
    """

    if data.target_role not in ["worker", "provider"]:
        raise HTTPException(status_code=400, detail="Role must be 'worker' or 'provider'")

    user_data = get_user_or_404(uid)

    if user_data.get("role") == data.target_role:
        raise HTTPException(status_code=400, detail=f"Already a {data.target_role}")

    # Target collection mein document exist karta hai?
    target_collection = "workers" if data.target_role == "worker" else "providers"
    target_doc = db.collection(target_collection).document(uid).get()

    # Pehli baar switch kar raha hai toh basic document banao
    if not target_doc.exists:
        if data.target_role == "worker":
            db.collection("workers").document(uid).set({
                "uid":             uid,
                "skills":          [],
                "bio":             None,
                "is_available":    True,
                "total_jobs_done": 0,
                "rating":          0,
            })
        else:
            db.collection("providers").document(uid).set({
                "uid":               uid,
                "bio":               None,
                "address":           None,
                "total_jobs_posted": 0,
                "rating":            0,
            })

    # Sirf role update karo — history safe rahegi
    db.collection("users").document(uid).update({"role": data.target_role})

    return {"message": f"Role switched to {data.target_role}"}


# ── Get My Profile ────────────────────────────────────────────────
@router.get("/me")
async def get_my_profile(uid: str = Depends(get_current_user)):
    """
    Common data users/ se + role specific data workers/ ya providers/ se.
    """

    user_data = get_user_or_404(uid)
    role = user_data.get("role")

    # Role specific data bhi fetch karo
    if role == "worker":
        extra = db.collection("workers").document(uid).get()
    elif role == "provider":
        extra = db.collection("providers").document(uid).get()
    else:
        extra = None

    profile = {**user_data}
    if extra and extra.exists:
        profile.update(extra.to_dict())

    return profile


# ── Get All Workers ───────────────────────────────────────────────
@router.get("/workers")
async def get_workers():
    """Fetch all workers."""
    users = db.collection("users").where("role", "==", "worker").stream()
    return {"workers": [u.to_dict() for u in users]}


# ── Get All Providers ─────────────────────────────────────────────
@router.get("/providers")
async def get_providers():
    """Fetch all providers."""
    users = db.collection("users").where("role", "==", "provider").stream()
    return {"providers": [u.to_dict() for u in users]}


# ── Get Workers by Pin Code ───────────────────────────────────────
@router.get("/workers/{pin_code}")
async def get_workers_by_pin(pin_code: str):
    users = (
        db.collection("users")
          .where("role",     "==", "worker")
          .where("pin_code", "==", pin_code)
          .stream()
    )
    return {"workers": [u.to_dict() for u in users]}


# ── Get Providers by Pin Code ─────────────────────────────────────
@router.get("/providers/{pin_code}")
async def get_providers_by_pin(pin_code: str):
    users = (
        db.collection("users")
          .where("role",     "==", "provider")
          .where("pin_code", "==", pin_code)
          .stream()
    )
    return {"providers": [u.to_dict() for u in users]}


# ── Get Single User ───────────────────────────────────────────────
@router.get("/{user_id}")
async def get_user(user_id: str, uid: str = Depends(get_current_user)):
    """Get any user by ID."""
    return get_user_or_404(user_id)


# ── Update User ───────────────────────────────────────────────────
@router.put("/{user_id}")
async def update_user(user_id: str, data: dict, uid: str = Depends(get_current_user)):
    """Update your own profile."""

    if user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user_data = get_user_or_404(uid)
    role = user_data.get("role")

    # Common fields users/ mein update karo
    common_fields = ["name", "phone", "pin_code", "profile_image_url"]
    common_update = {k: v for k, v in data.items() if k in common_fields}
    if common_update:
        db.collection("users").document(uid).update(common_update)

    # Role specific fields apni collection mein update karo
    if role == "worker":
        worker_fields = ["skills", "bio", "is_available"]
        worker_update = {k: v for k, v in data.items() if k in worker_fields}
        if worker_update:
            db.collection("workers").document(uid).update(worker_update)

    elif role == "provider":
        provider_fields = ["bio", "address"]
        provider_update = {k: v for k, v in data.items() if k in provider_fields}
        if provider_update:
            db.collection("providers").document(uid).update(provider_update)

    return {"message": "Profile updated"}


# ── Update Profile Image (Direct / No Auth Check) ─────────────────
@router.patch("/{uid}/profile-image")
async def update_profile_image_direct(uid: str, data: ProfileImageUpdate):
    """
    Update profile image URL directly with Firestore existence check and URL validation.
    """
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    if not data.profile_image_url.startswith("https://res.cloudinary.com/"):
        raise HTTPException(status_code=400, detail="Profile image URL must start with https://res.cloudinary.com/")

    user_ref.update({
        "profile_image_url": data.profile_image_url
    })

    updated_doc = user_ref.get()
    return updated_doc.to_dict()


# ── Update Profile Image ──────────────────────────────────────────
@router.patch("/{user_id}/profile-image")
async def update_profile_image(user_id: str, data: ProfileImageUpdate, uid: str = Depends(get_current_user)):
    """Update profile image URL."""

    if user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorized")

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    if user_doc.exists:
        current_data = user_doc.to_dict()
        old_image_url = current_data.get("profile_image_url")
        if old_image_url:
            delete_old_cloudinary_image(old_image_url)

    user_ref.update({
        "profile_image_url": data.profile_image_url
    })
    return {"message": "Profile image updated"}


# ── Delete User ───────────────────────────────────────────────────
@router.delete("/{user_id}")
async def delete_user(user_id: str, uid: str = Depends(get_current_user)):
    """Delete your own account — removes from all collections."""

    if user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    user_data = get_user_or_404(uid)
    role = user_data.get("role")

    # Teeno collections se delete karo
    db.collection("users").document(uid).delete()
    db.collection("workers").document(uid).delete()    # exist na kare toh bhi safe hai
    db.collection("providers").document(uid).delete()  # exist na kare toh bhi safe hai

    return {"message": "Account deleted successfully"}