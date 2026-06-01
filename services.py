from database.db import get_db
from utils import generate_account_number, generate_transaction_ref


def log_audit(user_id, action, details=None, ip=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
        (user_id, action, details, ip),
    )
    conn.commit()
    conn.close()


def create_account(user_id, account_type="savings", initial_deposit=0.0):
    conn = get_db()
    account_number = generate_account_number()
    while conn.execute(
        "SELECT id FROM accounts WHERE account_number = ?", (account_number,)
    ).fetchone():
        account_number = generate_account_number()

    cursor = conn.execute(
        """INSERT INTO accounts (account_number, user_id, account_type, balance)
           VALUES (?, ?, ?, ?)""",
        (account_number, user_id, account_type, initial_deposit),
    )
    account_id = cursor.lastrowid

    if initial_deposit > 0:
        ref = generate_transaction_ref()
        conn.execute(
            """INSERT INTO transactions
               (transaction_ref, account_id, type, amount, balance_after, description)
               VALUES (?, ?, 'deposit', ?, ?, 'Initial deposit')""",
            (ref, account_id, initial_deposit, initial_deposit),
        )

    conn.commit()
    account = conn.execute(
        "SELECT * FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    conn.close()
    return dict(account)


def deposit(account_id, amount, description="Deposit"):
    conn = get_db()
    account = conn.execute(
        "SELECT * FROM accounts WHERE id = ? AND status = 'active'", (account_id,)
    ).fetchone()
    if not account:
        conn.close()
        return None, "Account not found or inactive"

    new_balance = account["balance"] + amount
    conn.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id)
    )
    ref = generate_transaction_ref()
    conn.execute(
        """INSERT INTO transactions
           (transaction_ref, account_id, type, amount, balance_after, description)
           VALUES (?, ?, 'deposit', ?, ?, ?)""",
        (ref, account_id, amount, new_balance, description),
    )
    conn.commit()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE transaction_ref = ?", (ref,)
    ).fetchone()
    conn.close()
    return dict(txn), None


def withdraw(account_id, amount, description="Withdrawal"):
    conn = get_db()
    account = conn.execute(
        "SELECT * FROM accounts WHERE id = ? AND status = 'active'", (account_id,)
    ).fetchone()
    if not account:
        conn.close()
        return None, "Account not found or inactive"
    if account["balance"] < amount:
        conn.close()
        return None, "Insufficient funds"

    new_balance = account["balance"] - amount
    conn.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id)
    )
    ref = generate_transaction_ref()
    conn.execute(
        """INSERT INTO transactions
           (transaction_ref, account_id, type, amount, balance_after, description)
           VALUES (?, ?, 'withdrawal', ?, ?, ?)""",
        (ref, account_id, amount, new_balance, description),
    )
    conn.commit()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE transaction_ref = ?", (ref,)
    ).fetchone()
    conn.close()
    return dict(txn), None


def transfer(from_account_id, to_account_number, amount, description="Fund transfer"):
    conn = get_db()
    from_acc = conn.execute(
        "SELECT * FROM accounts WHERE id = ? AND status = 'active'",
        (from_account_id,),
    ).fetchone()
    to_acc = conn.execute(
        "SELECT * FROM accounts WHERE account_number = ? AND status = 'active'",
        (to_account_number,),
    ).fetchone()

    if not from_acc:
        conn.close()
        return None, "Source account not found or inactive"
    if not to_acc:
        conn.close()
        return None, "Destination account not found or inactive"
    if from_acc["id"] == to_acc["id"]:
        conn.close()
        return None, "Cannot transfer to the same account"
    if from_acc["balance"] < amount:
        conn.close()
        return None, "Insufficient funds"

    from_balance = from_acc["balance"] - amount
    to_balance = to_acc["balance"] + amount

    conn.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?", (from_balance, from_acc["id"])
    )
    conn.execute(
        "UPDATE accounts SET balance = ? WHERE id = ?", (to_balance, to_acc["id"])
    )

    ref_out = generate_transaction_ref()
    ref_in = generate_transaction_ref()

    conn.execute(
        """INSERT INTO transactions
           (transaction_ref, account_id, type, amount, balance_after, description,
            related_account_id)
           VALUES (?, ?, 'transfer_out', ?, ?, ?, ?)""",
        (
            ref_out,
            from_acc["id"],
            amount,
            from_balance,
            f"{description} to {to_account_number}",
            to_acc["id"],
        ),
    )
    conn.execute(
        """INSERT INTO transactions
           (transaction_ref, account_id, type, amount, balance_after, description,
            related_account_id)
           VALUES (?, ?, 'transfer_in', ?, ?, ?, ?)""",
        (
            ref_in,
            to_acc["id"],
            amount,
            to_balance,
            f"{description} from {from_acc['account_number']}",
            from_acc["id"],
        ),
    )
    conn.commit()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE transaction_ref = ?", (ref_out,)
    ).fetchone()
    conn.close()
    return dict(txn), None
