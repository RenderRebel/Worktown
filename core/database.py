import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin
def initialize_firebase():
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
        try:
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully.")
            else:
                print(f"Firebase credentials not found at {cred_path}. Firestore will not work.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            print("Ensure FIREBASE_CREDENTIALS_PATH is set correctly or serviceAccountKey.json exists.")

# Get Firestore DB instance
def get_db():
    try:
        return firestore.client()
    except ValueError:
        raise Exception("Firebase app not initialized. Please configure credentials.")
