import functools
import os

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import SECRET_KEY
from database.db import get_db, init_db
from services import create_account, deposit, log_audit, transfer, withdraw

app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        conn = get_db()
        g.user = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (session["user_id"],)
        ).fetchone()
        conn.close()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        account_type = request.form.get("account_type", "savings")
        initial_deposit = float(request.form.get("initial_deposit", 0) or 0)

        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if not full_name:
            errors.append("Full name is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if initial_deposit < 0:
            errors.append("Initial deposit cannot be negative.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html")

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
        if existing:
            conn.close()
            flash("Username or email already registered.", "error")
            return render_template("register.html")

        cursor = conn.execute(
            """INSERT INTO users (username, email, password_hash, full_name, phone)
               VALUES (?, ?, ?, ?, ?)""",
            (username, email, generate_password_hash(password), full_name, phone),
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        create_account(user_id, account_type, initial_deposit)
        log_audit(user_id, "REGISTER", f"New customer: {username}", request.remote_addr)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            log_audit(user["id"], "LOGIN", None, request.remote_addr)
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    log_audit(g.user["id"], "LOGOUT", None, request.remote_addr)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    if g.user["role"] == "admin":
        stats = {
            "customers": conn.execute(
                "SELECT COUNT(*) as c FROM users WHERE role = 'customer'"
            ).fetchone()["c"],
            "accounts": conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()[
                "c"
            ],
            "total_balance": conn.execute(
                "SELECT COALESCE(SUM(balance), 0) as s FROM accounts WHERE status = 'active'"
            ).fetchone()["s"],
            "transactions_today": conn.execute(
                """SELECT COUNT(*) as c FROM transactions
                   WHERE date(created_at) = date('now')"""
            ).fetchone()["c"],
        }
        conn.close()
        return render_template("admin_dashboard.html", stats=stats)

    accounts = conn.execute(
        "SELECT * FROM accounts WHERE user_id = ? ORDER BY created_at DESC",
        (g.user["id"],),
    ).fetchall()
    recent = conn.execute(
        """SELECT t.*, a.account_number FROM transactions t
           JOIN accounts a ON t.account_id = a.id
           WHERE a.user_id = ?
           ORDER BY t.created_at DESC LIMIT 10""",
        (g.user["id"],),
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", accounts=accounts, recent=recent)


@app.route("/accounts")
@login_required
def accounts():
    conn = get_db()
    if g.user["role"] == "admin":
        rows = conn.execute(
            """SELECT a.*, u.full_name, u.username FROM accounts a
               JOIN users u ON a.user_id = u.id ORDER BY a.created_at DESC"""
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE user_id = ? ORDER BY created_at DESC",
            (g.user["id"],),
        ).fetchall()
    conn.close()
    return render_template("accounts.html", accounts=rows, is_admin=g.user["role"] == "admin")


@app.route("/accounts/new", methods=["GET", "POST"])
@login_required
def new_account():
    if g.user["role"] == "admin":
        flash("Admins manage accounts from the admin panel.", "info")
        return redirect(url_for("admin_customers"))

    if request.method == "POST":
        account_type = request.form.get("account_type", "savings")
        initial = float(request.form.get("initial_deposit", 0) or 0)
        if initial < 0:
            flash("Initial deposit cannot be negative.", "error")
            return render_template("new_account.html")
        acc = create_account(g.user["id"], account_type, initial)
        log_audit(
            g.user["id"],
            "CREATE_ACCOUNT",
            acc["account_number"],
            request.remote_addr,
        )
        flash(f"Account {acc['account_number']} created successfully.", "success")
        return redirect(url_for("accounts"))

    return render_template("new_account.html")


@app.route("/accounts/<int:account_id>")
@login_required
def account_detail(account_id):
    conn = get_db()
    if g.user["role"] == "admin":
        account = conn.execute(
            """SELECT a.*, u.full_name, u.email FROM accounts a
               JOIN users u ON a.user_id = u.id WHERE a.id = ?""",
            (account_id,),
        ).fetchone()
    else:
        account = conn.execute(
            "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, g.user["id"]),
        ).fetchone()

    if not account:
        conn.close()
        flash("Account not found.", "error")
        return redirect(url_for("accounts"))

    transactions = conn.execute(
        "SELECT * FROM transactions WHERE account_id = ? ORDER BY created_at DESC LIMIT 50",
        (account_id,),
    ).fetchall()
    conn.close()
    return render_template(
        "account_detail.html", account=account, transactions=transactions
    )


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit_page():
    conn = get_db()
    if g.user["role"] == "admin":
        accounts_list = conn.execute(
            "SELECT a.id, a.account_number, u.full_name FROM accounts a JOIN users u ON a.user_id = u.id WHERE a.status = 'active'"
        ).fetchall()
    else:
        accounts_list = conn.execute(
            "SELECT id, account_number FROM accounts WHERE user_id = ? AND status = 'active'",
            (g.user["id"],),
        ).fetchall()
    conn.close()

    if request.method == "POST":
        account_id = int(request.form.get("account_id", 0))
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "Deposit").strip() or "Deposit"

        if amount <= 0:
            flash("Amount must be greater than zero.", "error")
            return render_template("deposit.html", accounts=accounts_list)

        if g.user["role"] != "admin":
            conn = get_db()
            owned = conn.execute(
                "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, g.user["id"]),
            ).fetchone()
            conn.close()
            if not owned:
                flash("Invalid account.", "error")
                return render_template("deposit.html", accounts=accounts_list)

        txn, err = deposit(account_id, amount, description)
        if err:
            flash(err, "error")
        else:
            log_audit(g.user["id"], "DEPOSIT", f"{amount} to account {account_id}", request.remote_addr)
            flash(f"Deposit of ${amount:,.2f} successful. Ref: {txn['transaction_ref']}", "success")
            return redirect(url_for("account_detail", account_id=account_id))

    return render_template("deposit.html", accounts=accounts_list)


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw_page():
    conn = get_db()
    if g.user["role"] == "admin":
        accounts_list = conn.execute(
            "SELECT a.id, a.account_number, u.full_name FROM accounts a JOIN users u ON a.user_id = u.id WHERE a.status = 'active'"
        ).fetchall()
    else:
        accounts_list = conn.execute(
            "SELECT id, account_number, balance FROM accounts WHERE user_id = ? AND status = 'active'",
            (g.user["id"],),
        ).fetchall()
    conn.close()

    if request.method == "POST":
        account_id = int(request.form.get("account_id", 0))
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "Withdrawal").strip() or "Withdrawal"

        if amount <= 0:
            flash("Amount must be greater than zero.", "error")
            return render_template("withdraw.html", accounts=accounts_list)

        if g.user["role"] != "admin":
            conn = get_db()
            owned = conn.execute(
                "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, g.user["id"]),
            ).fetchone()
            conn.close()
            if not owned:
                flash("Invalid account.", "error")
                return render_template("withdraw.html", accounts=accounts_list)

        txn, err = withdraw(account_id, amount, description)
        if err:
            flash(err, "error")
        else:
            log_audit(g.user["id"], "WITHDRAWAL", f"{amount} from account {account_id}", request.remote_addr)
            flash(f"Withdrawal of ${amount:,.2f} successful. Ref: {txn['transaction_ref']}", "success")
            return redirect(url_for("account_detail", account_id=account_id))

    return render_template("withdraw.html", accounts=accounts_list)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer_page():
    conn = get_db()
    accounts_list = conn.execute(
        "SELECT id, account_number, balance FROM accounts WHERE user_id = ? AND status = 'active'",
        (g.user["id"],),
    ).fetchall()
    conn.close()

    if g.user["role"] == "admin":
        flash("Fund transfers are performed by customers on their own accounts.", "info")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        from_id = int(request.form.get("from_account_id", 0))
        to_number = request.form.get("to_account_number", "").strip()
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "Fund transfer").strip() or "Fund transfer"

        if amount <= 0:
            flash("Amount must be greater than zero.", "error")
            return render_template("transfer.html", accounts=accounts_list)
        if not to_number:
            flash("Destination account number is required.", "error")
            return render_template("transfer.html", accounts=accounts_list)

        conn = get_db()
        owned = conn.execute(
            "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
            (from_id, g.user["id"]),
        ).fetchone()
        conn.close()
        if not owned:
            flash("Invalid source account.", "error")
            return render_template("transfer.html", accounts=accounts_list)

        txn, err = transfer(from_id, to_number, amount, description)
        if err:
            flash(err, "error")
        else:
            log_audit(
                g.user["id"],
                "TRANSFER",
                f"{amount} to {to_number}",
                request.remote_addr,
            )
            flash(f"Transfer of ${amount:,.2f} successful. Ref: {txn['transaction_ref']}", "success")
            return redirect(url_for("account_detail", account_id=from_id))

    return render_template("transfer.html", accounts=accounts_list)


