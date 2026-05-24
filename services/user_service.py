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
    }

    if existing.exists:
        existing_data = existing.to_dict()
        if "total_jobs_done" not in existing_data:
            worker_data["total_jobs_done"] = 0
            worker_data["rating"] = 0.0
            worker_data["is_available"] = True
            
        db.collection("users").document(uid).set(worker_data, merge=True)
    else:
        worker_data["rating"] = 0.0
        worker_data["total_jobs_done"] = 0
        worker_data["is_available"] = True
        worker_data["created_at"] = SERVER_TIMESTAMP
        db.collection("users").document(uid).set(worker_data)

    # Remove non-serializable Sentinel before returning
    worker_data.pop("created_at", None)
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

    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    provider_data = {
        "uid": uid,
        "role": "provider",
        "name": data.name,
        "phone": data.phone,
        "pin_code": data.pin_code,
        "address": data.address,
        "profile_image_url": data.profile_image_url,
    }

    if existing.exists:
        existing_data = existing.to_dict()
        if "total_jobs_posted" not in existing_data:
            provider_data["total_jobs_posted"] = 0
            provider_data["rating"] = 0.0
            
        db.collection("users").document(uid).set(provider_data, merge=True)
    else:
        provider_data["rating"] = 0.0
        provider_data["total_jobs_posted"] = 0
        provider_data["created_at"] = SERVER_TIMESTAMP
        db.collection("users").document(uid).set(provider_data)

    # Remove non-serializable Sentinel before returning
    provider_data.pop("created_at", None)
    return {"message": "Provider registered successfully", "uid": uid, "profile": provider_data}

def switch_role(target_role: str, token_claims: dict) -> dict:
    """Switch the active role of a user between 'worker' and 'provider'."""
    if target_role not in ["worker", "provider"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'worker' or 'provider'.")
        
    uid = token_claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="UID missing in token")

    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    doc_ref = db.collection("users").document(uid)
    existing = doc_ref.get()
    if not existing.exists:
        raise HTTPException(status_code=404, detail="User not found")
        
    existing_data = existing.to_dict()
    
    if target_role == "worker" and "skills" not in existing_data:
        raise HTTPException(status_code=400, detail="Cannot switch to worker. Please register as a worker first.")
    if target_role == "provider" and "total_jobs_posted" not in existing_data:
         raise HTTPException(status_code=400, detail="Cannot switch to provider. Please register as a provider first.")
         
    doc_ref.update({"role": target_role})
    return {"message": f"Successfully switched to {target_role} mode", "role": target_role}


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


def update_user(user_id: str, user_data: dict, token_claims: dict) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'users').document(user_id)
        existing = doc_ref.get()
        if not existing.exists:
            raise HTTPException(status_code=404, detail="User not found")

        # Force phone/email from Firebase token if present
        if token_claims.get("phone_number"):
            user_data["phone"] = token_claims.get("phone_number")
        if token_claims.get("email"):
            user_data["email"] = token_claims.get("email")

        # Merge so only provided fields are updated
        doc_ref.set(user_data, merge=True)

        updated = doc_ref.get().to_dict()
        updated["id"] = user_id
        return updated
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
