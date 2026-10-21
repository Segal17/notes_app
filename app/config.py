import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "192.168.1.50")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "notes")
DB_USER = os.getenv("DB_USER", "notes")
DB_PASSWORD = os.getenv("DB_PASSWORD", "notes_dev_pass")
