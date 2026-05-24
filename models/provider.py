from pydantic import BaseModel, Field
from typing import Optional

class ProviderCreate(BaseModel):
    name: str
    phone: str = Field(..., pattern=r"^\d{10}$", description="Phone number must be exactly 10 digits")
    pin_code: int
    address: Optional[str] = ""
    profile_image_url: Optional[str] = None

class ProviderUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str] = Field(default=None, pattern=r"^\d{10}$", description="Phone number must be exactly 10 digits")
    pin_code: Optional[int] = None
    address: Optional[str]
    profile_image_url: Optional[str] = None
