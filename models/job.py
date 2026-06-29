from pydantic import BaseModel
from typing import Optional

class JobCreate(BaseModel):
    title: str
    description: str
    category: str    # "household", "eldercare", "delivery", "other"
    pin_code: str
    address: Optional[str] = None
    pay: int         # e.g. "₹200"

class JobUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    category: Optional[str]
    address: Optional[str] = None
    pay: Optional[str]
