from pydantic import BaseModel
from typing import Optional, List

# This defines what a Worker profile looks like
class WorkerCreate(BaseModel):
    name: str
    phone: str
    pin_code: str
    skills: List[str] = []   # e.g. ["cleaning", "grocery"]
    bio: Optional[str] = ""
    profile_image_url: Optional[str] = None

class WorkerUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    pin_code: Optional[str]
    skills: Optional[List[str]]
    bio: Optional[str]
    is_available: Optional[bool]
    profile_image_url: Optional[str] = None
