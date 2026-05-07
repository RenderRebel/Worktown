from firebase_admin import auth
from fastapi import HTTPException, Header

# This function runs before every API call
# It checks the token Flutter sends and returns the user's UID
async def verify_token(authorization: str = Header(...)):
    try:
        # Token comes as "Bearer xxxxx", we remove "Bearer " and any whitespace
        token = authorization.replace("Bearer ", "").strip()

        # Firebase checks if this token is real and valid
        decoded = auth.verify_id_token(token)

        # Return the UID of whoever is making the request
        return decoded["uid"]

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token. Details: {str(e)}")
