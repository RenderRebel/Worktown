import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Priority 1: JSON string from environment variable (for Render / cloud deployments)
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully from FIREBASE_CREDENTIALS_JSON.")
                return

            # Priority 2: File path (for local development)
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully from file.")
            else:
                print(f"Firebase credentials not found at {cred_path}. Firestore will not work.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            print("Set FIREBASE_CREDENTIALS_JSON (JSON string) or FIREBASE_CREDENTIALS_PATH (file path).")

# Get Firestore DB instance
def get_db():
    try:
        return firestore.client()
    except ValueError:
        raise Exception("Firebase app not initialized. Please configure credentials.")
