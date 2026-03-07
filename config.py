"""
config.py — Markaziy sozlamalar va konstantlar
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS  = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
PROXY_URL  = os.getenv("PROXY_URL", "")   # Masalan: socks5://127.0.0.1:1080

# Toshkent vaqt zonasi (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

# Konstantalar
ATTENDANCE_EMOJI = {"present": "✅", "absent": "❌", "late": "⏰", "excused": "📝"}
ATTENDANCE_LABEL = {"present": "Keldi", "absent": "Kelmadi", "late": "Kech keldi", "excused": "Sababli"}
FILE_TYPE_EMOJI  = {"photo": "🖼", "document": "📎", "video": "🎥"}

CRITERIA_LABELS = {
    "homework":      "📝 Uyga vazifa",
    "participation": "🙋 Darsda faollik",
    "discipline":    "🧑‍💻 Intizom",
}

SCORE_EMOJI = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}

WEEKDAY_LABELS = {
    0: "1️⃣ Dushanba", 1: "2️⃣ Seshanba",  2: "3️⃣ Chorshanba",
    3: "4️⃣ Payshanba", 4: "5️⃣ Juma",      5: "6️⃣ Shanba",
}

WEEKDAY_UZ = {
    "Monday": "Dushanba", "Tuesday": "Seshanba", "Wednesday": "Chorshanba",
    "Thursday": "Payshanba", "Friday": "Juma", "Saturday": "Shanba", "Sunday": "Yakshanba",
}


def now_tashkent() -> str:
    """Tashkent vaqtini qaytaradi → YYYY-MM-DD HH:MM:SS"""
    return datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")


def time_tashkent() -> str:
    """Faqat vaqt → HH:MM"""
    return datetime.now(TASHKENT_TZ).strftime("%H:%M")


def utc_to_tashkent(utc_str: str, fmt_out: str = "%Y-%m-%d %H:%M") -> str:
    """
    SQLite CURRENT_TIMESTAMP (UTC) → Toshkent vaqti (UTC+5).
    utc_str formatlar: 'YYYY-MM-DD HH:MM:SS' yoki 'YYYY-MM-DD HH:MM'
    """
    if not utc_str:
        return ""
    try:
        utc_str_short = utc_str[:16]   # 'YYYY-MM-DD HH:MM'
        dt_utc  = datetime.strptime(utc_str_short, "%Y-%m-%d %H:%M")
        dt_tash = dt_utc + timedelta(hours=5)
        return dt_tash.strftime(fmt_out)
    except Exception:
        return utc_str[:16]


# ── DB instansiyasi ───────────────────────────────────────────────
from core.db import DB
db = DB()