@app.route("/transactions")
@login_required
def transactions():
    conn = get_db()
    account_filter = request.args.get("account_id")
    date_from = request.args.get("from")
    date_to = request.args.get("to")

    query = """SELECT t.*, a.account_number FROM transactions t
               JOIN accounts a ON t.account_id = a.id WHERE 1=1"""
    params = []

    if g.user["role"] != "admin":
        query += " AND a.user_id = ?"
        params.append(g.user["id"])

    if account_filter:
        query += " AND t.account_id = ?"
        params.append(int(account_filter))
    if date_from:
        query += " AND date(t.created_at) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(t.created_at) <= date(?)"
        params.append(date_to)

    query += " ORDER BY t.created_at DESC LIMIT 200"
    rows = conn.execute(query, params).fetchall()

    if g.user["role"] == "admin":
        accounts_list = conn.execute(
            "SELECT id, account_number FROM accounts ORDER BY account_number"
        ).fetchall()
    else:
        accounts_list = conn.execute(
            "SELECT id, account_number FROM accounts WHERE user_id = ?",
            (g.user["id"],),
        ).fetchall()
    conn.close()
    return render_template(
        "transactions.html",
        transactions=rows,
        accounts=accounts_list,
        filters={"account_id": account_filter, "from": date_from, "to": date_to},
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not full_name:
            flash("Full name is required.", "error")
            return render_template("profile.html")

        conn = get_db()
        if new_password:
            if len(new_password) < 6:
                flash("Password must be at least 6 characters.", "error")
                conn.close()
                return render_template("profile.html")
            if new_password != confirm:
                flash("Passwords do not match.", "error")
                conn.close()
                return render_template("profile.html")
            conn.execute(
                "UPDATE users SET full_name = ?, phone = ?, password_hash = ? WHERE id = ?",
                (full_name, phone, generate_password_hash(new_password), g.user["id"]),
            )
        else:
            conn.execute(
                "UPDATE users SET full_name = ?, phone = ? WHERE id = ?",
                (full_name, phone, g.user["id"]),
            )
        conn.commit()
        conn.close()
        log_audit(g.user["id"], "PROFILE_UPDATE", None, request.remote_addr)
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html")


# --- Admin routes ---

@app.route("/admin/customers")
@admin_required
def admin_customers():
    conn = get_db()
    customers = conn.execute(
        """SELECT u.*, COUNT(a.id) as account_count,
                  COALESCE(SUM(a.balance), 0) as total_balance
           FROM users u
           LEFT JOIN accounts a ON u.id = a.user_id AND a.status = 'active'
           WHERE u.role = 'customer'
           GROUP BY u.id ORDER BY u.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin_customers.html", customers=customers)


@app.route("/admin/customers/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_customer(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'customer'", (user_id,)
    ).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        log_audit(g.user["id"], "TOGGLE_USER", f"user {user_id} active={new_status}", request.remote_addr)
        flash(f"Customer {'activated' if new_status else 'deactivated'}.", "success")
    conn.close()
    return redirect(url_for("admin_customers"))


@app.route("/admin/accounts/<int:account_id>/status", methods=["POST"])
@admin_required
def admin_account_status(account_id):
    status = request.form.get("status", "active")
    if status not in ("active", "frozen", "closed"):
        flash("Invalid status.", "error")
        return redirect(url_for("accounts"))

    conn = get_db()
    conn.execute("UPDATE accounts SET status = ? WHERE id = ?", (status, account_id))
    conn.commit()
    conn.close()
    log_audit(g.user["id"], "ACCOUNT_STATUS", f"account {account_id} -> {status}", request.remote_addr)
    flash(f"Account status updated to {status}.", "success")
    return redirect(url_for("accounts"))


@app.route("/admin/audit-logs")
@admin_required
def admin_audit():
    conn = get_db()
    logs = conn.execute(
        """SELECT l.*, u.username FROM audit_logs l
           LEFT JOIN users u ON l.user_id = u.id
           ORDER BY l.created_at DESC LIMIT 100"""
    ).fetchall()
    conn.close()
    return render_template("admin_audit.html", logs=logs)


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
