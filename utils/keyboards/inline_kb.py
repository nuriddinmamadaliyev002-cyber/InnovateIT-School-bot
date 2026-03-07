"""
utils/keyboards/inline_kb.py — Umumiy Inline klaviaturalar
"""
from datetime import date, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import WEEKDAY_UZ


# ── Bekor qilish ─────────────────────────────────────────────────

def kb_cancel(data: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Bekor", callback_data=data)
    ]])


def kb_cancel_teacher() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Bekor qilish", callback_data="tch_cancel")
    ]])


# ── Sinflar / Fanlar ──────────────────────────────────────────────

def kb_classes(classes: list, prefix: str = "cls") -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"{prefix}_{c['id']}")]
        for c in classes
    ]
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="cancel")])
    return InlineKeyboardMarkup(btns)


def kb_subjects(subjects: list, prefix: str = "subj",
                back: str = "back_main") -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(f"📚 {s['name']}", callback_data=f"{prefix}_{s['id']}")]
        for s in subjects
    ]
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data=back)])
    return InlineKeyboardMarkup(btns)


def kb_teacher_subjects(subjects: list, prefix: str = "tch_subj") -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(s["name"], callback_data=f"{prefix}_{s['id']}")]
        for s in subjects
    ]
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


# ── Sana tanlash ─────────────────────────────────────────────────

def _uz_day(d: date, i: int) -> str:
    if i == 0: return "Bugun"
    if i == 1: return "Kecha"
    en = d.strftime("%A")
    return d.strftime("%d.%m ") + f"({WEEKDAY_UZ.get(en, en)})"


def kb_dates(prefix: str = "date", days: int = 7) -> InlineKeyboardMarkup:
    today = date.today()
    btns = [
        [InlineKeyboardButton(_uz_day(today - timedelta(days=i), i),
                              callback_data=f"{prefix}_{(today - timedelta(days=i)).isoformat()}")]
        for i in range(days)
    ]
    btns.append([InlineKeyboardButton("📅 Boshqa sana", callback_data="custom_date")])
    return InlineKeyboardMarkup(btns)


# ── Jadval bo'yicha sana tanlash ─────────────────────────────────

def kb_schedule_dates(schedule_dates: list, prefix: str = "tch_date") -> InlineKeyboardMarkup:
    """
    O'qituvchi haftalik jadvali asosida dars bor kunlarni ko'rsatadi.
    schedule_dates: [{'date': 'YYYY-MM-DD', 'weekday': int,
                      'start_time': str, 'end_time': str}, ...]
    """
    today = date.today()
    btns = []
    for item in schedule_dates:
        d        = date.fromisoformat(item['date'])
        delta    = (today - d).days
        wd_uz    = WEEKDAY_UZ.get(d.strftime("%A"), "")
        d_fmt    = d.strftime("%d.%m.%Y")
        time_str = ""
        if item.get('start_time') and item.get('end_time'):
            time_str = f" {item['start_time']}–{item['end_time']}"

        if delta == 0:
            label = f"📍 Bugun — {d_fmt} ({wd_uz}){time_str}"
        elif delta == 1:
            label = f"📅 Kecha — {d_fmt} ({wd_uz}){time_str}"
        elif delta < 0:
            # Kelgusi dars
            label = f"🔜 {d_fmt} ({wd_uz}){time_str}"
        else:
            label = f"📅 {d_fmt} ({wd_uz}){time_str}"

        btns.append([InlineKeyboardButton(label, callback_data=f"{prefix}_{item['date']}")])

    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


# ── Dars amallar ──────────────────────────────────────────────────

def kb_lesson_actions(date_str: str, subject_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Vazifa", callback_data=f"view_hw_{date_str}_{subject_id}"),
            InlineKeyboardButton("📖 Mavzu",  callback_data=f"view_topic_{date_str}_{subject_id}"),
        ],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_dates")],
    ])


# ── Ko'p fayl yuborish ─────────────────────────────────────────────

def kb_teacher_files() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tayyor (saqlash)",   callback_data="tch_files_done")],
        [InlineKeyboardButton("❌ Bekor qilish",       callback_data="tch_cancel")],
    ])


def kb_student_files() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tayyor (yuborish)",  callback_data="sub_done")],
        [InlineKeyboardButton("❌ Bekor qilish",       callback_data="cancel")],
    ])