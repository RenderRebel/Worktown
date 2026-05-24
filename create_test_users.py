"""
create_test_users.py
====================
Creates Firebase Auth users + Firestore documents that match your
user_services.py schema (worker & provider roles).

Usage:
    python create_test_users.py create   # create auth + firestore docs
    python create_test_users.py list     # print all test users + their data
    python create_test_users.py tokens   # print ID tokens (for Postman/curl)
    python create_test_users.py delete   # remove auth + firestore docs
"""

import os
import sys
import json
import requests
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# ─────────────────────────────────────────────
# CONFIG  ← fill these two values
# ─────────────────────────────────────────────
SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"   # path to your service account JSON
FIREBASE_WEB_API_KEY  = "AIzaSyAzKhGHmBxZ9mVppLvhIPWZFQqVOhlpBEs"         # Firebase Console → Project Settings → General → Web API Key

# ─────────────────────────────────────────────
# TEST USERS  (edit freely)
# ─────────────────────────────────────────────
TEST_USERS = [

    # ── WORKERS ──────────────────────────────
    {
        "email":    "worker1@test.com",
        "password": "Test@1234",
        "display_name": "Alice Worker",
        "role": "worker",
        "firestore": {
            "name":     "Alice Worker",
            "phone":    "+911234567890",
            "pin_code": "226001",
            "skills":   ["plumbing", "electrical"],
            "bio":      "Experienced plumber with 5 years of work.",
            "profile_image_url": "",
            "total_jobs_done":   0,
            "rating":            0.0,
            "is_available":      True,
        }
    },
    {
        "email":    "worker2@test.com",
        "password": "Test@1234",
        "display_name": "Bob Worker",
        "role": "worker",
        "firestore": {
            "name":     "Bob Worker",
            "phone":    "+911234567891",
            "pin_code": "226001",
            "skills":   ["painting", "carpentry"],
            "bio":      "Professional painter and carpenter.",
            "profile_image_url": "",
            "total_jobs_done":   3,
            "rating":            4.2,
            "is_available":      False,
        }
    },

    # ── PROVIDERS ────────────────────────────
    {
        "email":    "provider1@test.com",
        "password": "Test@1234",
        "display_name": "Carol Provider",
        "role": "provider",
        "firestore": {
            "name":     "Carol Provider",
            "phone":    "+911234567892",
            "pin_code": "226001",
            "address":  "12 MG Road, Lucknow, UP",
            "profile_image_url": "",
            "total_jobs_posted": 0,
            "rating":            0.0,
        }
    },
    {
        "email":    "provider2@test.com",
        "password": "Test@1234",
        "display_name": "Dave Provider",
        "role": "provider",
        "firestore": {
            "name":     "Dave Provider",
            "phone":    "+911234567893",
            "pin_code": "226010",
            "address":  "45 Hazratganj, Lucknow, UP",
            "profile_image_url": "",
            "total_jobs_posted": 5,
            "rating":            3.8,
        }
    },

    # ── DUAL ROLE (worker first, can switch to provider) ──
    {
        "email":    "dualrole@test.com",
        "password": "Test@1234",
        "display_name": "Eve Dual",
        "role": "worker",                        # current active role
        "firestore": {
            "name":     "Eve Dual",
            "phone":    "+911234567894",
            "pin_code": "226001",
            # worker fields
            "skills":   ["cleaning", "cooking"],
            "bio":      "Multi-skilled worker.",
            "total_jobs_done":   1,
            "rating":            4.5,
            "is_available":      True,
            # provider fields (already registered both sides)
            "address":  "99 Indira Nagar, Lucknow, UP",
            "total_jobs_posted": 2,
            "profile_image_url": "",
        }
    },
]


# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────
def create_test_users():
    db = init_firebase()
    print("\n🚀 Creating test users...\n")
    created_count = 0

    for u in TEST_USERS:
        email = u["email"]

        # ── 1. Firebase Auth ──
        try:
            fb_user = auth.create_user(
                email=email,
                password=u["password"],
                display_name=u["display_name"],
                email_verified=True,        # skip email verification in tests
            )
            uid = fb_user.uid
            print(f"✅ Auth created : {email}  (uid={uid})")
        except auth.EmailAlreadyExistsError:
            fb_user = auth.get_user_by_email(email)
            uid = fb_user.uid
            print(f"⚠️  Auth exists  : {email}  (uid={uid}) — skipping auth creation")
        except Exception as e:
            print(f"❌ Auth failed  : {email} — {e}")
            continue

        # ── 2. Custom claim (role) ──
        try:
            auth.set_custom_user_claims(uid, {"role": u["role"]})
        except Exception as e:
            print(f"   ⚠️  Could not set custom claim: {e}")

        # ── 3. Firestore document ──
        doc_data = {
            **u["firestore"],
            "uid":   uid,
            "email": email,
            "role":  u["role"],
            "created_at": SERVER_TIMESTAMP,
        }
        try:
            db.collection("users").document(uid).set(doc_data)
            print(f"   📄 Firestore doc written (role={u['role']})\n")
            created_count += 1
        except Exception as e:
            print(f"   ❌ Firestore write failed: {e}\n")

    print(f"Done — {created_count}/{len(TEST_USERS)} users ready.\n")


# ─────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────
def list_test_users():
    db = init_firebase()
    print("\n📋 Listing test users...\n")

    for u in TEST_USERS:
        email = u["email"]
        try:
            fb_user = auth.get_user_by_email(email)
            uid = fb_user.uid
            doc = db.collection("users").document(uid).get()
            fs_data = doc.to_dict() if doc.exists else "❌ No Firestore doc"
            print(f"👤 {email}")
            print(f"   UID      : {uid}")
            print(f"   Role     : {u['role']}")
            print(f"   Claims   : {fb_user.custom_claims}")
            print(f"   Firestore: {json.dumps({k: v for k, v in (fs_data or {}).items() if k != 'created_at'}, indent=6, default=str)}\n")
        except auth.UserNotFoundError:
            print(f"❌ Not found in Firebase Auth: {email}\n")
        except Exception as e:
            print(f"❌ Error for {email}: {e}\n")


# ─────────────────────────────────────────────
# TOKENS  (for Postman / curl testing)
# ─────────────────────────────────────────────
def get_id_token(email: str, password: str) -> str:
    url = (
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_WEB_API_KEY}"
    )
    res = requests.post(url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }, timeout=10)
    data = res.json()
    if "idToken" not in data:
        return f"ERROR: {data.get('error', {}).get('message', 'unknown')}"
    return data["idToken"]


def print_tokens():
    if FIREBASE_WEB_API_KEY == "YOUR_WEB_API_KEY":
        print("❌ Set FIREBASE_WEB_API_KEY in this script first.\n")
        return

    print("\n🔑 Fetching ID tokens...\n")
    for u in TEST_USERS:
        token = get_id_token(u["email"], u["password"])
        short = token[:60] + "..." if len(token) > 60 else token
        print(f"📧 {u['email']}  [{u['role']}]")
        print(f"   Token: {short}\n")
        print(f'   curl: curl -H "Authorization: Bearer {token}" http://localhost:8000/v1/users/me\n')


# ─────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────
def delete_test_users():
    db = init_firebase()
    print("\n🗑️  Deleting test users...\n")

    for u in TEST_USERS:
        email = u["email"]
        try:
            fb_user = auth.get_user_by_email(email)
            uid = fb_user.uid

            # Delete Firestore doc
            db.collection("users").document(uid).delete()
            print(f"   📄 Firestore doc deleted")

            # Delete Auth user
            auth.delete_user(uid)
            print(f"✅ Auth deleted : {email}\n")

        except auth.UserNotFoundError:
            print(f"⚠️  Not found   : {email} — skipping\n")
        except Exception as e:
            print(f"❌ Error        : {email} — {e}\n")

    print("Cleanup complete.\n")


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────
COMMANDS = {
    "create": create_test_users,
    "list":   list_test_users,
    "tokens": print_tokens,
    "delete": delete_test_users,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    if cmd not in COMMANDS:
        print(f"Unknown command '{cmd}'. Choose from: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[cmd]()