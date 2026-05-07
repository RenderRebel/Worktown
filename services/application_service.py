from fastapi import HTTPException
from typing import List, Optional
from models.schemas import Application, ApplicationCreate
from core.database import get_db


def create_application(application: ApplicationCreate) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = application.dict()
    data["applied_at"] = data["applied_at"].isoformat()

    try:
        _, doc_ref = db.collection(u'applications').add(data)
        data["app_id"] = doc_ref.id
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit application: {str(e)}")


def get_applications(
    job_id: Optional[str] = None,
    application_uid: Optional[str] = None,
    status: Optional[str] = None,
) -> List[dict]:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ref = db.collection(u'applications')
    if job_id:
        ref = ref.where(u'job_id', u'==', job_id)
    if application_uid:
        ref = ref.where(u'application_uid', u'==', application_uid)
    if status:
        ref = ref.where(u'status', u'==', status)

    try:
        docs = ref.stream()
        return [{**doc.to_dict(), "app_id": doc.id} for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch applications: {str(e)}")


def get_application(app_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc = db.collection(u'applications').document(app_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Application not found")
        return {**doc.to_dict(), "app_id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch application: {str(e)}")


def update_application(app_id: str, updates: dict) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'applications').document(app_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Application not found")
        doc_ref.update(updates)
        d = doc_ref.get().to_dict()
        d["app_id"] = app_id
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update application: {str(e)}")


def delete_application(app_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'applications').document(app_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Application not found")
        doc_ref.delete()
        return {"message": f"Application {app_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete application: {str(e)}")
