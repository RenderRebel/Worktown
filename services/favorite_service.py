from fastapi import HTTPException
from typing import List, Optional
from models.schemas import Favorite, FavoriteCreate
from core.database import get_db


def add_favorite(favorite: FavoriteCreate) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Prevent duplicate favourites
    try:
        existing = (
            db.collection(u'favorites')
            .where(u'user_id',   u'==', favorite.user_id)
            .where(u'item_type', u'==', favorite.item_type)
            .where(u'item_id',   u'==', favorite.item_id)
            .stream()
        )
        if any(True for _ in existing):
            raise HTTPException(status_code=409, detail="Item is already in favourites")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check duplicates: {str(e)}")

    try:
        data = favorite.dict()
        _, doc_ref = db.collection(u'favorites').add(data)
        data["id"] = doc_ref.id
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add favourite: {str(e)}")


def get_favorites(user_id: str, item_type: Optional[str] = None) -> List[dict]:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ref = db.collection(u'favorites').where(u'user_id', u'==', user_id)
    if item_type:
        ref = ref.where(u'item_type', u'==', item_type)

    try:
        docs = ref.stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch favourites: {str(e)}")


def get_favorite(favorite_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc = db.collection(u'favorites').document(favorite_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Favourite not found")
        return {**doc.to_dict(), "id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch favourite: {str(e)}")


def remove_favorite(favorite_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'favorites').document(favorite_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Favourite not found")
        doc_ref.delete()
        return {"message": f"Favourite {favorite_id} removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove favourite: {str(e)}")
