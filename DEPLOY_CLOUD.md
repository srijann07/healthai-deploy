# HealthAI — Unified Supabase Cloud Deployment & Evaluation Guide

This guide gives you the exact step-by-step instructions to connect **HealthAI** to **Supabase** (for both your Cloud Database & Cloud Object Storage in a single dashboard) and deploy the Backend on **Render** (free HTTPS).

---

## 🏛️ What You Show Your Evaluator (Unified Cloud Architecture)

In a single browser window on **Supabase** (`https://supabase.com/dashboard/project/...`), you can show:
1. **Table Editor (DBaaS)**: All 11 tables (`users`, `patients`, `doctors`, `predictions`, `medical_reports`, `phone_otps`, etc.) updating in real-time.
2. **Storage Bucket (BaaS)**: The `medical-reports` bucket showing uploaded patient medical PDFs, images, sizes, and timestamps.
3. **Database Schema Visualizer**: Interactive ER diagrams showing relational tables and foreign keys.

---

## 📋 What to Do from Your Side (Step-by-Step)

### Step 1: Create a Free Supabase Project

1. Go to **[https://supabase.com](https://supabase.com)** and sign up / log in with your GitHub account.
2. Click **New Project**:
   - **Name**: `healthai-cloud`
   - **Database Password**: Choose a strong password and save it somewhere safe (e.g. `HealthAi@2026!`).
   - **Region**: Choose `ap-south-1` (Mumbai) or Singapore / closest region.
   - Click **Create new project** (takes ~1-2 minutes to provision).

---

### Step 2: Create the Storage Bucket in Supabase

1. In your Supabase project menu on the left, click **Storage** (bucket icon).
2. Click **New Bucket**:
   - **Bucket name**: `medical-reports`
   - **Public bucket**: Toggle **ON** (so files can be previewed/downloaded by patients & doctors).
3. Click **Save**.

---

### Step 3: Get Your Credentials from Supabase

1. Click the **Gear icon (Project Settings)** at the bottom left:
2. Go to **API**:
   - Copy **Project URL** (e.g. `https://xyzprojectref.supabase.co`).
   - Copy **anon / public key** or **service_role key** (under Project API keys).
3. Go to **Database**:
   - Scroll to **Connection string** $\rightarrow$ select **URI**.
   - Copy the URI string:
     ```
     postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
   - Replace `[YOUR-PASSWORD]` with the actual database password you created in Step 1.

---

### Step 4: Test Cloud Connection Locally & Seed Demo Data

In your project folder on your computer, open your `.env` file (or create it from `.env.example`) and add your Supabase keys:

```ini
# 1. Cloud Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres.yourref:your_password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# 2. Cloud Storage (Supabase Storage)
STORAGE_PROVIDER=supabase
SUPABASE_URL=https://yourref.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_role_key
SUPABASE_STORAGE_BUCKET=medical-reports

# 3. Security Keys
SECRET_KEY=healthai-super-secret-key-32-chars-minimum
JWT_SECRET_KEY=healthai-jwt-secret-key-32-chars-minimum
```

Now run the seeding script in PowerShell:

```powershell
# Creates all 11 tables directly in your Supabase Cloud Database:
venv\Scripts\python.exe seed.py

# Seeds demo patient (+919876543210) and demo doctor accounts:
venv\Scripts\python.exe seed_demo_users.py
```

👉 **Check Supabase**: Go to **Table Editor** on your Supabase dashboard — you will immediately see all 11 tables populated with the demo accounts!

---

### Step 5: Deploy the Web Backend to Render (Free HTTPS)

1. Push this project to your **GitHub** repository.
2. Go to **[https://render.com](https://render.com)** and sign in with GitHub.
3. Click **New +** $\rightarrow$ **Web Service** $\rightarrow$ connect your `healthai` repository.
4. Settings:
   - **Name**: `healthai-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:application`
5. Under **Environment Variables**, add the exact same variables from Step 4:
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = `your-secret-key`
   - `JWT_SECRET_KEY` = `your-jwt-key`
   - `DATABASE_URL` = `postgresql://postgres.xxx...` (from Supabase)
   - `STORAGE_PROVIDER` = `supabase`
   - `SUPABASE_URL` = `https://yourref.supabase.co`
   - `SUPABASE_KEY` = `your_supabase_key`
   - `SUPABASE_STORAGE_BUCKET` = `medical-reports`
6. Click **Deploy Web Service**. You will receive a live URL: `https://healthai-backend.onrender.com`.

---

## 👨‍🏫 What to Show During Your Presentation / Viva

Have two browser windows side-by-side:

### Window 1: Live Web App (`https://healthai-backend.onrender.com`)
1. **Login with Indian Mobile OTP**:
   - Go to `/login`, select **Mobile OTP (+91)**, enter `9876543210`, and enter the OTP.
2. **AI Health Risk Check**:
   - Run a symptom assessment, show the AI risk score and doctor assignment.
3. **Medical Report Upload**:
   - Go to **My Health Reports** $\rightarrow$ Upload a sample medical PDF or report image.

### Window 2: Supabase Dashboard
1. **Table Editor**:
   - Open `users`, `predictions`, `phone_otps` — show that new records are inserted live into the PostgreSQL cloud database.
2. **Storage Bucket**:
   - Open **Storage** $\rightarrow$ `medical-reports` — show the uploaded patient PDF file stored directly in the cloud bucket with download/preview capability.
3. **Schema Visualizer**:
   - Open **Database** $\rightarrow$ **Schema Visualizer** to show the complete relational architecture to your professors!
