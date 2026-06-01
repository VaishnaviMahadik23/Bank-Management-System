from models.db import generate_account_number, generate_transaction_ref, get_connection, log_audit


class BankingError(Exception):
    pass


def create_account(user_id, account_type="savings", initial_deposit=0.0, ip=None):
    if initial_deposit < 0:
        raise BankingError("Initial deposit cannot be negative.")
    account_number = generate_account_number()
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user or not user["is_active"]:
            raise BankingError("User not found or inactive.")
        conn.execute(
            """INSERT INTO accounts (account_number, user_id, account_type, balance)
               VALUES (?, ?, ?, ?)""",
            (account_number, user_id, account_type, initial_deposit),
        )
        account_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if initial_deposit > 0:
            _record_transaction(
                conn,
                account_id,
                "deposit",
                initial_deposit,
                initial_deposit,
                "Initial deposit",
            )
        log_audit(conn, user_id, "account_created", f"Account {account_number}", ip)
        conn.commit()
    return account_number


def get_user_accounts(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, account_number, account_type, balance, status, created_at
               FROM accounts WHERE user_id = ? AND status != 'closed'
               ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_account_for_user(account_id, user_id, admin=False):
    with get_connection() as conn:
        if admin:
            row = conn.execute(
                """SELECT a.*, u.full_name, u.username
                   FROM accounts a JOIN users u ON a.user_id = u.id
                   WHERE a.id = ?""",
                (account_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id),
            ).fetchone()
    if not row:
        raise BankingError("Account not found or access denied.")
    return dict(row)


def deposit(account_id, user_id, amount, description="", ip=None, admin=False):
    if amount <= 0:
        raise BankingError("Deposit amount must be positive.")
    with get_connection() as conn:
        account = _get_account_locked(conn, account_id, user_id, admin)
        if account["status"] != "active":
            raise BankingError("Account is not active.")
        new_balance = account["balance"] + amount
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id)
        )
        _record_transaction(
            conn, account_id, "deposit", amount, new_balance, description or "Deposit"
        )
        log_audit(conn, user_id, "deposit", f"{amount} to {account['account_number']}", ip)
        conn.commit()
    return new_balance


def withdraw(account_id, user_id, amount, description="", ip=None, admin=False):
    if amount <= 0:
        raise BankingError("Withdrawal amount must be positive.")
    with get_connection() as conn:
        account = _get_account_locked(conn, account_id, user_id, admin)
        if account["status"] != "active":
            raise BankingError("Account is not active.")
        if account["balance"] < amount:
            raise BankingError("Insufficient funds.")
        new_balance = account["balance"] - amount
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id)
        )
        _record_transaction(
            conn,
            account_id,
            "withdrawal",
            amount,
            new_balance,
            description or "Withdrawal",
        )
        log_audit(
            conn, user_id, "withdrawal", f"{amount} from {account['account_number']}", ip
        )
        conn.commit()
    return new_balance


def transfer(from_account_id, user_id, to_account_number, amount, description="", ip=None):
    if amount <= 0:
        raise BankingError("Transfer amount must be positive.")
    with get_connection() as conn:
        from_acc = _get_account_locked(conn, from_account_id, user_id, False)
        if from_acc["status"] != "active":
            raise BankingError("Source account is not active.")
        to_acc = conn.execute(
            "SELECT * FROM accounts WHERE account_number = ? AND status = 'active'",
            (to_account_number.upper().strip(),),
        ).fetchone()
        if not to_acc:
            raise BankingError("Destination account not found.")
        if to_acc["id"] == from_account_id:
            raise BankingError("Cannot transfer to the same account.")
        if from_acc["balance"] < amount:
            raise BankingError("Insufficient funds.")

        from_balance = from_acc["balance"] - amount
        to_balance = to_acc["balance"] + amount
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (from_balance, from_account_id)
        )
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (to_balance, to_acc["id"])
        )
        desc = description or f"Transfer to {to_account_number}"
        _record_transaction(
            conn,
            from_account_id,
            "transfer_out",
            amount,
            from_balance,
            desc,
            to_acc["id"],
        )
        _record_transaction(
            conn,
            to_acc["id"],
            "transfer_in",
            amount,
            to_balance,
            f"Transfer from {from_acc['account_number']}",
            from_account_id,
        )
        log_audit(
            conn,
            user_id,
            "transfer",
            f"{amount} {from_acc['account_number']} -> {to_account_number}",
            ip,
        )
        conn.commit()
    return from_balance


def get_transactions(account_id, user_id, limit=50, admin=False):
    get_account_for_user(account_id, user_id, admin)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT transaction_ref, type, amount, balance_after, description, created_at
               FROM transactions WHERE account_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (account_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def update_account_status(account_id, status, admin_user_id, ip=None):
    if status not in ("active", "frozen", "closed"):
        raise BankingError("Invalid status.")
    with get_connection() as conn:
        conn.execute("UPDATE accounts SET status = ? WHERE id = ?", (status, account_id))
        log_audit(conn, admin_user_id, "account_status_change", f"{account_id} -> {status}", ip)
        conn.commit()


def _get_account_locked(conn, account_id, user_id, admin):
    if admin:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id),
        ).fetchone()
    if not row:
        raise BankingError("Account not found or access denied.")
    return dict(row)


def _record_transaction(
    conn, account_id, tx_type, amount, balance_after, description, related_id=None
):
    conn.execute(
        """INSERT INTO transactions
           (transaction_ref, account_id, type, amount, balance_after, description, related_account_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            generate_transaction_ref(),
            account_id,
            tx_type,
            amount,
            balance_after,
            description,
            related_id,
        ),
    )


def get_all_customers():
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT u.id, u.username, u.email, u.full_name, u.phone, u.is_active, u.created_at,
                      COUNT(a.id) as account_count
               FROM users u
               LEFT JOIN accounts a ON u.id = a.user_id AND a.status != 'closed'
               WHERE u.role = 'customer'
               GROUP BY u.id
               ORDER BY u.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_accounts():
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT a.id, a.account_number, a.account_type, a.balance, a.status, a.created_at,
                      u.full_name, u.username
               FROM accounts a
               JOIN users u ON a.user_id = u.id
               ORDER BY a.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_audit_logs(limit=100):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT al.*, u.username
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id
               ORDER BY al.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
