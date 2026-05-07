import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

# This connects your backend to Firebase using your secret key
cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)

# Initialize app only if not already initialized to prevent errors
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# This gives you access to Firestore database
db = firestore.client()
