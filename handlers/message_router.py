"""
handlers/message_router.py — Barcha xabarlar uchun markaziy routing

bot.py dagi MessageHandler shu funksiyani chaqiradi.
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import db, logger
from utils.auth import is_super_admin

# Super Admin paneli tugmalari — boshqa rol handlerlarga o'tkazilmasin
SUPER_ONLY = {
    "🏫 Maktablar", "👨‍💼 Maktab adminlari",
    "📊 Umumiy statistika", "🔙 Super Admin paneli",
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id
    waiting = context.user_data.get("waiting_for", "")

    # ── Waiting holat ─────────────────────────────────────────────
    if waiting and (update.message.text or update.message.photo
                    or update.message.document or update.message.video):
        from handlers.waiting_router import handle_waiting
        await handle_waiting(update, context, waiting)
        return

    text = update.message.text or ""

    # ── Super Admin ───────────────────────────────────────────────
    if is_super_admin(user_id):
        if text in SUPER_ONLY or not context.user_data.get("school_id"):
            from panels.super.text import handle_super_text
            await handle_super_text(update, context)
        else:
            from panels.admin.text import handle_admin_text
            await handle_admin_text(update, context)
        return

    # ── Maktab Admin ──────────────────────────────────────────────
    sa = db.get_school_admin(user_id)
    if sa:
        context.user_data["school_id"] = sa["school_id"]
        from panels.admin.text import handle_admin_text
        await handle_admin_text(update, context)
        return

    # ── O'qituvchi ────────────────────────────────────────────────
    teachers = db.get_teachers_by_telegram_id(user_id)
    if teachers:
        # Ko'p maktabli: context dagi school_id ga qarab to'g'ri yozuvni olish
        school_id = context.user_data.get("teacher_school_id")
        if school_id:
            teacher = next(
                (t for t in teachers if t["school_id"] == school_id), teachers[0]
            )
        else:
            teacher = teachers[0]
            context.user_data["teacher_school_id"] = teacher["school_id"]
            context.user_data["teacher_id"] = teacher["id"]

        # Maktabni almashtirish tugmasi bosildi
        if text == "🔄 Maktabni almashtirish":
            from handlers.teacher.text import handle_teacher_switch_school
            await handle_teacher_switch_school(update, context, teachers)
            return

        from handlers.teacher.text import handle_teacher_text
        await handle_teacher_text(update, context, teacher)
        return

    # ── O'quvchi ─────────────────────────────────────────────────
    wl = db.get_whitelist_user(user_id)
    if wl:
        from handlers.student.text import handle_student_text
        await handle_student_text(update, context, wl)
        return

    # ── Noma'lum ─────────────────────────────────────────────────
    from handlers.start import cmd_start
    await cmd_start(update, context)