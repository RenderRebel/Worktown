from fastapi import HTTPException
from typing import List, Optional
from models.schemas import job, jobCreate
from core.database import get_db


def create_job(job_data: jobCreate) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = job_data.dict()
    try:
        _, doc_ref = db.collection(u'jobs').add(data)
        data["id"] = doc_ref.id
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add job: {str(e)}")


def get_jobs(
    pincode: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> List[dict]:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    ref = db.collection(u'jobs')
    if pincode:
        ref = ref.where(u'pincode', u'==', pincode)
    if category:
        ref = ref.where(u'category', u'==', category)
    if status:
        ref = ref.where(u'status', u'==', status)

    try:
        docs = ref.stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")


def get_job(job_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc = db.collection(u'jobs').document(job_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Job not found")
        return {**doc.to_dict(), "id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job: {str(e)}")


def update_job(job_id: str, job_data: jobCreate) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'jobs').document(job_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Job not found")
        data = job_data.dict()
        doc_ref.set(data)
        data["id"] = job_id
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")


def delete_job(job_id: str) -> dict:
    try:
        db = get_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        doc_ref = db.collection(u'jobs').document(job_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Job not found")
        doc_ref.delete()
        return {"message": f"Job {job_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")
