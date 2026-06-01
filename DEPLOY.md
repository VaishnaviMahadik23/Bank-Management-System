# Deploy Bank Management System (with persistent PostgreSQL)

Use **Option 2: PostgreSQL on Render** so registered users and transactions are **saved permanently** (no more “user not found” after restart).

---

## Part 1 — Create PostgreSQL database on Render

1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **PostgreSQL**.
3. Settings:
   - **Name:** `bank-db` (or any name)
   - **Database:** `bankmanagement`
   - **User:** `bankuser`
   - **Region:** Same as your web service
   - **Plan:** **Free**
4. Click **Create Database**.
5. Wait until status is **Available**.
6. Open the database → copy **Internal Database URL** (starts with `postgresql://` or `postgres://`).  
   Use **Internal** URL for your web service on Render (not External).

---

## Part 2 — Connect database to your Web Service

1. Open your **Web Service** (Bank Management System app).
2. Go to **Environment**.
3. Add variable:

   | Key | Value |
   |-----|--------|
   | `DATABASE_URL` | Paste **Internal Database URL** from Part 1 |

4. Ensure these also exist:

   | Key | Value |
   |-----|--------|
   | `FLASK_ENV` | `production` |
   | `SECRET_KEY` | Long random string (Generate) |

5. Click **Save Changes**.
6. Render will **redeploy** automatically (wait 2–5 minutes).

---

## Part 3 — Push latest code (PostgreSQL support)

In VS Code terminal:

```powershell
cd d:\Z+Projects\bank-management-system
git add .
git commit -m "Add PostgreSQL support for persistent user data on Render"
git push origin main
```

After push, Render rebuilds the web service. On startup, tables and admin user are created in PostgreSQL.

---

## Part 4 — Test

1. Open your live URL.
2. **Register** a new user.
3. **Log out**, close the browser, wait a few minutes (or redeploy once).
4. **Log in** again with the same user → should work.

Default admin (recreated if missing): `admin` / `admin123`

---

## New deploy from scratch (Blueprint)

If creating everything new:

1. Push code with `render.yaml` to GitHub.
2. **New +** → **Blueprint** → select repo → **Apply**.
3. Render creates **PostgreSQL + Web Service** and links `DATABASE_URL` automatically.

---

## Local development

Without `DATABASE_URL`, the app uses **SQLite** (`data/bank.db`) as before:

```powershell
python app.py
```

To test PostgreSQL locally, set `DATABASE_URL` in `.env` (do not commit `.env`).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build error `psycopg2` | `requirements.txt` includes `psycopg2-binary`; redeploy |
| Still losing users | Confirm `DATABASE_URL` is set on **Web Service** (not only on DB) |
| `admin` works, new users don’t | Old SQLite deploy; add `DATABASE_URL` and redeploy |
| Connection refused | Use **Internal** Database URL on Render |

---

## Why not PythonAnywhere (Option 4)?

You already use Render. PostgreSQL on Render is the best fit: same platform, persistent data, and stronger for your resume (`Flask + PostgreSQL`).
