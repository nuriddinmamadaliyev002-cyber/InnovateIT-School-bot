"""
panels/super/waiting.py — Super Admin waiting holatlari

  sup_new_school    — yangi maktab nomi
  sup_rename_school — maktab nomini o'zgartirish
  sup_admin_id      — yangi admin Telegram ID
  sup_admin_name    — yangi admin ismi
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_super_admin, kb_cancel


async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting: str):
    text = update.message.text or ""

    if waiting == 'sup_new_school':
        name = text.strip()
        if not name:
            await update.message.reply_text("❌ Maktab nomi bo'sh bo'lishi mumkin emas.")
            return
        db.add_school(name)
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(
            f"✅ *{name}* maktabi qo'shildi!",
            parse_mode="Markdown",
            reply_markup=kb_super_admin()
        )

    elif waiting == 'sup_rename_school':
        name = text.strip()
        sid  = context.user_data.pop('tmp_school_id', None)
        if not name or not sid:
            await update.message.reply_text("❌ Xato. Qaytadan urinib ko'ring.")
            return
        # Nomni o'zgartirish — add_school UNIQUE constraint bor, shuning uchun update:
        with db.conn() as c:
            c.execute("UPDATE schools SET name=? WHERE id=?", (name, sid))
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(f"✅ Maktab nomi *{name}* ga o'zgartirildi.", parse_mode="Markdown")

    elif waiting == 'sup_admin_id':
        try:
            tid = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Telegram ID son bo'lishi kerak.")
            return
        context.user_data['tmp_admin_id'] = tid
        context.user_data['waiting_for']  = 'sup_admin_name'
        await update.message.reply_text(
            f"👤 ID: `{tid}`\n\nAdmin ismini (to'liq ism) kiriting:",
            parse_mode="Markdown",
            reply_markup=kb_cancel()
        )

    elif waiting == 'sup_admin_name':
        name   = text.strip()
        tid    = context.user_data.pop('tmp_admin_id', None)
        sid    = context.user_data.pop('tmp_school_id', None)
        if not name or not tid or not sid:
            await update.message.reply_text("❌ Ma'lumotlar to'liq emas. Qaytadan urinib ko'ring.")
            return
        db.add_school_admin(tid, sid, name)
        school = db.get_school(sid)
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(
            f"✅ *{name}* admin sifatida tayinlandi!\n"
            f"🏫 Maktab: *{school['name']}*\n"
            f"🆔 Telegram ID: `{tid}`",
            parse_mode="Markdown",
            reply_markup=kb_super_admin()
        )
