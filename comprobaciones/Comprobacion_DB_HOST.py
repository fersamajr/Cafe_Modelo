import os
from dotenv import load_dotenv
load_dotenv()
print("DB_HOST =", os.getenv("DB_HOST"))
