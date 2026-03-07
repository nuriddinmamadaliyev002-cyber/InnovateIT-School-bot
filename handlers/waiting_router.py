"""
handlers/waiting_router.py — Barcha 'waiting_for' holatlarini to'g'ri modulga yo'naltiradi

Waiting holat prefikslari:
  add_*       → panels/admin/waiting.py
  sup_*       → panels/super/waiting.py
  tch_*       → handlers/teacher/waiting.py
  *_submission, student_* → handlers/student/waiting.py
  custom_date → universal
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import db
from utils.auth import is_super_admin

# Admin/Teacher menyusi tugmalari — waiting ni bekor qiladi
MENU_BUTTONS = {
    "👥 O'quvchilar", "🏫 Sinflar", "📚 Fanlar", "📝 Vazifa/Mavzu",
    "👨‍🏫 O'qituvchilar", "📥 Topshirmalar", "🗓 Dars jadvali", "📊 Statistika",
    "🔙 Super Admin paneli", "🏫 Maktablar", "👨‍💼 Maktab adminlari",
    "📊 Umumiy statistika", "📅 O'qit. jadvali", "📋 O'qit. davomati",
    "📋 O'quvchilar davomati",
    "📝 Uyga vazifa", "📖 Mavzu", "📊 Mening davomatim",
    "📚 Bugungi vazifalar", "📖 Bugungi mavzular",
    "📋 Hamma mavzu va vazifalar",
}

# Waiting prefiksi → modul yo'li
WAITING_ROUTES = {
    # Admin — barcha 'adm_' prefiksli waiting holatlar
    "adm_new_class":      "panels.admin.waiting",
    "adm_rename_class":   "panels.admin.waiting",
    "adm_student_id":     "panels.admin.waiting",
    "adm_student_name":   "panels.admin.waiting",
    "adm_student_class":  "panels.admin.waiting",
    "adm_new_subject":    "panels.admin.waiting",
    "adm_rename_subject": "panels.admin.waiting",
    "adm_teacher_id":     "panels.admin.waiting",
    "adm_upd_student_id": "panels.admin.waiting",
    "adm_upd_teacher_id": "panels.admin.waiting",
    "adm_teacher_name":   "panels.admin.waiting",
    "adm_lesson_date":    "panels.admin.waiting",
    "adm_lesson_content": "panels.admin.waiting",
    "adm_schedule_file":  "panels.admin.waiting",
    "adm_att_custom_date": "panels.admin.waiting",
    # Super Admin — barcha 'sup_' prefiksli waiting holatlar
    "sup_new_school":    "panels.super.waiting",
    "sup_rename_school": "panels.super.waiting",
    "sup_admin_id":      "panels.super.waiting",
    "sup_admin_name":    "panels.super.waiting",
    # O'qituvchi
    "tch_lesson_content": "handlers.teacher.waiting",
    "tch_extra_files":    "handlers.teacher.waiting",
    "tch_lesson_date":    "handlers.teacher.waiting",
    "tch_deadline":       "handlers.teacher.waiting",
    "tws_time":           "handlers.teacher.waiting",
    "tws_edit_time":      "handlers.teacher.waiting",
    "tch_edit_content":   "handlers.teacher.waiting",
    "tch_edit_comment":   "handlers.teacher.waiting",
    "tch_edit_deadline":  "handlers.teacher.waiting",
    "tch_replace_file":   "handlers.teacher.waiting",
    "tch_sub_comment":    "handlers.teacher.waiting",
    "tch_sub_cmt_file":   "handlers.teacher.waiting",
    # O'qituvchi davomati izoh
    "tadm_comment":       "handlers.teacher.waiting",
    "att_comment":         "handlers.teacher.waiting",
    # O'quvchi
    "homework_submission": "handlers.student.waiting",
    "student_extra_files": "handlers.student.waiting",
    # Universal
    "custom_date":         "universal",
}


async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting: str):
    text = update.message.text or ""
    user_id = update.effective_user.id

    # Menyu tugmasi bosildimi — waiting ni bekor qil
    if text in MENU_BUTTONS:
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("tmp_class_id", None)
        _dispatch_menu(update, context, text, user_id)
        return

    # Custom date — universal holat
    if waiting == "custom_date":
        await _handle_custom_date(update, context, text)
        return

    # Modul aniqla
    module_path = _find_route(waiting)
    if not module_path:
        context.user_data.pop("waiting_for", None)
        return

    # Dinamik import
    import importlib
    module = importlib.import_module(module_path)
    await module.handle_waiting(update, context, waiting)


def _find_route(waiting: str) -> str:
    for prefix, path in WAITING_ROUTES.items():
        if waiting.startswith(prefix):
            return path
    return ""


def _dispatch_menu(update, context, text, user_id):
    import asyncio
    from handlers.message_router import handle_message
    # Asyncio task — context allaqachon tozalangan
    asyncio.create_task(handle_message(update, context))


async def _handle_custom_date(update, context, text: str):
    """Qo'lda sana kiritish: KK/OO/YYYY"""
    from datetime import datetime
    from utils.keyboards import kb_dates, kb_cancel
    try:
        d = datetime.strptime(text.strip(), "%d/%m/%Y").date()
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format. *KK/OO/YYYY* ko'rinishida kiriting:\n"
            "Masalan: *20/02/2026*",
            parse_mode="Markdown",
            reply_markup=kb_cancel("back_dates")
        )
        return

    context.user_data.pop("waiting_for", None)
    context.user_data["selected_date"] = d.isoformat()

    wl = context.user_data.get("student_class_id")
    if wl:
        # O'quvchi fan tanlashga o'tadi
        from handlers.student.text import show_subjects_for_date
        await show_subjects_for_date(update, context, d.isoformat())
    else:
        await update.message.reply_text(
            f"📅 Tanlangan sana: *{d.strftime('%d.%m.%Y')}*",
            parse_mode="Markdown",
            reply_markup=kb_dates()
        )