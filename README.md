# Worktown Backend API

A robust backend service for **Worktown**, a localized service marketplace built with **FastAPI** and **Firebase**. The application connects **Providers** (people who post jobs) with **Workers** (people looking to complete jobs locally).

---

## 🚀 Features

* **Dual User Roles**: Support for both `Worker` and `Provider` profiles.
* **Firebase Authentication**: Fully secured endpoints utilizing Firebase JWT Tokens.
* **Firestore Database**: Real-time NoSQL database integration using Google Cloud Firestore.
* **Job Application Lifecycle**: Comprehensive state management for jobs:
  - `open` ➔ `assigned` ➔ `arriving` ➔ `in_progress` ➔ `pending_confirm` ➔ `completed`
   * **Dockerized**: Includes a `Dockerfile` for seamless deployment to any cloud provider.
* **CI/CD Ready**: Configured with GitHub Actions for automated testing and image building.

---

## 🛠️ Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
* **Database:** Google Cloud Firestore
* **Authentication:** Firebase Admin SDK (JWT Validation)
* **Server:** Uvicorn
* **Containerization:** Docker

---

## 💻 Local Development Setup

### 1. Clone and Install Dependencies

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository (if applicable)
git clone <repository_url>
cd dream_app

# Create and activate a virtual environment
python -m venv myenv

# Windows
myenv\Scripts\activate
# Mac/Linux
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory (this file is ignored by Git):

```env
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

### 3. Setup Firebase Service Account

To communicate with Firestore and verify tokens, you need a Firebase Service Account key.

1. Go to your [Firebase Console](https://console.firebase.google.com/).
2. Navigate to **Project Settings** > **Service Accounts**.
3. Click **Generate new private key** and download the JSON file.
4. Rename the downloaded file to `serviceAccountKey.json` and place it in the root directory of this project.

> ⚠️ **IMPORTANT:** Never commit `serviceAccountKey.json` or `.env` to version control. They are already listed in `.gitignore`.

### 4. Run the Server

Start the development server using Uvicorn:

```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`.
You can view the auto-generated Swagger UI Documentation at `http://127.0.0.1:8000/docs`.

---

## 🐳 Docker Deployment

You can build and run the application locally using Docker:

```bash
# Build the Docker image
docker build -t nearhelp-api .

# Run the container (Make sure serviceAccountKey.json is in the directory)
docker run -p 8000:8000 nearhelp-api
```

---

## 🔑 Generating a Test Token

For local testing without the Flutter frontend, you can use the provided script to log in as a test user and get a valid Firebase JWT Token.

1. Edit `generate_test_token.py` and insert your Firebase Web API Key and test user credentials.
2. Run the script:
   ```bash
   python generate_test_token.py
   ```
3. Copy the outputted `eyJ...` token.
4. Go to `http://127.0.0.1:8000/docs`, click **Authorize**, and paste your token in this format:
   `Bearer <your_token_here>`

---

## 📚 Core Application Flow

### As a Provider
1. Register Profile (`POST /auth/register/provider`)
2. Post a Job (`POST /jobs/`)
3. Approve an Application (`PATCH /applications-v2/{app_id}/approve`)
4. Confirm Worker Arrival (`PATCH /applications-v2/{app_id}/confirm-arrival`)
5. Confirm Job Completion (`PATCH /applications-v2/{app_id}/confirm-done`)

### As a Worker
1. Register Profile (`POST /auth/register/worker`)
2. Browse Open Jobs (`GET /jobs/pincode/{pin_code}`)
3. Apply for a Job (`POST /applications-v2/`)
4. Cancel an Application (`PATCH /applications-v2/{app_id}/cancel`)
5. Signal Arrival (`PATCH /applications-v2/{app_id}/worker-arriving`)
6. Mark Job as Done (`PATCH /applications-v2/{app_id}/worker-done`)
