import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME_MAIN = os.getenv("DB_NAME_MAIN")
DB_NAME_GEO = os.getenv("DB_NAME_GEO")