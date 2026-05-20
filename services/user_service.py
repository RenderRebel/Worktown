from fastapi import HTTPException
from typing import List, Optional
from models.schemas import User, UserCreate
from core.database import get_db


def create_user(user: UserCreate, token_claims: dict) -> dict:
    if user.role == "worker":
        if user.skills is None or user.bio is None or user.total_jobs_done is None or user.is_available is None:
            raise HTTPException(
                status_code=400, 
                detail="Workers must provide skills, bio, total_jobs_done, and is_available fields."
            )
    elif user.role == "provider":
        if user.total_jobs_posted is None:
            raise HTTPException(
                status_code=400, 
                detail="Providers must provide the total_jobs_posted field."
            )

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = user.dict()
    
    # Force phone/email from Firebase token if present
    uid = token_claims.get("uid")
    if token_claims.get("phone_number"):
        data["phone"] = token_claims.get("phone_number")
    if token_claims.get("email"):
        data["email"] = token_claims.get("email")

    try:
        db.collection(u'users').document(uid).set(data)
        data["id"] = uid
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add user: {str(e)}")


def get_users(pin_code: Optional[str] = None, role: Optional[str] = None) -> List[dict]:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ref = db.collection(u'users')
    if pin_code:
        ref = ref.where(u'pin_code', u'==', pin_code)
    if role:
        ref = ref.where(u'role', u'==', role)

    try:
        docs = ref.stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


def register_worker(data, token_claims: dict) -> dict:
    """Register a new worker using V2 schema but store in unified 'users' collection."""
    uid = token_claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="UID missing in token")

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    existing = db.collection("users").document(uid).get()
    if existing.exists:
        raise HTTPException(status_code=400, detail="User already registered")

    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    worker_data = {
        "uid": uid,
        "role": "worker",
        "name": data.name,
        "phone": data.phone,
        "pin_code": data.pin_code,
        "skills": data.skills,
        "bio": data.bio,
        "profile_image_url": data.profile_image_url,
        "rating": 0.0,
        "total_jobs_done": 0,
        "is_available": True,
        "created_at": SERVER_TIMESTAMP
    }

    db.collection("users").document(uid).set(worker_data)
    return {"message": "Worker registered successfully", "uid": uid, "profile": worker_data}


def register_provider(data, token_claims: dict) -> dict:
    """Register a new provider using V2 schema but store in unified 'users' collection."""
    uid = token_claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="UID missing in token")

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    existing = db.collection("users").document(uid).get()
    if existing.exists:
        raise HTTPException(status_code=400, detail="User already registered")

    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    provider_data = {
        "uid": uid,
        "role": "provider",
        "name": data.name,
        "phone": data.phone,
        "pin_code": data.pin_code,
        "address": data.address,
        "profile_image_url": data.profile_image_url,
        "rating": 0.0,
        "total_jobs_posted": 0,
        "created_at": SERVER_TIMESTAMP
    }

    db.collection("users").document(uid).set(provider_data)
    return {"message": "Provider registered successfully", "uid": uid, "profile": provider_data}


def get_my_profile(token_claims: dict) -> dict:
    """Fetch the current user's profile from the unified 'users' collection."""
    uid = token_claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="UID missing in token")

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    user_doc = db.collection("users").document(uid).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = user_doc.to_dict()
    return {"role": data.get("role"), "profile": data}


def get_user(user_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc = db.collection(u'users').document(user_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        return {**doc.to_dict(), "id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")


def update_user(user_id: str, user: UserCreate, token_claims: dict) -> dict:
    if user.role == "worker":
        if user.skills is None or user.bio is None or user.total_jobs_done is None or user.is_available is None:
            raise HTTPException(
                status_code=400, 
                detail="Workers must provide skills, bio, total_jobs_done, and is_available fields."
            )
    elif user.role == "provider":
        if user.total_jobs_posted is None:
            raise HTTPException(
                status_code=400, 
                detail="Providers must provide the total_jobs_posted field."
            )

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'users').document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
            
        data = user.dict()
        
        # Force phone/email from Firebase token if present
        if token_claims.get("phone_number"):
            data["phone"] = token_claims.get("phone_number")
        if token_claims.get("email"):
            data["email"] = token_claims.get("email")
            
        doc_ref.set(data)
        data["id"] = user_id
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


def delete_user(user_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'users').document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        doc_ref.delete()
        return {"message": f"User {user_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

def update_profile_image(user_id: str, profile_image_url: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'users').document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
            
        doc_ref.update({u"profile_image_url": profile_image_url})
        return {"message": "Profile image updated successfully", "profile_image_url": profile_image_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile image: {str(e)}")
