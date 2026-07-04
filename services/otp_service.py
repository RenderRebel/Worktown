import os
import random
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from firebase_admin import auth as firebase_auth
from firebase_config import db


# ── Constants ─────────────────────────────────────────────────────────────────
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RATE_LIMIT_SECONDS = 60

TWOFACTOR_API_KEY = os.getenv("TWOFACTOR_API_KEY")


# ── Phone Formatting Helper ───────────────────────────────────────────────────
def _get_db_phone(phone: str) -> str:
    """Helper to convert country-code prefixed phone to 10-digit format for users collection."""
    if len(phone) == 12 and phone.startswith("91"):
        return phone[2:]
    return phone


# ── Rate Limiting & Lockout Check ─────────────────────────────────────────────
def check_rate_limit(phone: str) -> None:
    """
    Enforce max 1 OTP send request per 60 seconds per phone number.
    Uses the `created_at` field in the existing otp_sessions record.
    Also raises lockout error if user is locked out.
    """
    doc_ref = db.collection("otp_sessions").document(phone)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        now = datetime.now(timezone.utc)

        # Check lockout first
        locked_until = data.get("locked_until")
        if locked_until:
            if now < locked_until:
                remaining = int((locked_until - now).total_seconds() // 60) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many failed attempts. Try again in {remaining} minutes.",
                )
            else:
                # Lockout period expired — delete the document to reset
                doc_ref.delete()
                return

        created_at = data.get("created_at")
        if created_at:
            diff = (now - created_at).total_seconds()
            if diff < RATE_LIMIT_SECONDS:
                wait = int(RATE_LIMIT_SECONDS - diff)
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {wait} seconds before requesting another OTP",
                )


# ── Store OTP Session in Firestore ────────────────────────────────────────────
def store_session(phone: str, session_id: str) -> None:
    """Write OTP session record to Firestore under `otp_sessions/{phone}`."""
    now = datetime.now(timezone.utc)
    db.collection("otp_sessions").document(phone).set({
        "session_id": session_id,
        "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0,
        "created_at": now,
    })


# ── Send OTP via 2Factor ─────────────────────────────────────────────────────
async def send_otp_via_2factor(phone: str) -> str:
    """
    Send OTP to the given phone number using 2Factor AUTOGEN route.
    Returns the session_id on success, raises HTTPException on failure.
    """
    if not TWOFACTOR_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="2Factor API key not configured",
        )

    url = f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/{phone}/AUTOGEN/LoginOTP"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            data = response.json()

            if data.get("Status") == "Success":
                return data.get("Details")
            else:
                detail = data.get("Details", "SMS sending failed")
                raise HTTPException(status_code=502, detail=f"2Factor error: {detail}")

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach 2Factor: {str(e)}",
            )


# ── Verify OTP via 2Factor ───────────────────────────────────────────────────
async def verify_otp_via_2factor(phone: str, code: str) -> None:
    """
    Verify the OTP code for the given phone number using 2Factor VERIFY route.
    Looks up Firestore session doc, checks lockout and expiry, increments attempts,
    locks out if limit reached. Deletes session doc on success.
    """
    doc_ref = db.collection("otp_sessions").document(phone)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="No OTP found for this number. Please request a new one.")

    data = doc.to_dict()
    now = datetime.now(timezone.utc)

    # Check lockout
    locked_until = data.get("locked_until")
    if locked_until:
        if now < locked_until:
            remaining = int((locked_until - now).total_seconds() // 60) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Try again in {remaining} minutes.",
            )
        else:
            # Lockout period expired — delete stale record
            doc_ref.delete()
            raise HTTPException(
                status_code=404,
                detail="OTP expired. Please request a new one.",
            )

    # Check expiry
    expires_at = data.get("expires_at")
    if expires_at and now > expires_at:
        doc_ref.delete()
        raise HTTPException(status_code=410, detail="OTP has expired. Please request a new one.")

    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session data. Please request a new OTP.")

    if not TWOFACTOR_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="2Factor API key not configured",
        )

    url = f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/VERIFY/{session_id}/{code}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            verify_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach 2Factor for verification: {str(e)}",
            )

    is_matched = (verify_data.get("Status") == "Success") and (verify_data.get("Details") == "OTP Matched")

    if is_matched:
        # Success — delete the OTP record
        doc_ref.delete()
        return

    # Increment attempts on failure
    attempts = data.get("attempts", 0) + 1
    if attempts >= MAX_ATTEMPTS:
        # Lockout for 15 minutes
        locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        doc_ref.update({
            "attempts": attempts,
            "locked_until": locked_until
        })
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.",
        )
    else:
        doc_ref.update({"attempts": attempts})
        remaining = MAX_ATTEMPTS - attempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP code. {remaining} attempts remaining.",
        )


# ── Mark Phone Verified ──────────────────────────────────────────────────────
def mark_phone_verified(phone: str) -> str | None:
    """
    Find the user document by phone number and set phone_verified = True.
    Returns the user's UID if found, None otherwise.
    """
    db_phone = _get_db_phone(phone)
    users_ref = db.collection("users")
    query = users_ref.where("phone", "==", db_phone).limit(1).get()

    for doc in query:
        doc.reference.update({"phone_verified": True})
        return doc.id

    return None


# ── Create Firebase Custom Token ─────────────────────────────────────────────
def create_session_token(phone: str) -> str:
    """
    Find or create a Firebase user for this phone number and issue a custom token.
    This token can be used with FirebaseAuth.signInWithCustomToken() on the client.
    """
    db_phone = _get_db_phone(phone)

    # First try to find an existing user by phone in Firestore
    users_ref = db.collection("users")
    query = users_ref.where("phone", "==", db_phone).limit(1).get()

    uid = None
    for doc in query:
        uid = doc.id
        break

    if uid is None:
        # No existing user — create a placeholder that will be completed during
        # registration. Use a deterministic UID based on phone for consistency.
        uid = f"phone_{db_phone}"
        db.collection("users").document(uid).set({
            "uid": uid,
            "email": "",
            "name": "",
            "phone": db_phone,
            "created_at": datetime.now(timezone.utc),
            "pin_code": "",
            "role": "",
            "profile_image_url": "",
            "rating": 0.0,
            "total_jobs_done": 0,
            "total_jobs_posted": 0,
            "skills": [],
            "bio": "",
            "address": "",
            "is_available": True,
            "phone_verified": True,
        })

    # Create Firebase Auth user if not exists, then issue custom token
    try:
        firebase_auth.get_user(uid)
    except firebase_auth.UserNotFoundError:
        formatted_phone = phone if phone.startswith("+") else f"+{phone}"
        if len(phone) == 10:
            formatted_phone = f"+91{phone}"
        firebase_auth.create_user(uid=uid, phone_number=formatted_phone)

    custom_token = firebase_auth.create_custom_token(uid)
    return custom_token.decode("utf-8") if isinstance(custom_token, bytes) else custom_token
