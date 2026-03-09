"""
handlers/student/text.py — O'quvchi reply keyboard tugmalari

Yangiliklar (v2):
  "Hamma mavzu va vazifalar" → endi homework sanalar ro'yxatini ko'rsatadi
"""
from datetime import date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_subjects, kb_dates


async def handle_student_text(update: Update, context: ContextTypes.DEFAULT_TYPE, wl: dict):
    text       = update.message.text
    class_id   = wl['class_id']
    class_name = wl['class_name']
    student_id = wl['telegram_id']
    today_str  = date.today().isoformat()

    context.user_data['student_class_id'] = class_id

    if text == "📚 Bugungi vazifalar":
        subjects = db.get_subjects(class_id=class_id)
        if not subjects:
            await update.message.reply_text("❌ Bu sinfda fan qo'shilmagan.")
            return
        await update.message.reply_text(
            "📚 *Bugungi vazifalar* — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_subjects(subjects, prefix=f"view_hw_{today_str}",
                                     back=f"stu_subj_list_hw_{today_str}")
        )

    elif text == "📖 Bugungi mavzular":
        subjects = db.get_subjects(class_id=class_id)
        if not subjects:
            await update.message.reply_text("❌ Bu sinfda fan qo'shilmagan.")
            return
        await update.message.reply_text(
            "📖 *Bugungi mavzular* — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_subjects(subjects, prefix=f"view_topic_{today_str}",
                                     back=f"stu_subj_list_topic_{today_str}")
        )

    elif text == "📋 Hamma mavzu va vazifalar":
        await update.message.reply_text(
            "📋 *Hamma mavzu va vazifalar*\n\nQaysi bo'limni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Vazifalar",  callback_data="hmv_hw")],
                [InlineKeyboardButton("📖 Mavzular",   callback_data="hmv_topics")],
            ])
        )

    elif text == "🗓 Dars jadvali":
        schedule = db.get_schedule(school_id=wl['school_id'], class_id=class_id)
        if not schedule:
            await update.message.reply_text(
                "🗓 *Dars jadvali*\n\n❌ Hali dars jadvali yuklanmagan.",
                parse_mode="Markdown"
            )
        else:
            caption = f"🗓 *{class_name} — Dars jadvali*"
            if schedule['file_type'] == 'photo':
                await update.message.reply_photo(
                    schedule['file_id'], caption=caption, parse_mode="Markdown"
                )
            else:
                await update.message.reply_document(
                    schedule['file_id'], caption=caption, parse_mode="Markdown"
                )

    elif text == "📊 Mening davomatim":
        records = db.get_student_attendance(student_id)
        if not records:
            await update.message.reply_text(
                "📊 *Mening davomatim*\n\n❌ Hozircha davomat ma'lumoti yo'q.",
                parse_mode="Markdown"
            )
            return
        stats = db.get_attendance_stats(student_id)
        await update.message.reply_text(
            f"📊 *Mening davomatim*\n\n"
            f"✅ Keldi: *{stats['present']}* kun\n"
            f"❌ Kelmadi: *{stats['absent']}* kun\n"
            f"⏰ Kech keldi: *{stats['late']}* kun\n"
            f"📈 Davomat: *{stats['percent']}%*",
            parse_mode="Markdown"
        )

    elif text == "⭐ Baholarim":
        from config import WEEKDAY_UZ
        
        # Oxirgi 10 kundan yakshanba (6) bo'lmaganlarini tanlaymiz
        buttons = []
        days_added = 0
        check_day = 0
        
        while days_added < 3 and check_day < 30:  # Max 30 kun orqaga
            check_date = date.today() - timedelta(days=check_day)
            weekday = check_date.weekday()  # 0=Dushanba, 6=Yakshanba
            
            # Yakshanba (6) bo'lmasa qo'shamiz
            if weekday != 6:
                weekday_name = WEEKDAY_UZ.get(check_date.strftime('%A'), '')
                date_str = check_date.strftime('%d.%m.%Y')
                
                # Bugun va kecha so'zlarini qo'shamiz
                if check_day == 0:
                    label = f"📅 Bugun, {weekday_name} ({date_str})"
                elif check_day == 1:
                    label = f"📅 Kecha, {weekday_name} ({date_str})"
                else:
                    label = f"📅 {weekday_name} ({date_str})"
                
                buttons.append([InlineKeyboardButton(
                    label,
                    callback_data=f"stu_grades_date_{check_date.isoformat()}"
                )])
                days_added += 1
            
            check_day += 1
        
        await update.message.reply_text(
            "⭐ *Baholarim* — Qaysi kunni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif text == "🏆 Mening reytingim":
        await update.message.reply_text(
            "🏆 *Mening reytingim*\n\n"
            "_Batafsil ma'lumot uchun o'qituvchingizga murojaat qiling._",
            parse_mode="Markdown"
        )