from fastapi import APIRouter
from models.otp_schemas import SendOtpRequest, VerifyOtpRequest, OtpResponse
from services.otp_service import (
    check_rate_limit,
    store_session,
    send_otp_via_2factor,
    verify_otp_via_2factor,
    mark_phone_verified,
    create_session_token,
)

router = APIRouter(prefix="/otp", tags=["OTP"])


# ── Send OTP ──────────────────────────────────────────────────────────────────
@router.post("/send-otp", response_model=OtpResponse)
async def send_otp(data: SendOtpRequest):
    """
    Trigger 2Factor AUTOGEN OTP send, and store the session in Firestore.
    Rate-limited to 1 request per 60 seconds per phone number.
    """
    # 1. Rate limit & lockout check
    check_rate_limit(data.phone)

    # 2. Send via 2Factor AUTOGEN
    session_id = await send_otp_via_2factor(data.phone)

    # 3. Store session in Firestore
    store_session(data.phone, session_id)

    return OtpResponse(
        success=True,
        message="OTP sent successfully",
    )


# ── Verify OTP ────────────────────────────────────────────────────────────────
@router.post("/verify-otp", response_model=OtpResponse)
async def verify_otp_endpoint(data: VerifyOtpRequest):
    """
    Verify the OTP code. On success, marks the user as phone-verified
    and returns a Firebase custom token for client-side sign-in.
    """
    # 1. Verify the OTP (raises HTTPException on failure)
    await verify_otp_via_2factor(data.phone, data.code)

    # 2. Mark user as phone-verified in Firestore
    mark_phone_verified(data.phone)

    # 3. Issue a Firebase custom token
    token = create_session_token(data.phone)

    return OtpResponse(
        success=True,
        message="Phone verified successfully",
        token=token,
    )
