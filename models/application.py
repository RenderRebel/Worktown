from pydantic import BaseModel

class ApplicationCreate(BaseModel):
    job_id: str
    applicant_phone: str   # worker's phone, sent with every application
