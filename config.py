import os
from dotenv import load_dotenv

# .env ফাইল থেকে সিক্রেট লোড করবে
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ভ্যালিডেশন চেক
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ API_ID, API_HASH, অথবা BOT_TOKEN পাওয়া যায়নি! .env ফাইল চেক করুন।")
