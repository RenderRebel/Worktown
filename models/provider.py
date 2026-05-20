from pydantic import BaseModel
from typing import Optional

class ProviderCreate(BaseModel):
    name: str
    phone: str
    pin_code: str
    address: Optional[str] = ""
    profile_image_url: Optional[str] = None

class ProviderUpdate(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    pin_code: Optional[str]
    address: Optional[str]
    profile_image_url: Optional[str] = None
