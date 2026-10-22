---
title: HealthAI
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HealthAI — AI-Powered Early Health Risk Detection System

HealthAI is a full-stack web application for early health-risk screening. It combines patient-reported symptoms and health information with an AI-assisted assessment workflow, then routes results to doctors for review.

> **Medical disclaimer:** HealthAI is a screening and educational tool, not a substitute for professional medical diagnosis or treatment.

## Core Features

### Patient workflow
- Secure registration and login
- Profile and health-information management
- Symptom and vital-input assessment
- Prediction/history view
- Medical-report uploads
- Appointment requests
- PDF report generation

### Doctor workflow
- Assigned-patient management
- AI assessment review
- Approve/reject workflow
- Medical notes and recommendations
- Appointment management
- Search and risk-based filtering

### Admin workflow
- Platform dashboard
- Patient and doctor management
- Role/account administration
- File oversight
- Security/audit visibility

## AI / Assessment Engine

The assessment flow combines reported symptoms with saved health and lifestyle information to produce a risk level and supporting recommendations. Predictions are stored and routed for doctor verification rather than presented as a definitive diagnosis.

## Architecture

```text
Browser
   │
   ▼
Flask application
   ├── Routes / controllers
   ├── Services / validation
   ├── Role-based middleware
   ├── SQLAlchemy data layer
   └── AI assessment module
        │
        ├── MySQL / SQLite (development)
        └── Stored prediction + review workflow
```

## Tech Stack

**Backend:** Python, Flask, SQLAlchemy  
**Auth & Security:** JWT, bcrypt, CSRF protection, role-based access control  
**Database:** MySQL with SQLite development fallback  
**AI/Data:** scikit-learn, Pandas, NumPy, Joblib  
**Frontend:** Jinja2, HTML/CSS, Bootstrap 5, JavaScript, Chart.js  
**Reports:** ReportLab  
**Testing:** pytest  
**Deployment:** Docker, WSGI, Render configuration

## Repository Structure

```text
controllers/      Request and response handling
dataset/          Training / project data
ml/               AI assessment and model-related code
models/           Database models
middlewares/      Authentication and role checks
routes/           Application routes
services/         Business logic
static/           CSS / JavaScript / assets
templates/        Web UI templates
app.py            Application entry point
config.py         Environment configuration
Dockerfile        Container build configuration
render.yaml       Deployment configuration
wsgi.py           WSGI entry point
```

## Local Setup

### 1. Clone

```bash
git clone https://github.com/srijann07/healthai-deploy.git
cd healthai-deploy
```

### 2. Create an environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\\Scripts\\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and set the required values for your local environment.

### 5. Initialize and run

```bash
python seed.py
python app.py
```

## Testing

```bash
python -m pytest tests -v
```

## Deployment

The repository includes a `Dockerfile`, `wsgi.py`, and `render.yaml` for deployment-oriented workflows. See [`DEPLOY_CLOUD.md`](DEPLOY_CLOUD.md) for cloud deployment notes.

## Security Notes

- Do not commit `.env` files or real credentials.
- Uploaded patient files and local databases should remain outside version control.
- Demo credentials, when used locally, are for development only.

## Project Status

This is an academic portfolio project showing the progression from prototype to deployable full-stack application.

## Author

**Srijan Sangroula**  
BCA student · Software Development · AI/ML · Data · Cloud

[Portfolio](https://srijann07.github.io/my-website/)
