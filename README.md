# Bank Management System

A secure web application for automating core banking operations: customer registration, account management, deposits, withdrawals, fund transfers, balance inquiries, transaction history, and administrative controls.

## Features

- **Customer registration** — Sign up with automatic account creation
- **Secure authentication** — Password hashing (Werkzeug), session-based login
- **Deposits & withdrawals** — Real-time balance updates with transaction records
- **Fund transfers** — Transfer between accounts with dual ledger entries
- **Balance inquiry** — View account details and current balance
- **Transaction history** — Filterable statements by account and date range
- **Profile management** — Update personal info and password
- **Admin panel** — Customer management, account status control, audit logs, system metrics

## Tech Stack

| Layer    | Technology              |
|----------|-------------------------|
| Frontend | HTML, CSS, JavaScript   |
| Backend  | Python (Flask)          |
| Database | SQLite                  |

## Quick Start

### Prerequisites

- Python 3.10+

### Installation

```bash
cd bank-management-system
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Default Admin Account

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

> Change the admin password after first login in production.

### Environment Variables (optional)

| Variable       | Description                          |
|----------------|--------------------------------------|
| `SECRET_KEY`   | Flask session secret (set in prod)   |
| `FLASK_ENV`    | Set to `production` when deployed    |
| `DATABASE_PATH`| Custom SQLite file path (optional)   |
| `PORT`         | Server port (default `5000`)         |

## Deployment

Deploy to the cloud for a live demo URL (portfolio / resume).

**Recommended:** [Render](https://render.com) (free tier + GitHub)

See **[DEPLOY.md](DEPLOY.md)** for step-by-step instructions (Render Blueprint or manual setup, plus PythonAnywhere).

## Project Structure

```
bank-management-system/
├── app.py              # Flask routes and application entry
├── config.py           # Configuration
├── services.py         # Banking business logic
├── utils.py            # Helpers (IDs, refs)
├── database/
│   ├── schema.sql      # Database schema
│   └── db.py           # Connection and init
├── templates/          # HTML templates (Jinja2)
├── static/
│   ├── css/style.css
│   └── js/main.js
├── data/               # SQLite DB (created on first run)
└── requirements.txt
```

## Usage Flow

1. **Register** a new customer account (creates user + first bank account).
2. **Login** and use the dashboard to view accounts and recent transactions.
3. **Deposit / Withdraw / Transfer** funds from the sidebar navigation.
4. **View transactions** with optional filters for account and date range.
5. **Admin** users can manage customers, freeze/close accounts, process transactions, and review audit logs.

## Security Notes

- Passwords are hashed with Werkzeug before storage.
- Foreign keys and balance constraints enforced at the database level.
- All significant actions are logged in `audit_logs`.
- Set a strong `SECRET_KEY` environment variable before deploying to production.

## Deployement

**Live URL:-** `https://bank-management-system-mtws.onrender.com`

## License

MIT — free for educational and portfolio use.
