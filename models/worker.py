from pydantic import BaseModel, Field
from typing import Optional, List

# This defines what a Worker profile looks like
class WorkerCreate(BaseModel):
    name: str
    phone: str = Field(..., pattern=r"^\d{10}$", description="Phone number must be exactly 10 digits")
    pin_code: int
    skills: List[str] = []   # e.g. ["cleaning", "grocery"]
    bio: Optional[str] = ""
    profile_image_url: Optional[str] = None

class WorkerUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str] = Field(default=None, pattern=r"^\d{10}$", description="Phone number must be exactly 10 digits")
    pin_code: Optional[int] = None
    skills: Optional[List[str]]
    bio: Optional[str]
    is_available: Optional[bool]
    profile_image_url: Optional[str] = None
