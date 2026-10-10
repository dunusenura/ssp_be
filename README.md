# Smart Service Platform - Backend (Python / Flask)

The backend API for the Smart Service Platform (WorkPub), built with Python, Flask, and MongoDB.

---

## 📁 Directory Structure

```text
Backend/
├── routes/                 # Blueprint API routes (auth, booking, chat, job, payment, review, user)
├── app.py                  # Main Flask application entry point
├── config.py               # Application configurations & environment loader
├── database.py             # MongoDB connection setup
├── seed_db.py              # Database seeding script for sample data
├── whatsapp_gateway.py     # WhatsApp notification gateway
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment template file
├── .env                    # Local environment variables (Ignored in Git)
├── .gitignore              # Git ignore rules for Backend
└── README.md               # Backend documentation
```

---

## ⚙️ Prerequisites

Before getting started, ensure you have installed:
- **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
- **MongoDB**: Local MongoDB server or [MongoDB Atlas Cloud Cluster](https://www.mongodb.com/cloud/atlas)
- **Git**: [Download Git](https://git-scm.com/)

---

## 🚀 Local Development Setup

### Step 1: Navigate to the Backend Folder
```bash
cd Backend
```

### Step 2: Create & Activate Virtual Environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  \.venv\Scripts\Activate.ps1
  ```
- **On Windows (Command Prompt):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  ```
- **On macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the environment template file to `.env`:
- **Windows PowerShell:**
  ```powershell
  Copy-Item .env.example .env
  ```
- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

Edit `.env` and configure your credentials:
```env
PORT=5000
DEBUG=True
SECRET_KEY=your_secure_random_secret_key
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/<dbname>?retryWrites=true&w=majority
ONEPAY_APP_ID=your_onepay_app_id
ONEPAY_APP_TOKEN=your_onepay_app_token
ONEPAY_HASH_TOKEN=your_onepay_hash_token
ONEPAY_API_URL=https://api.onepay.lk/v3/checkout/link/
WHATSAPP_VERIFY_TOKEN=your_whatsapp_verify_token
```

### Step 5: (Optional) Seed the Database
Populate initial sample service categories, users, and jobs:
```bash
python seed_db.py
```

### Step 6: Start Development Server
```bash
python app.py
```
The Flask backend API server will be available at: `http://127.0.0.1:5000`

---

## 🌐 Production Deployment Instructions

### 1. Deployment on Cloud Platforms (Render / Railway / Heroku)

1. **Set Build & Start Commands:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command (Gunicorn WSGI):** `gunicorn app:app` (or `python app.py`)
2. **Add Environment Variables in Platform Settings:**
   Add all key-value pairs from `.env.example` in the platform dashboard.
3. **Configure MongoDB Atlas IP Access:**
   Allow access from `0.0.0.0/0` (or the IP ranges of your cloud provider) in MongoDB Atlas Network Access settings.

### 2. Deployment on Virtual Private Server (Ubuntu / EC2 / DigitalOcean)

1. Clone repository to server and enter backend directory.
2. Setup system python environment and install production WSGI server:
   ```bash
   pip install gunicorn
   ```
3. Run Gunicorn server with systemd or supervisor:
   ```bash
   gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
   ```
4. Configure Nginx reverse proxy to proxy requests from port `80/443` to `http://127.0.0.1:5000`.

---

## 🔒 Security Notes
- Never commit the actual `.env` file to Git.
- Ensure `DEBUG=False` in production.
