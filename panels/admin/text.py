"""
panels/admin/text.py — Maktab Admin reply keyboard tugmalari
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_school_admin, kb_teacher_att_dates


def _sid(context) -> int:
    return context.user_data.get('school_id', 1)


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text      = update.message.text
    school_id = _sid(context)
    school    = db.get_school(school_id)
    sname     = school['name'] if school else "Maktab"

    context.user_data.pop('waiting_for', None)

    if text == "🔙 Super Admin paneli":
        from panels.super.text import handle_super_text
        await handle_super_text(update, context)
        return

    if text == "👥 O'quvchilar":
        # O'quvchilar sinf orqali boshqariladi
        classes = db.get_classes(school_id)
        if not classes:
            await update.message.reply_text(
                "❌ Avval sinf qo'shing.", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Sinf qo'shish", callback_data="adm_add_class")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(
                f"🏫 {c['name']} ({len(db.get_whitelist_by_class(c['id']))} o'q)",
                callback_data=f"adm_students_of_{c['id']}"
            )]
            for c in classes
        ]
        buttons.append([InlineKeyboardButton("➕ O'quvchi qo'shish", callback_data="adm_add_student")])
        archived_all = db.get_archived_students(school_id)
        if archived_all:
            buttons.append([InlineKeyboardButton(f"📦 Arxivlangan o'quvchilar ({len(archived_all)} ta)", callback_data="adm_all_archived_students")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
        await update.message.reply_text(
            f"👥 *{sname} — O'quvchilar:*\n\nSinf tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif text == "🏫 Sinflar":
        classes = db.get_classes(school_id)
        if not classes:
            await update.message.reply_text(
                "❌ Hali sinf qo'shilmagan.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Sinf qo'shish", callback_data="adm_add_class")
                ]])
            )
            return
        buttons = []
        for c in classes:
            subjects = db.get_subjects(class_id=c['id'])
            stu_cnt  = len(db.get_whitelist_by_class(c['id']))
            subj_cnt = len(subjects)
            buttons.append([InlineKeyboardButton(
                f"🏫 {c['name']}  ({subj_cnt} fan | {stu_cnt} o'q)",
                callback_data=f"adm_class_card_{c['id']}"
            )])
        buttons.append([InlineKeyboardButton("➕ Sinf qo'shish", callback_data="adm_add_class")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
        await update.message.reply_text(
            "🏫 *Sinflar ro'yxati:*\n_(sinfga bosib batafsil ko'ring)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif text == "📚 Fanlar":
        await update.message.reply_text(
            f"📚 *{sname} — Fanlar:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Fan yaratish",          callback_data="adm_add_subject")],
                [InlineKeyboardButton("📋 Fanlar ro'yxati",       callback_data="adm_list_subjects")],
                [InlineKeyboardButton("🔗 Fanni sinfga biriktir", callback_data="adm_assign_subject")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")],
            ])
        )

    elif text == "👨‍🏫 O'qituvchilar":
        await update.message.reply_text(
            f"👨‍🏫 *{sname} — O'qituvchilar:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ O'qituvchi qo'shish",   callback_data="adm_add_teacher")],
                [InlineKeyboardButton("📋 O'qituvchilar ro'yxati", callback_data="adm_list_teachers")],
                [InlineKeyboardButton("🔗 O'qituvchini biriktirish", callback_data="adm_assign_teacher")],
                [InlineKeyboardButton("👥 Sinf guruhlari", callback_data="adm_list_groups")],  # YANGI
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")],
            ])
        )

    elif text == "📅 O'qituvchi jadvali":
        slots = db.get_slots(school_id=school_id)
        await update.message.reply_text(
            f"📅 *O'qituvchilar haftalik dars jadvali*\n\n"
            f"{'✅ Jadval mavjud.' if slots else '❌ Jadval hali kiritilmagan.'}\n\n"
            f"Quyidagi amallardan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Jadval yaratish/tahrirlash", callback_data="tws_start")],
                [InlineKeyboardButton("👁 Jadvalni ko'rish",           callback_data="tws_view")],
                [InlineKeyboardButton("🔙 Orqaga",                     callback_data="adm_main_menu")],
            ])
        )

    elif text == "📋 O'quvchi davomati":
        classes = db.get_classes(school_id)
        if not classes:
            await update.message.reply_text(
                "❌ Hali sinf qo'shilmagan.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Sinf qo'shish", callback_data="adm_add_class"),
                    InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")
                ]])
            )
            return
        btns = [
            [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"adm_att_class_{c['id']}")]
            for c in classes
        ]
        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
        await update.message.reply_text(
            f"📋 *{sname} — O'quvchilar davomati*\n\nSinf tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif text == "📋 O'qituvchi davomati":
        await update.message.reply_text(
            "📋 *O'qituvchilar davomati*\n\nKun tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_teacher_att_dates(school_id=school_id)
        )

    elif text == "🗓 Sinf dars jadvali":
        classes = db.get_classes(school_id)
        if not classes:
            await update.message.reply_text(
                "❌ Avval sinf qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Sinf qo'shish", callback_data="adm_add_class"),
                    InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(
                f"{'✅' if db.get_schedule(school_id=school_id, class_id=c['id']) else '❌'} {c['name']}",
                callback_data=f"adm_schedule_{c['id']}"
            )]
            for c in classes
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
        await update.message.reply_text(
            "🗓 *Dars jadvallari:* _(✅ yuklangan | ❌ yuklanmagan)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif text == "📊 Statistika":
        stats = db.get_school_stats(school_id)

        # students_active/archived kalitlari bo'lmasa fallback
        stu_active   = stats.get('students_active',   stats.get('students', 0))
        stu_archived = stats.get('students_archived', 0)
        tch_active   = stats.get('teachers_active',   stats.get('teachers', 0))
        tch_archived = stats.get('teachers_archived', 0)

        stu_line = f"👥 O'quvchilar: *{stu_active}* ta faol"
        if stu_archived:
            stu_line += f" | *{stu_archived}* ta arxivlangan"

        tch_line = f"👨‍🏫 O'qituvchilar: *{tch_active}* ta faol"
        if tch_archived:
            tch_line += f" | *{tch_archived}* ta arxivlangan"

        await update.message.reply_text(
            f"📊 *{sname} — Statistika:*\n\n"
            f"🏫 Sinflar: *{stats['classes']}* ta\n"
            f"{stu_line}\n"
            f"{tch_line}\n"
            f"📚 Fanlar: *{stats['subjects']}* ta",
            parse_mode="Markdown"
        )