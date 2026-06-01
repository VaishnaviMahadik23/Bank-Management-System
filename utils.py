import random
import string
from datetime import datetime


def generate_account_number():
    return "".join(random.choices(string.digits, k=10))


def generate_transaction_ref():
    prefix = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"TXN{prefix}{suffix}"
