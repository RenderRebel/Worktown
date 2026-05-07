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
