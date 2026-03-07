"""
panels/super/text.py — Super Admin reply keyboard tugmalari
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_super_admin


async def handle_super_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔙 Super Admin paneli":
        context.user_data.pop('school_id', None)
        context.user_data.pop('waiting_for', None)
        schools = db.get_schools()
        await update.message.reply_text(
            f"🔑 *Super Admin paneli*\n🏫 Maktablar: *{len(schools)}* ta",
            parse_mode="Markdown",
            reply_markup=kb_super_admin()
        )
        return

    context.user_data.pop('waiting_for', None)

    if text == "🏫 Maktablar":
        await _show_schools(update)

    elif text == "👨‍💼 Maktab adminlari":
        await _show_all_admins(update)

    elif text == "📊 Umumiy statistika":
        stats = db.get_global_stats()
        schools = db.get_schools()
        await update.message.reply_text(
            f"📊 *Umumiy statistika:*\n\n"
            f"🏫 Maktablar: *{len(schools)}* ta\n"
            f"👥 O'quvchilar: *{stats['students']}* ta\n"
            f"👨‍🏫 O'qituvchilar: *{stats['teachers']}* ta\n"
            f"🌐 Telegram foydalanuvchilar: *{stats['users']}* ta",
            parse_mode="Markdown"
        )


async def _show_schools(update):
    schools = db.get_schools()
    if not schools:
        await update.message.reply_text(
            "🏫 Hali maktab yo'q.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Maktab qo'shish", callback_data="sup_add_school")
            ]])
        )
        return
    buttons = []
    for s in schools:
        st = db.get_school_stats(s['id'])
        buttons.append([InlineKeyboardButton(
            f"🏫 {s['name']}  ({st['students']} o'quvchilar | {st['teachers']} o'qituvchilar)",
            callback_data=f"sup_school_{s['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Maktab qo'shish", callback_data="sup_add_school")])
    await update.message.reply_text(
        "🏫 *Maktablar ro'yxati:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def _show_all_admins(update):
    admins = db.get_school_admins()
    if not admins:
        await update.message.reply_text(
            "👨‍💼 Hali maktab admini yo'q.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Admin tayinlash", callback_data="sup_add_admin")
            ]])
        )
        return
    buttons = []
    for a in admins:
        buttons.append([
            InlineKeyboardButton(f"👨‍💼 {a['full_name']}  ({a['school_name']})", callback_data="noop"),
            InlineKeyboardButton("🗑️", callback_data=f"sup_del_admin_{a['telegram_id']}_{a['school_id']}"),
        ])
    buttons.append([InlineKeyboardButton("➕ Admin tayinlash", callback_data="sup_add_admin")])
    await update.message.reply_text(
        "👨‍💼 *Maktab adminlari:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
