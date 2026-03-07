"""
panels/admin/waiting.py — Maktab Admin waiting holatlari

Prefixlar:
  adm_new_class       — yangi sinf nomi
  adm_rename_class    — sinf nomi o'zgartirish
  adm_student_id      — yangi o'quvchi Telegram ID
  adm_student_name    — yangi o'quvchi ismi
  adm_new_subject     — yangi fan nomi
  adm_rename_subject  — fan nomi o'zgartirish
  adm_teacher_id      — yangi o'qituvchi Telegram ID
  adm_teacher_name    — yangi o'qituvchi ismi
  adm_schedule_file   — dars jadvali fayli
"""
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_classes, kb_cancel
from utils.media import extract_file


def _sid(context) -> int:
    return context.user_data.get('school_id', 1)


async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting: str):
    text      = update.message.text or ""
    school_id = _sid(context)

    # ── SINFLAR ──────────────────────────────────────────────────

    if waiting == 'adm_new_class':
        name = text.strip()
        if not name:
            await update.message.reply_text("❌ Sinf nomi bo'sh bo'lishi mumkin emas.")
            return
        db.add_class(name, school_id)
        # waiting_for saqlanib qoladi — yana sinf kiritish mumkin
        await update.message.reply_text(
            f"✅ *{name}* sinfi qo'shildi!\n\n"
            f"➕ Yana sinf nomini kiriting yoki tugmani bosing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yana qo'shish",    callback_data="adm_add_class")],
                [InlineKeyboardButton("📋 Sinflar ro'yxati", callback_data="adm_list_classes")],
                [InlineKeyboardButton("✅ Tayyor",           callback_data="adm_done")],
            ])
        )

    elif waiting == 'adm_rename_class':
        name = text.strip()
        cid  = context.user_data.pop('tmp_class_id', None)
        if not name or not cid:
            return
        with db.conn() as c:
            c.execute("UPDATE classes SET name=? WHERE id=?", (name, cid))
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(f"✅ Sinf nomi *{name}* ga o'zgartirildi.", parse_mode="Markdown")

    # ── O'QUVCHILAR ──────────────────────────────────────────────

    elif waiting == 'adm_student_id':
        try:
            tid = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Telegram ID son bo'lishi kerak.")
            return

        # 1. Allaqachon o'quvchimi?
        existing = db.get_whitelist_user(tid)
        if existing:
            await update.message.reply_text(
                f"⚠️ Bu ID allaqachon *{existing['full_name']}* nomli o'quvchiga biriktirilgan\n"
                f"🏫 Sinf: *{existing['class_name']}* | Maktab: *{existing['school_name']}*",
                parse_mode="Markdown"
            )
            return

        # 2. O'qituvchimi?
        teachers = db.get_teachers_by_telegram_id(tid)
        if teachers:
            names = ", ".join(f"{t['full_name']} ({t['school_name']})" for t in teachers)
            await update.message.reply_text(
                f"⚠️ Bu ID allaqachon *o'qituvchi* sifatida ro'yxatda:\n"
                f"👨‍🏫 {names}",
                parse_mode="Markdown"
            )
            return

        # 3. Maktab admini yoki super admimi?
        sa = db.get_school_admin(tid)
        if sa:
            await update.message.reply_text(
                f"⚠️ Bu ID *{sa['full_name']}* — maktab adminiga biriktirilgan\n"
                f"🏫 Maktab: *{sa['school_name']}*",
                parse_mode="Markdown"
            )
            return

        from utils.auth import is_super_admin
        if is_super_admin(tid):
            await update.message.reply_text(
                f"⚠️ Bu ID *Super Admin* ga tegishli. O'quvchi sifatida qo'shib bo'lmaydi.",
                parse_mode="Markdown"
            )
            return

        context.user_data['tmp_student_id'] = tid
        context.user_data['waiting_for']    = 'adm_student_name'
        await update.message.reply_text(
            f"✅ ID: `{tid}`\n\nO'quvchining to'liq ismini kiriting:",
            parse_mode="Markdown"
        )

    elif waiting == 'adm_student_name':
        name = text.strip()
        tid  = context.user_data.get('tmp_student_id')
        if not name or not tid:
            return
        context.user_data['tmp_student_name'] = name
        context.user_data['waiting_for']      = 'adm_student_class'
        classes = db.get_classes(school_id)
        await update.message.reply_text(
            f"🏫 *{name}* — sinf tanlang:", parse_mode="Markdown",
            reply_markup=kb_classes(classes, prefix="adm_student_class")
        )

    # ── FANLAR ───────────────────────────────────────────────────

    elif waiting == 'adm_new_subject':
        name = text.strip()
        if not name:
            await update.message.reply_text("❌ Fan nomi bo'sh bo'lishi mumkin emas.")
            return
        # Fan maktab darajasida yaratiladi — sinfga bog'liq emas
        db.add_subject(name, school_id)
        # waiting_for saqlanib qoladi — yana fan kiritish mumkin
        await update.message.reply_text(
            f"✅ *{name}* fani qo'shildi!\n\n"
            f"➕ Yana fan nomini kiriting yoki tugmani bosing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yana qo'shish",    callback_data="adm_add_subject")],
                [InlineKeyboardButton("📋 Fanlar ro'yxati",  callback_data="adm_list_subjects")],
                [InlineKeyboardButton("✅ Tayyor",           callback_data="adm_done")],
            ])
        )

    elif waiting == 'adm_rename_subject':
        name = text.strip()
        sid  = context.user_data.pop('tmp_subject_id', None)
        if not name or not sid:
            return
        with db.conn() as c:
            c.execute("UPDATE subjects SET name=? WHERE id=?", (name, sid))
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(f"✅ Fan nomi *{name}* ga o'zgartirildi.", parse_mode="Markdown")

    # ── O'QITUVCHILAR ────────────────────────────────────────────

    elif waiting == 'adm_teacher_id':
        try:
            tid = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Telegram ID son bo'lishi kerak.")
            return

        # 1. Aynan shu maktabda o'qituvchimi?
        existing = db.get_teacher_with_school(tid, school_id)
        if existing:
            await update.message.reply_text(
                f"⚠️ *{existing['full_name']}* allaqachon sizning maktabingizda o'qituvchi sifatida qo'shilgan.",
                parse_mode="Markdown"
            )
            return

        # 2. O'quvchimi?
        wl = db.get_whitelist_user(tid)
        if wl:
            await update.message.reply_text(
                f"⚠️ Bu ID allaqachon *o'quvchi* sifatida ro'yxatda:\n"
                f"👤 *{wl['full_name']}* | 🏫 {wl['class_name']} ({wl['school_name']})",
                parse_mode="Markdown"
            )
            return

        # 3. Maktab admini yoki super admimi?
        sa = db.get_school_admin(tid)
        if sa:
            await update.message.reply_text(
                f"⚠️ Bu ID *{sa['full_name']}* — maktab adminiga biriktirilgan\n"
                f"🏫 Maktab: *{sa['school_name']}*",
                parse_mode="Markdown"
            )
            return

        from utils.auth import is_super_admin
        if is_super_admin(tid):
            await update.message.reply_text(
                f"⚠️ Bu ID *Super Admin* ga tegishli. O'qituvchi sifatida qo'shib bo'lmaydi.",
                parse_mode="Markdown"
            )
            return

        # 4. Boshqa maktabda mavjudligini tekshirish
        other_teachers = db.get_teachers_by_telegram_id(tid)
        if other_teachers:
            context.user_data['tmp_teacher_id']   = tid
            context.user_data['tmp_teacher_name'] = other_teachers[0]['full_name']
            context.user_data['waiting_for']      = 'adm_teacher_confirm'
            schools_list = ", ".join([t['school_name'] for t in other_teachers])
            await update.message.reply_text(
                f"ℹ️ *{other_teachers[0]['full_name']}* allaqachon boshqa maktabda ishlamoqda:\n"
                f"🏫 {schools_list}\n\n"
                f"Sizning maktabingizga ham biriktirmoqchimisiz?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Ha, biriktirish", callback_data="adm_confirm_add_teacher")],
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
                ])
            )
            return

        # 5. Butunlay yangi o'qituvchi
        context.user_data['tmp_teacher_id'] = tid
        context.user_data['waiting_for']    = 'adm_teacher_name'
        await update.message.reply_text(
            f"✅ ID: `{tid}`\n\nO'qituvchining to'liq ismini kiriting:", parse_mode="Markdown"
        )

    elif waiting == 'adm_teacher_name':
        name = text.strip()
        tid  = context.user_data.pop('tmp_teacher_id', None)
        if not name or not tid:
            return
        db.add_teacher(tid, school_id, name)
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(
            f"✅ *{name}* o'qituvchi sifatida qo'shildi!\n🆔 `{tid}`\n\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Yana o'qituvchi qo'shish", callback_data="adm_add_teacher")],
                [InlineKeyboardButton("📋 O'qituvchilar ro'yxati",   callback_data="adm_list_teachers")],
                [InlineKeyboardButton("✅ Tayyor",                   callback_data="adm_done")],
            ])
        )

    # ── DARS JADVALI ─────────────────────────────────────────────

    elif waiting == 'adm_schedule_file':
        class_id = context.user_data.get('tmp_class_id')
        file_id, file_type, _ = extract_file(update.message)
        if not file_id:
            await update.message.reply_text("❌ Rasm yoki PDF fayl yuboring.")
            return
        db.save_schedule(school_id, file_id, file_type or 'photo', class_id)
        context.user_data.pop('waiting_for', None)
        cls = db.get_class(class_id)
        await update.message.reply_text(
            f"✅ *{cls['name']}* dars jadvali yuklandi!", parse_mode="Markdown"
        )

    # ── TELEGRAM ID YANGILASH ─────────────────────────────────────

    elif waiting == 'adm_upd_student_id':
        try:
            new_id = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Telegram ID son bo'lishi kerak.")
            return

        old_id = context.user_data.pop('adm_upd_old_student_id', None)
        if not old_id:
            context.user_data.pop('waiting_for', None)
            return

        st = db.get_whitelist_user(old_id)
        if not st:
            await update.message.reply_text("❌ O'quvchi topilmadi.")
            context.user_data.pop('waiting_for', None)
            return

        success = db.update_student_telegram_id(old_id, new_id)
        context.user_data.pop('waiting_for', None)

        if not success:
            await update.message.reply_text(
                f"⚠️ *{new_id}* ID allaqachon boshqa foydalanuvchida mavjud.\n"
                f"Boshqa ID kiriting.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"✅ *{st['full_name']}* — ID yangilandi!\n\n"
            f"🔴 Eski ID: `{old_id}`\n"
            f"🟢 Yangi ID: `{new_id}`\n\n"
            f"📊 Barcha davomati, baholari va topshirmalari saqlanib qoldi.",
            parse_mode="Markdown"
        )
        # O'quvchiga xabar yuborish
        try:
            await update.message.bot.send_message(
                new_id,
                f"✅ *Sizning akkauntingiz yangilandi!*\n\n"
                f"👤 *{st['full_name']}*\n"
                f"🏫 Sinf: *{st['class_name']}*\n\n"
                f"/start bosing!",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    elif waiting == 'adm_upd_teacher_id':
        try:
            new_id = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Telegram ID son bo'lishi kerak.")
            return

        old_tid = context.user_data.pop('adm_upd_old_teacher_tid', None)
        if not old_tid:
            context.user_data.pop('waiting_for', None)
            return

        t = db.get_teacher(old_tid)
        if not t:
            await update.message.reply_text("❌ O'qituvchi topilmadi.")
            context.user_data.pop('waiting_for', None)
            return

        success = db.update_teacher_telegram_id(old_tid, new_id)
        context.user_data.pop('waiting_for', None)

        if not success:
            await update.message.reply_text(
                f"⚠️ *{new_id}* ID allaqachon boshqa o'qituvchida mavjud.\n"
                f"Boshqa ID kiriting.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"✅ *{t['full_name']}* — ID yangilandi!\n\n"
            f"🔴 Eski ID: `{old_tid}`\n"
            f"🟢 Yangi ID: `{new_id}`\n\n"
            f"📊 Barcha dars, davomat va baho ma'lumotlari saqlanib qoldi.",
            parse_mode="Markdown"
        )
        # O'qituvchiga xabar yuborish
        try:
            await update.message.bot.send_message(
                new_id,
                f"✅ *Sizning akkauntingiz yangilandi!*\n\n"
                f"👨‍🏫 *{t['full_name']}*\n"
                f"🏫 Maktab: *{t['school_name']}*\n\n"
                f"/start bosing!",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    # ── OTA-ONA TELEGRAM ID ──────────────────────────────────────

    elif waiting == 'adm_parent_telegram_id':
        text = text.strip()
        student_tid = context.user_data.get('tmp_parent_student_tid')
        if not student_tid:
            await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan boshlang.")
            context.user_data.pop('waiting_for', None)
            return

        # ID validatsiyasi
        try:
            parent_tid = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Noto'g'ri format. Faqat raqam kiriting:\n_(Masalan: 987654321)_",
                parse_mode="Markdown"
            )
            return

        st = db.get_whitelist_user(student_tid)
        if not st:
            await update.message.reply_text("❌ O'quvchi topilmadi.")
            context.user_data.pop('waiting_for', None)
            return

        # Tekshiruv: bu ID allaqachon boshqa rolda bormi?
        if db.get_whitelist_user(parent_tid):
            await update.message.reply_text(
                f"❌ `{parent_tid}` ID si allaqachon o'quvchi sifatida ro'yxatda!",
                parse_mode="Markdown"
            )
            return
        if db.is_school_admin(parent_tid):
            await update.message.reply_text(
                f"❌ `{parent_tid}` ID si maktab admin hisobi!",
                parse_mode="Markdown"
            )
            return

        # Tekshiruv: allaqachon boshqa o'quvchiga biriktirilganmi?
        existing_wl = db.get_student_by_parent(parent_tid)
        if existing_wl:
            await update.message.reply_text(
                f"❌ Bu ID allaqachon *{existing_wl['full_name']}* o'quvchisiga biriktirilgan!",
                parse_mode="Markdown"
            )
            return

        # Label so'rash
        context.user_data['tmp_parent_telegram_id'] = parent_tid
        context.user_data['waiting_for'] = 'adm_parent_label'
        from utils.keyboards import kb_cancel
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        await update.message.reply_text(
            f"👤 ID: `{parent_tid}`\n\n"
            f"Kim ekanligini tanlang yoki yozing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👨 Ota", callback_data="adm_parent_lbl_Ota"),
                 InlineKeyboardButton("👩 Ona", callback_data="adm_parent_lbl_Ona")],
                [InlineKeyboardButton("👤 Ota/Ona", callback_data="adm_parent_lbl_Ota/Ona")],
                [InlineKeyboardButton("❌ Bekor", callback_data=f"adm_student_card_{student_tid}")],
            ])
        )

    elif waiting == 'adm_parent_label':
        label       = text.strip() or "Ota/Ona"
        parent_tid  = context.user_data.pop('tmp_parent_telegram_id', None)
        student_tid = context.user_data.pop('tmp_parent_student_tid', None)
        context.user_data.pop('waiting_for', None)
        if not parent_tid or not student_tid:
            await update.message.reply_text("❌ Xatolik. Qaytadan boshlang.")
            return
        ok = db.add_student_parent(student_tid, parent_tid, label)
        st = db.get_whitelist_user(student_tid)
        if ok:
            await update.message.reply_text(
                f"✅ *{label}* ({parent_tid}) muvaffaqiyatli biriktirildi!\n\n"
                f"👤 O'quvchi: *{st['full_name'] if st else student_tid}*\n\n"
                f"Endi {label} /start buyrug'ini bosib farzandining ma'lumotlarini ko'rishi mumkin.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Biriktirishda xatolik. Bu ID allaqachon biriktirilgan bo'lishi mumkin."
            )

    elif waiting == 'adm_att_custom_date':
        # Admin qo'lda sana kiritib davomat oladi
        from datetime import datetime
        from utils.keyboards import kb_att_dates_for_class, kb_cancel
        class_id = context.user_data.get('att_class_id')
        try:
            d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        except ValueError:
            cls = db.get_class(class_id)
            await update.message.reply_text(
                "❌ Noto'g'ri format. *KK.OO.YYYY* ko'rinishida kiriting:\n"
                "Masalan: *03.03.2026*",
                parse_mode="Markdown",
                reply_markup=kb_cancel(f"adm_att_class_{class_id}")
            )
            return
        context.user_data.pop('waiting_for', None)
        context.user_data['att_subject_id'] = 0
        from handlers.teacher.attendance import start_attendance
        await start_attendance(update, context, d.isoformat())