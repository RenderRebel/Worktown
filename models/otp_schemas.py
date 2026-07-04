from pydantic import BaseModel, Field


class SendOtpRequest(BaseModel):
    phone: str = Field(
        ...,
        pattern=r"^\d{10,15}$",
        description="Phone number with country code (no + or spaces)",
    )


class VerifyOtpRequest(BaseModel):
    phone: str = Field(
        ...,
        pattern=r"^\d{10,15}$",
        description="Phone number with country code (no + or spaces)",
    )
    code: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


class OtpResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None
