# Deploying HealthAI to PythonAnywhere (free, always-on)

PythonAnywhere gives you a free account with one always-on Flask web app at
`https://yourname.pythonanywhere.com` (HTTPS included) — no credit card.

---

## 0. What you need

- A Gmail (or any) email address for the PythonAnywhere account.
- `healthai-deploy.zip` from this project (already excludes `venv`, databases,
  caches and tests).

## 1. Sign up

1. Go to <https://www.pythonanywhere.com> → **Create a Beginner account** (free).
2. Verify your email and log in.
3. Your app URL will be `https://YOURUSERNAME.pythonanywhere.com`.

## 2. Upload the code

1. From the machine with the zip: paste `healthai-deploy.zip` into the **Files**
   tab → **Upload a file** (drag & drop works).
2. Open the main menu → **Bash** console.
3. Unzip into `~/healthai` (the *contents* of the zip have no top-level folder):

```bash
mkdir -p ~/healthai
unzip -o healthai-deploy.zip -d ~/healthai
cd ~/healthai
ls          # you should see app.py, config.py, wsgi.py, ...
```

## 3. Create a virtualenv and install dependencies

```bash
mkvirtualenv healthai --python=python3.10
pip install --upgrade pip
pip install -r requirements.txt
```

(`scikit-learn`, `pandas`, `numpy` and `reportlab` all install fine here; this
takes a couple of minutes.)

## 4. Configure the environment

PythonAnywhere loads environment variables from **Web → your web app →
Environment variables**, one per line. Add these:

```ini
FLASK_ENV=production
SECRET_KEY=replace-with-a-long-random-string
JWT_SECRET_KEY=replace-with-a-different-long-random-string
APP_BASE_URL=https://YOURUSERNAME.pythonanywhere.com
ADMIN_EMAIL=admin@healthai.local
ADMIN_PASSWORD=PickAStrongPassword@123
```

Generate the two secrets, e.g.:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 5. Create the database and seed accounts

Still in the Bash console, from `~/healthai`:

```bash
flask --app app init-db
python seed.py                 # roles + admin + demo doctors
python seed_demo_users.py      # demo patient + demo doctor, linked to each other
```

Use SQLite (the automatic fallback) — the database file `healthai_dev.db` lives
in `~/healthai` and persists on your account.

Demo accounts:

| Role | Email | Password |
|---|---|---|
| Admin | `ADMIN_EMAIL` you set | your `ADMIN_PASSWORD` |
| Doctor | `demo.doctor@healthai.local` | `Doctor@12345` |
| Patient | `demo.patient@healthai.local` | `Patient@12345` |

## 6. Wire up the web app

1. **Web** tab → **Add a new web app** → **Manual configuration** → Python 3.10.
2. Under **Code**:
   - Source directory: `/home/YOURUSERNAME/healthai`
   - Working directory: `/home/YOURUSERNAME/healthai`
   - WSGI configuration file: click the link to open it, **delete everything**,
     and paste the WSGI file already in the repo:

     ```python
     import sys
     sys.path.insert(0, "/home/YOURUSERNAME/healthai")   # points at the source dir
     from wsgi import application                        # e.g. /home/YOURUSERNAME/healthai/wsgi.py
     ```

     (The repo's `wsgi.py` is just `from app import create_app; application = create_app()`.)
3. **Virtualenv**: under *Virtualenv* enter the path printed by
   `mkvirtualenv` (confirm with `ls ~/.virtualenvs`) —
   `/home/YOURUSERNAME/.virtualenvs/healthai`.
4. **Static files** (same Web tab): add a map
   URL → `/static`, directory → `/home/YOURUSERNAME/healthai/static`.
5. **Reload** the web app (need the environment variables above saved first;
   each save of env vars triggers its own reload).

## 7. Test

- Open `https://YOURUSERNAME.pythonanywhere.com` — landing page with live stats.
- Sign in with the patient demo account → health check, profile ring, ECG trace.
- Sign out, sign in with the demo doctor → review queue, patients.
- Send the URL to your friend — that's it.

## Troubleshooting

- **Login works locally but not on the site** → cookie/HTTPS issue:
  `FLASK_ENV=production` turns on `JWT_COOKIE_SECURE=True`; PythonAnywhere
  serves HTTPS on your subdomain, so plain `https://...` is required.
- **Landing page loads but dashboards 500** → the Database not created;
  re-run the `flask --app app init-db` + seed commands and reload.
- **Homepage works but /static is unstyled** → step 6.4 (static map) missing.
- **Password reset links**: no SMTP is configured on the demo, so reset links
  print in the server console (Errors tab / Bash) instead of email — registration
  is open, so a friend can just create their own account.
- **Model errors on first prediction** → the scikit-learn model (re)trains
  automatically on first use, then caches to `ml/artifacts/`.
- Check running logs: **Web → your app → Error log / Event log**.

## Bringing updates later

Re-upload the new zip, then in Bash: `cd ~/healthai && python seed... ` (only if
schema changed: `flask --app app init-db`), then hit **Reload** on the Web tab.