from pydantic import BaseModel, Field

class ApplicationCreate(BaseModel):
    job_id: str
    applicant_phone: str = Field(..., pattern=r"^\d{10}$", description="Phone number must be exactly 10 digits")
