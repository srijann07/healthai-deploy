# HealthAI — AI-Powered Early Health Risk Detection System

HealthAI helps users detect possible health risks early by analysing their
symptoms and vitals with machine learning. Patients receive AI risk
assessments that are reviewed and verified by real doctors; admins manage the
whole platform.

> **Medical disclaimer:** HealthAI provides screening guidance only and is not
> a substitute for professional medical diagnosis.

## Features

**Patients** — register and sign in securely, manage their profile and health
information (vitals, blood group, medical history), upload medical reports
(PDF/JPG/PNG), run AI symptom assessments, view prediction history, and
download PDF reports.

**Doctors** — automatically assigned the least-loaded available doctor's
patients (on registration), review assigned patients, verify or reject AI
predictions, add medical notes, recommend tests, medicines and lifestyle
changes, filter patients by risk, keyword and age, and manage appointment
requests (confirm / complete / cancel).

**Admins** — platform dashboard with live statistics, doctor and patient
management, file oversight, account suspension and role management.

**AI module** — `/patient/assess` runs AI health checks: a transparent
rule-based risk engine (versioned: `healthai-rule-engine-v1`) scores the
patient's reported symptoms plus their saved vitals, BMI, age and lifestyle
habits (smoking, alcohol, exercise, history), returning a risk level
(Low/Medium/High/Critical), the most likely condition(s), a recommended
specialist, confidence, urgency and tailored health suggestions. Every
result is saved as a prediction and routed to the patient's assigned doctor
for verification.

## Build status (phased)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Setup, database, authentication, base UI | ✅ Complete |
| 2 | Patient module — profile, health information, medical history, reports | ✅ Complete |
| 3 | Doctor module — patients, review queue, appointments | ✅ Complete |
| 5 | Machine learning — AI health analysis engine (symptoms + habits + vitals) | ✅ Complete |
| 4 | Admin module | 🚧 In progress |
| 6 | Reports, analytics, extra testing, docs | 🚧 In progress |

## Tech stack

Python · Flask · SQLAlchemy · MySQL (SQLite fallback for dev) · JWT
(flask-jwt-extended, cookie + header) · bcrypt · Bootstrap 5 · Chart.js ·
scikit-learn · ReportLab · pytest

## Folder structure

```
backend/
├── app.py                 # Application factory + entry point
├── config.py              # Environment-based configuration
├── extensions.py          # SQLAlchemy / JWT instances
├── seed.py                # Roles + admin/doctor seed script
├── models/                # One file per table (10 tables)
├── routes/                # Blueprint URL wiring
├── controllers/           # Request/response handling
├── services/              # Business logic (auth, validation, audit, ...)
├── middlewares/           # JWT + role-based access decorators
├── templates/             # Jinja2 pages (auth, dashboards, errors)
├── static/                # css / js / images
├── uploads/               # Patient-uploaded files (gitignored)
├── ml/                    # Training code + saved model artifacts
├── dataset/               # Training dataset
└── tests/                 # pytest suite
```

## Getting started

### 1. Install

**Windows (PowerShell)** — run each line separately (`&&` is not supported in Windows PowerShell), and use `py` / the venv's `python.exe` so the Microsoft Store `python` alias doesn't interfere:

```powershell
cd backend
py -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
copy .env.example .env       # then edit values
```

For **MySQL**, create a database and set in `.env`:

```
DATABASE_URL=mysql+pymysql://healthai_user:strong_password@localhost:3306/healthai
```

```sql
CREATE DATABASE healthai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'healthai_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON healthai.* TO 'healthai_user'@'localhost';
```

Leave `DATABASE_URL` empty to use a local SQLite file (development only).

### 3. Seed and run

```powershell
venv\Scripts\python.exe seed.py     # creates tables, roles, admin + demo doctor
venv\Scripts\python.exe app.py      # http://127.0.0.1:5000
```

(On macOS/Linux with the venv activated: `python seed.py` then `python app.py`.)

Default accounts created by the seed script:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@healthai.local | Admin@12345 |
| Doctor | dr.sharma@healthai.local | Doctor@12345 |

Patients register themselves at `/register`.

> Password reset links are printed to the server console in development
> (no SMTP required).

### 4. Test

```powershell
venv\Scripts\python.exe -m pytest tests -v
```

## API endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register` | — | Create a patient account |
| POST | `/api/login` | — | Get JWT access + refresh tokens |
| POST | `/api/predict` | Patient | Run an AI assessment *(Phase 5)* |
| POST | `/api/reports` | Patient | Upload a medical report |
| GET | `/api/reports` | Patient | List own uploaded reports |
| DELETE | `/api/report/<id>` | Patient | Delete own report |
| GET | `/api/patients` | Doctor/Admin | List patients *(Phase 3/4)* |
| GET | `/api/doctors` | Admin | List doctors *(Phase 4)* |
| PUT | `/api/profile` | Any | Update own profile *(Phase 2)* |

API clients authenticate with `Authorization: Bearer <access_token>`; the web
UI uses secure JWT cookies with CSRF protection automatically.

### Web pages (Phase 2 + 3)

| Path | Role | Description |
|------|------|-------------|
| `/patient/assess` | Patient | Run an AI health check (symptoms + vitals, habits from profile) |
| `/patient/predictions` | Patient | History of AI assessments with review status |
| `/patient/predictions/<id>` | Patient | Full assessment result + doctor's review |
| `/patient/doctor` | Patient | View the automatically assigned doctor |
| `/patient/appointments` | Patient | Book / cancel appointments with the assigned doctor |
| `/patient/profile` | Patient | View/edit name and phone (email immutable) |
| `/patient/health` | Patient | Basic health info + medical history + lifestyle |
| `/patient/reports` | Patient | Upload, list, download and delete medical reports |
| `/patient/change-password` | Patient | Change account password |
| `/doctor/patients` | Doctor | Assigned patients (search + risk filter) |
| `/doctor/patients/<id>` | Doctor | Full patient profile, history and assessments |
| `/doctor/predictions` | Doctor | Review queue (pending / reviewed) |
| `/doctor/predictions/<id>/review` | Doctor | Approve / reject an AI assessment + recommendations |
| `/doctor/appointments` | Doctor | Confirm / complete / cancel appointment requests |

## Security

Passwords hashed with bcrypt · JWT auth with role claims · role-based access
decorators on every private route · centralised input validation ·
parameterised queries via SQLAlchemy (SQL-injection safe) · Jinja2
autoescaping (XSS safe) · CSRF double-submit protection on cookie auth ·
upload type/size validation · audit logging of security events · security
headers on every response.

## Screenshots

*(Screenshots will be added here.)*

## Future enhancements

Real-time chat between patients and doctors, appointment booking with
calendar view, email/SMS notifications, wearable-device data import, and
multi-language support.
