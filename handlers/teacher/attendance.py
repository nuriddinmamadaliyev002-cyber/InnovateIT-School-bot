"""
handlers/teacher/attendance.py — O'quvchilar davomati logikasi (o'qituvchi uchun)
"""
from datetime import date
from telegram.ext import ContextTypes

from config import db, ATTENDANCE_EMOJI
from utils.keyboards import kb_student_attendance


async def start_attendance(update_or_query, context: ContextTypes.DEFAULT_TYPE,
                            date_str: str):
    """
    Davomat olishni boshlaydi.
    subject_id=0 bo'lsa — fansiz (admin rejimi).
    """
    class_id   = context.user_data.get("att_class_id") or context.user_data.get("teacher_class")
    subject_id = context.user_data.get("att_subject_id") or context.user_data.get("teacher_subject") or 0
    students   = db.get_whitelist_by_class(class_id)

    if not students:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        cls  = db.get_class(class_id)
        name = cls['name'] if cls else "Bu sinf"
        await update_or_query.edit_message_text(
            f"❌ *{name}* sinfida hali o'quvchi qo'shilmagan.\n\n"
            f"Davomat olish uchun avval admin o'quvchilarni qo'shishi kerak.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="cancel")
            ]])
        )
        return

    rows = db.get_attendance(class_id, subject_id, date_str)
    existing          = {str(a["student_id"]): a["status"]  for a in rows}
    existing_comments = {str(a["student_id"]): a["comment"] for a in rows if a["comment"]}

    context.user_data["attendance_date"]     = date_str
    context.user_data["attendance_data"]     = existing.copy()
    context.user_data["attendance_comments"] = existing_comments.copy()
    context.user_data["attendance_students"] = [s["telegram_id"] for s in students]

    await show_attendance(update_or_query, context, students, date_str, is_new=True)


async def show_attendance(update_or_query, context: ContextTypes.DEFAULT_TYPE,
                           students: list, date_str: str, is_new: bool = False):
    """Davomat klaviaturasini ko'rsatadi yoki yangilaydi"""
    class_id   = context.user_data.get("att_class_id") or context.user_data.get("teacher_class")
    subject_id = context.user_data.get("att_subject_id") or context.user_data.get("teacher_subject") or 0
    cls        = db.get_class(class_id)
    att_data   = context.user_data.get("attendance_data", {})
    comments   = context.user_data.get("attendance_comments", {})

    d = date.fromisoformat(date_str).strftime("%d.%m.%Y")

    # Fan nomi — faqat subject_id > 0 bo'lganda ko'rsatiladi
    if subject_id:
        subj = db.get_subject(subject_id)
        subj_line = f" | 📚 {subj['name']}" if subj else ""
    else:
        subj_line = ""

    text = (
        f"📋 *Davomat* | 🏫 {cls['name']}{subj_line}\n"
        f"📅 {d}\n\n"
        f"✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli\n"
        f"_(O'quvchi nomiga bosing — holat o'zgaradi)_\n"
        f"_💬 — izoh kiritilgan_"
    )
    markup = kb_student_attendance(students, att_data, comments)

    if is_new:
        if hasattr(update_or_query, "message") and update_or_query.message:
            await update_or_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await update_or_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        try:
            await update_or_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            pass


def next_status(current: str) -> str:
    """present → absent → late → excused → present"""
    return {
        "present": "absent",
        "absent":  "late",
        "late":    "excused",
        "excused": "present",
    }.get(current, "present")