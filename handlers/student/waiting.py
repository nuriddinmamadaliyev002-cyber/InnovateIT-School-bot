import psycopg2
import psycopg2.extras
"""
handlers/student/waiting.py — O'quvchi waiting holatlari

Holatlar:
  homework_submission  — vazifa topshirish (matn/fayl)
  student_extra_files  — qo'shimcha fayllar
"""
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import db, TASHKENT_TZ
from utils.media import extract_file


async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting: str):

    # ── Vazifa topshirish ─────────────────────────────────────────
    if waiting == 'homework_submission':
        subject_id = context.user_data.get('submit_subject_id')
        class_id   = context.user_data.get('submit_class_id')
        date_str   = context.user_data.get('submit_date')
        deadline   = context.user_data.get('submit_deadline')
        lesson_id  = context.user_data.get('submit_lesson_id')
        student_id = update.effective_user.id

        file_id, file_type, caption = extract_file(update.message)
        content = caption or update.message.text or ""

        if not content and not file_id:
            await update.message.reply_text("❌ Matn, rasm, video yoki fayl yuboring.")
            return

        # Deadline o'tganini tekshirish
        is_late = False
        if deadline:
            try:
                dl  = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
                is_late = now > dl
            except Exception:
                pass

        # Topshirmani saqlash (lesson_id bilan)
        submission_id = db.save_submission(
            student_id, subject_id, class_id, date_str,
            content, file_id, file_type or "text",
            lesson_id=lesson_id
        )

        # is_late ni yangilash
        if is_late:
            with db.conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
                    c.execute(
                        "UPDATE submissions SET is_late=1 WHERE id=%s",
                        (submission_id,)
                    )

                conn.commit()
        # Context ga submission_id saqlash (qo'shimcha fayllar uchun)
        context.user_data['tmp_submission_id'] = submission_id
        context.user_data['waiting_for']        = 'student_extra_files'

        late_txt = "\n⚠️ _Deadline o'tib ketgan — kech topshirildi!_" if is_late else ""
        subj = db.get_subject(subject_id)
        await update.message.reply_text(
            f"✅ *Vazifa qabul qilindi!*{late_txt}\n"
            f"📚 {subj['name'] if subj else ''} | 📅 {date_str}\n\n"
            f"📎 *Yana fayl qo'shmoqchimisiz?*\n"
            f"_(Yuboring yoki ✅ Tayyor tugmasini bosing)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Tayyor", callback_data="sub_done")
            ]])
        )

    # ── Qo'shimcha fayllar ────────────────────────────────────────
    elif waiting == 'student_extra_files':
        submission_id = context.user_data.get('tmp_submission_id')
        if not submission_id:
            context.user_data.pop('waiting_for', None)
            return

        file_id, file_type, _ = extract_file(update.message)
        if file_id:
            db.add_submission_file(submission_id, file_id, file_type)
            await update.message.reply_text(
                "✅ Fayl biriktirildi.\n📎 Yana fayl yuboring yoki ✅ Tayyor bosing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Tayyor", callback_data="sub_done")
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ Fayl yuborilmadi. Rasm, video yoki hujjat yuboring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Tayyor", callback_data="sub_done")
                ]])
            )