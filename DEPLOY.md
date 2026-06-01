# Deploy Bank Management System

This guide deploys the app to **[Render](https://render.com)** (free tier, connects to GitHub).

**Live URL example:** `https://bank-management-system-xxxx.onrender.com`

---

## Before you deploy

1. Push your code to GitHub:  
   `https://github.com/VaishnaviMahadik23/Bank-Management-System`

2. Sign up at [render.com](https://render.com) (use **Sign in with GitHub**).

---

## Option A — Deploy with Blueprint (easiest)

1. Open [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Blueprint**.
3. Connect repository `VaishnaviMahadik23/Bank-Management-System`.
4. Render reads `render.yaml` automatically.
5. Click **Apply** → wait for build (2–5 minutes).
6. Open the generated URL.

---

## Option B — Manual Web Service

1. **New +** → **Web Service**.
2. Connect your GitHub repo `Bank-Management-System`.
3. Use these settings:

| Setting | Value |
|---------|--------|
| **Name** | `bank-management-system` |
| **Region** | Singapore or closest to you |
| **Branch** | `main` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| **Plan** | Free |

4. **Environment variables** (Environment → Add):

| Key | Value |
|-----|--------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | *(Generate or paste a long random string)* |

5. Click **Create Web Service**.

---

## After deployment

- **Admin login:** `admin` / `admin123`  
  Change the password from **Profile** after first login.
- Free tier may **sleep** after ~15 min idle; first visit can take 30–60 seconds to wake.
- **SQLite on free tier:** Data persists while the service runs but can reset if Render rebuilds or moves your instance. Fine for demos/portfolio; use PostgreSQL for real production.

---

## Option C — PythonAnywhere (SQLite-friendly)

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com).
2. Upload project or clone from GitHub (Bash console).
3. Create virtualenv and `pip install -r requirements.txt`.
4. **Web** tab → **Manual configuration** → Python 3.11.
5. WSGI file:

```python
import sys
path = '/home/YOUR_USERNAME/Bank-Management-System'
if path not in sys.path:
    sys.path.append(path)

from wsgi import app as application
```

6. Reload web app. Set `SECRET_KEY` and `FLASK_ENV=production` in WSGI or `.env`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check `requirements.txt` and Python version in `runtime.txt` |
| 502 / crash on start | Logs → ensure start command is `gunicorn wsgi:app ...` |
| Login/session issues | Set `SECRET_KEY` and `FLASK_ENV=production` |
| Database empty after redeploy | Expected on free Render; re-register or use paid disk / PostgreSQL |

---

## Custom domain (optional)

Render → your service → **Settings** → **Custom Domains** → add your domain and DNS records.
