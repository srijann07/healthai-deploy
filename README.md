# HealthAI — Production Healthcare Risk Assessment & Workflow Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20MySQL%20%7C%20SQLite-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Security](https://img.shields.io/badge/Auth-JWT%20%2B%20RBAC%20%2B%20Bcrypt-green?style=flat&logo=jsonwebtokens)](https://jwt.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![Testing](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://pytest.org)

> 🚀 **Live Production Deployment (Render 24/7):** **[https://healthai-backend.onrender.com](https://healthai-backend.onrender.com)**  
> 🌐 **Live Mirror:** **[https://rock-requests-karen-submitted.trycloudflare.com](https://rock-requests-karen-submitted.trycloudflare.com)**  
> *Fully functional live deployment with database seeding, machine learning pipeline, role-based workflows, and report generation.*

---

## 🔑 Quick Evaluation & Demo Credentials

Reviewers and hiring teams can evaluate all system roles immediately using pre-seeded accounts:

| Role | Email / Login | Password | Available Features & Permissions |
| :--- | :--- | :--- | :--- |
| **Patient** | `demo.patient@healthai.local` | `Patient@12345` | Real-time AI symptom assessment, vital tracking, PDF clinical report download, appointment booking. |
| **Mobile OTP** | Phone: `9876543210` *(1-Click Autofill)* | *Instant OTP* | Instant passwordless authentication with direct DOM OTP populate. |
| **Doctor** | `demo.doctor@healthai.local` | `Doctor@12345` | Assigned patient queue, clinical AI prediction review, approve/reject workflow, clinical notes. |
| **Admin** | `admin@healthai.local` | `Admin@12345` | System audit logs, user & doctor provisioning, global patient records, platform metrics. |

---

## 🏗️ Architecture & Backend System Design

HealthAI is designed with a strict **layered separation of concerns** (Controller $\rightarrow$ Service $\rightarrow$ Model), ensuring maintainability, testability, and high API performance.

```text
 Client (Browser / Mobile / API Client)
    │
    ▼
 WSGI Gateway (Gunicorn / Reverse Proxy)
    │
 ┌──┴────────────────────────────────────────────────────────────────┐
 │                      FLASK APPLICATION                            │
 │                                                                   │
 │  ┌─────────────────┐   ┌──────────────────┐   ┌────────────────┐  │
 │  │  Route Handlers │──▶│   Middlewares    │──▶│  Controllers   │  │
 │  │  (Blueprints)   │   │  (JWT Auth/RBAC) │   │ (Request/Resp) │  │
 │  └─────────────────┘   └──────────────────┘   └───────┬────────┘  │
 │                                                       │           │
 │  ┌────────────────────────────────────────────────────▼────────┐  │
 │  │                     SERVICE LAYER                           │  │
 │  │  • AuthService        • PredictionService    • PDFService   │  │
 │  │  • ValidationService   • DoctorService        • OTPService   │  │
 │  └────────────────────────────┬────────────────────────────────┘  │
 │                               │                                   │
 │  ┌────────────────────────────▼────────────────────────────────┐  │
 │  │                      DATA & AI LAYER                        │  │
 │  │  • SQLAlchemy 2.0 ORM Models (Users, Patients, Records)     │  │
 │  │  • Machine Learning Inference Pipeline (Scikit-learn)       │  │
 │  └────────────────────────────┬────────────────────────────────┘  │
 └──┬────────────────────────────┼───────────────────────────────────┘
    │                            ▼
    ▼             ┌─────────────────────────────┐
 Cloud Storage    │      RELATIONAL DATABASE    │
 (Supabase/Local) │   PostgreSQL / MySQL / SQLite│
                  └─────────────────────────────┘
```

---

## ⚡ Core Backend Features (JD Alignment)

### 1. Robust RESTful APIs & Clean Service Layer
- **Layered Architecture:** Segregated into `routes/`, `controllers/`, and `services/` to keep business logic isolated from HTTP transport mechanics.
- **Defensive Validation:** Strict payload and query validation for clinical vitals, dates, symptoms, and MIME types.
- **Consistent Response Schema:** Standardized JSON error and success payloads across all endpoints with proper HTTP status codes.

### 2. Relational Database Modeling & SQLAlchemy ORM
- Designed high-integrity relational schemas with foreign-key constraints, cascading deletes, and optimized indexing.
- Multi-table schema covering `Users`, `Roles`, `Patients`, `Doctors`, `Appointments`, `Predictions`, `MedicalReports`, and `AuditLogs`.
- **Database Agnostic:** Native support for **PostgreSQL** (`psycopg2-binary`) in cloud production and **MySQL** (`PyMySQL`), with automated **SQLite** fallback for local development.

### 3. Enterprise Security, JWT & Role-Based Access Control (RBAC)
- **Multi-Role Access Control:** Custom decorators enforcing strict permission boundaries between Patients, Doctors, and Admins.
- **Stateless & Session Auth:** Dual JWT token storage support (HTTP-Only, SameSite cookies for server-rendered UI; Authorization Bearer headers for API clients).
- **Password Security:** Cryptographically secure password hashing using `bcrypt` with salt rounds.
- **CSRF & Security Headers:** Built-in CSRF token validation and automated security response headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).

### 4. Integrated AI & Automation Pipeline
- **Real-Time Clinical Risk Assessment:** Ingests patient symptoms and physiological vitals, pre-processes feature vectors, and computes multi-class health risk predictions via `scikit-learn`.
- **Doctor Verification Loop:** Predictions are stored with audit trails and routed for clinician verification and note generation before status updates.
- **Automated PDF Report Engine:** Asynchronously generates formatted, printable clinical PDF summaries using `ReportLab`.
- **Cloud Storage Integration:** Multi-provider storage adapters supporting **Supabase Storage**, **Firebase Admin**, and local filesystem with automatic fallback.

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.11, Flask 3.0, Werkzeug, Jinja2 |
| **Data Layer & ORM** | SQLAlchemy 2.0, PostgreSQL, MySQL (PyMySQL), SQLite |
| **Auth & Security** | Flask-JWT-Extended, Bcrypt, ItsDangerous, CSRF protection |
| **Machine Learning** | Scikit-learn, Pandas, NumPy, Joblib |
| **Reporting & Docs** | ReportLab (Dynamic PDF synthesis) |
| **Server & WSGI** | Gunicorn (Workers + Threads configuration) |
| **DevOps & Containers** | Docker (Multi-stage build), Cloudflare Tunnel, Render |
| **Testing** | Pytest, Pytest-flask |

---

## 🚀 Quick Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/srijann07/healthai-deploy.git
cd healthai-deploy
```

### 2. Create virtual environment & install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Seed database & run
```bash
python seed.py            # Generates schema, default roles, and demo accounts
python seed_demo_users.py # Adds demo patient & doctor profiles
python wsgi.py            # Starts web server on http://localhost:5000
```

---

## 🐳 Docker Deployment

The application includes a production-grade multi-stage [Dockerfile](Dockerfile):

```bash
# Build the Docker image
docker build -t healthai:latest .

# Run container
docker run -p 8080:8080 -e SECRET_KEY="your-secret-key" healthai:latest
```

---

## 👤 Author

**Srijan Sangroula**  
Software Development · Backend Systems · AI & Cloud Integrations  
- **GitHub:** [@srijann07](https://github.com/srijann07)  
- **Repository:** [https://github.com/srijann07/healthai-deploy](https://github.com/srijann07/healthai-deploy)
