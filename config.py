import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "bank.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-in-production-use-env-var")
