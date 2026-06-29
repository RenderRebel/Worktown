from firebase_admin import auth
from fastapi import HTTPException, Header

class UserIdentity(str):
    """
    A custom string subclass representing the user's UID.
    Carries the email_verified flag and yields both when unpacked.
    """
    def __new__(cls, uid: str, email_verified: bool):
        obj = str.__new__(cls, uid)
        obj.email_verified = email_verified
        return obj

    def __iter__(self):
        yield str(self)
        yield self.email_verified

# This function runs before every API call
# It checks the token Flutter sends and returns the user's UID and email verification status
async def verify_token(authorization: str = Header(...)):
    try:
        # Token comes as "Bearer xxxxx", we remove "Bearer " and any whitespace
        token = authorization.replace("Bearer ", "").strip()

        # Firebase checks if this token is real and valid
        decoded = auth.verify_id_token(token)

        # Return the UserIdentity containing UID and email_verified status
        return UserIdentity(decoded["uid"], decoded.get("email_verified", False))

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token. Details: {str(e)}")

