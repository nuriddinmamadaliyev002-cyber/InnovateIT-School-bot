"""
handlers/teacher/text.py — O'qituvchi reply keyboard tugmalari
"""
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db, WEEKDAY_LABELS
from utils.keyboards import kb_classes


def _school_badge(teacher: dict) -> str:
    """Joriy maktab nomi — barcha xabarlarga qo'shiladi."""
    return f"🏫 _{teacher['school_name']}_\n"


async def handle_teacher_switch_school(
    update: Update, context: ContextTypes.DEFAULT_TYPE, teachers: list
):
    """2+ maktabda ishlaydigan o'qituvchi maktabni almashtiradi."""
    current_school_id = context.user_data.get("teacher_school_id")

    buttons = []
    for t in teachers:
        is_current = t["school_id"] == current_school_id
        label = f"{'✅ ' if is_current else '🏫 '}{t['school_name']}"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"select_school_{t['school_id']}")
        ])

    current = next((t for t in teachers if t["school_id"] == current_school_id), teachers[0])
    await update.message.reply_text(
        f"🔄 *Maktabni tanlang*\n\n"
        f"Hozir: ✅ *{current['school_name']}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_teacher_text(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher: dict):
    text = update.message.text
    context.user_data.clear()
    # clear() dan keyin teacher ma'lumotlarini qayta tiklaymiz
    context.user_data["teacher_school_id"] = teacher["school_id"]
    context.user_data["teacher_id"] = teacher["id"]

    teacher_id = teacher['id']
    badge = _school_badge(teacher)

    classes = db.get_teacher_classes(teacher_id)

    if not classes and text not in ("🗓 Dars jadvali", "📊 Mening davomatim"):
        from utils.keyboards import kb_cancel_teacher
        await update.message.reply_text(
            f"{badge}\n❌ Sizga hali sinf biriktirilmagan.\n\n"
            "Admin → O'qituvchilar → Sinf kartasi → O'qituvchi biriktirish.",
            parse_mode="Markdown",
            reply_markup=kb_cancel_teacher()
        )
        return

    if text == "📝 Uyga vazifa":
        await update.message.reply_text(
            f"{badge}📝 *Uyga vazifa* — nima qilmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Vazifa qo'shish",       callback_data="tch_hw_add")],
                [InlineKeyboardButton("✏️ Vazifalarni tahrirlash", callback_data="tch_hw_edit_list")],
            ])
        )

    elif text == "📖 Mavzu":
        context.user_data['teacher_action'] = 'add_topic'
        await update.message.reply_text(
            f"{badge}📖 *Mavzu qo'shish* — Sinf tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_classes(classes, prefix="tch_class")
        )

    elif text == "📨 O'quvchi vazifalari":
        context.user_data['teacher_action'] = 'view_submissions'
        await update.message.reply_text(
            f"{badge}📨 *O'quvchi vazifalari* — Sinf tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_classes(classes, prefix="tch_sub_class")
        )

    elif text == "🗓 Dars jadvali":
        all_teachers = db.get_teachers_by_telegram_id(teacher['telegram_id'])

        if not all_teachers:
            await update.message.reply_text("❌ Ma'lumot topilmadi.")
            return

        all_slots = []
        schools_map = {}

        for t in all_teachers:
            slots = db.get_slots(teacher_id=t['id'])
            all_slots.extend(slots)
            schools_map[t['id']] = t['school_name']

        if not all_slots:
            await update.message.reply_text(
                f"{badge}❌ Sizning dars jadvalingiz hali kiritilmagan.\nAdmin bilan bog'laning.",
                parse_mode="Markdown"
            )
            return

        grouped = {}
        for s in all_slots:
            grouped.setdefault(s['weekday'], []).append(s)

        if len(all_teachers) == 1:
            lines = [
                f"📅 *{teacher['full_name']} — Haftalik jadval*\n"
                f"🏫 *{all_teachers[0]['school_name']}*\n"
            ]
        else:
            schools_list = ", ".join([t['school_name'] for t in all_teachers])
            lines = [
                f"📅 *{teacher['full_name']} — Haftalik jadval*\n"
                f"🏫 *Maktablar:* {schools_list}\n"
            ]

        for day in sorted(grouped):
            lines.append(f"\n*{WEEKDAY_LABELS[day]}:*")
            for s in grouped[day]:
                if len(all_teachers) > 1:
                    school_name = schools_map.get(s['teacher_id'], '?')
                    lines.append(
                        f"  • {school_name} - {s['class_name']} | {s['subject_name']} | {s['start_time']}-{s['end_time']}"
                    )
                else:
                    lines.append(
                        f"  • {s['class_name']} | {s['subject_name']} | {s['start_time']}-{s['end_time']}"
                    )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Yuklab olish", callback_data="tch_schedule_download_menu")],
            ])
        )

    elif text == "⭐ O'quvchilarni baholash":
        context.user_data['teacher_action'] = 'grading'
        btns = [
            [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"grade_class_{c['id']}")]
            for c in classes
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        await update.message.reply_text(
            f"{badge}⭐ *O'quvchilarni baholash* — Sinf tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif text == "🏆 Reyting":
        btns = [
            [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"rating_class_{c['id']}")]
            for c in classes
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        await update.message.reply_text(
            f"{badge}🏆 *Reyting* — Sinf tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif text == "📊 Mening davomatim":
        month = date.today().strftime("%Y-%m")
        records = db.get_teacher_attendance_for_teacher(teacher_id, month)
        STATUS_EMOJI = {'present': '✅', 'absent': '❌', 'late': '⏰'}
        STATUS_LABEL = {'present': 'Keldi', 'absent': 'Kelmadi', 'late': 'Kech keldi'}
        present = sum(1 for r in records if r['status'] == 'present')
        absent  = sum(1 for r in records if r['status'] == 'absent')
        late    = sum(1 for r in records if r['status'] == 'late')
        lines = [
            f"{badge}📊 *Mening davomatim — {month}*\n",
            f"✅ Keldi: *{present}* kun",
            f"❌ Kelmadi: *{absent}* kun",
            f"⏰ Kech keldi: *{late}* kun",
        ]
        if records:
            lines.append("\n📋 *Kunlar bo'yicha:*")
            for r in records:
                emoji = STATUS_EMOJI.get(r['status'], '?')
                label = STATUS_LABEL.get(r['status'], r['status'])
                lines.append(f"  {emoji} {r['date']} — {label}")
        else:
            lines.append("\n❌ Bu oy uchun ma'lumot yo'q.")
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📅 Oldingi oy", callback_data=f"tch_att_prev_{teacher_id}")
            ]])
        )