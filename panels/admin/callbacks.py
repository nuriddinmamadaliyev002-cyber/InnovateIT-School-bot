"""
panels/admin/callbacks.py — Maktab Admin inline callback handlerlari

MANTIQ:
  Sinf yaratiladi → Sinfga fan biriktiriladi → Sinfga o'qituvchi biriktiriladi

  adm_*         — asosiy CRUD
  adm_class_*   — sinf kartasi (fan + o'qituvchi biriktirish markazi)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db
from utils.keyboards import kb_cancel, kb_classes


def _sid(context) -> int:
    return context.user_data.get('school_id', 1)


async def handle_admin_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    school_id = _sid(context)
    try:
        await _inner(query, context, data, school_id)
    except Exception as e:
        if "Message is not modified" in str(e):
            return
        raise


async def _class_card(query, context, class_id: int, school_id: int, msg: str = ""):
    """Sinf kartasi — fan va o'qituvchi biriktirishning asosiy sahifasi"""
    cls      = db.get_class(class_id)
    subjects = db.get_subjects(class_id=class_id)
    students = db.get_whitelist_by_class(class_id)

    subj_text = ", ".join(s['name'] for s in subjects) if subjects else "_(yo'q)_"
    stu_count = len(students)

    teachers_set = set()
    for s in subjects:
        for t in db.get_teachers_by_subject_class(s['id'], class_id):
            teachers_set.add(t['full_name'])
    tch_text = ", ".join(teachers_set) if teachers_set else "_(yo'q)_"

    text = (
        f"{msg}\n" if msg else ""
    ) + (
        f"🏫 *{cls['name']}*\n\n"
        f"📚 Fanlar: {subj_text}\n"
        f"👨‍🏫 O'qituvchilar: {tch_text}\n"
        f"👥 O'quvchilar: *{stu_count}* ta"
    )

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Fan biriktirish",        callback_data=f"adm_class_subj_{class_id}")],
            [InlineKeyboardButton("👨‍🏫 O'qituvchi biriktirish", callback_data=f"adm_class_tch_{class_id}")],
            [InlineKeyboardButton("👥 O'quvchilar",            callback_data=f"adm_students_of_{class_id}")],
            [InlineKeyboardButton("✏️ Nomini o'zgartirish",    callback_data=f"adm_rename_class_{class_id}")],
            [InlineKeyboardButton("🗑️ Sinfni o'chirish",       callback_data=f"adm_del_class_{class_id}")],
            [InlineKeyboardButton("🔙 Sinflar ro'yxati",       callback_data="adm_list_classes")],
        ])
    )


async def _inner(query, context, data, school_id):

    # ══════════════════════════════════════════════
    #  SINFLAR
    # ══════════════════════════════════════════════

    if data == "adm_add_class":
        context.user_data['waiting_for'] = 'adm_new_class'
        await query.edit_message_text(
            "🏫 Yangi sinf nomini kiriting:\n_(Masalan: 9-A, 10-B)_",
            parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_classes")
        )

    elif data == "adm_list_classes":
        classes = db.get_classes(school_id)
        if not classes:
            await query.edit_message_text(
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
        await query.edit_message_text(
            "🏫 *Sinflar ro'yxati:*\n_(sinfga bosib batafsil ko'ring)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_class_card_"):
        class_id = int(data.split("_")[-1])
        await _class_card(query, context, class_id, school_id)

    elif data.startswith("adm_rename_class_"):
        cid = int(data.split("_")[-1])
        cls = db.get_class(cid)
        context.user_data['tmp_class_id'] = cid
        context.user_data['waiting_for']  = 'adm_rename_class'
        await query.edit_message_text(
            f"✏️ *'{cls['name']}'* — yangi nom kiriting:",
            parse_mode="Markdown",
            reply_markup=kb_cancel(f"adm_class_card_{cid}")
        )

    elif data.startswith("adm_del_class_ok_"):
        cid = int(data.split("_")[-1])
        cls = db.get_class(cid)
        db.delete_class(cid)
        await query.edit_message_text(
            f"✅ *'{cls['name']}'* o'chirildi.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sinflar", callback_data="adm_list_classes")
            ]])
        )

    elif data.startswith("adm_del_class_"):
        cid = int(data.split("_")[-1])
        cls = db.get_class(cid)
        await query.edit_message_text(
            f"⚠️ *'{cls['name']}'* sinfini o'chirasizmi?\n_(Barcha o'quvchi, fan va darslar o'chadi!)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"adm_del_class_ok_{cid}")],
                [InlineKeyboardButton("❌ Bekor",         callback_data=f"adm_class_card_{cid}")],
            ])
        )

    # ══════════════════════════════════════════════
    #  SINF → FAN BIRIKTIRISH
    # ══════════════════════════════════════════════

    elif data.startswith("adm_class_subj_"):
        class_id = int(data.split("_")[-1])
        cls      = db.get_class(class_id)
        all_subj = db.get_subjects(school_id=school_id)
        if not all_subj:
            await query.edit_message_text(
                f"❌ Avval *📚 Fanlar* menyusidan fan yarating.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{class_id}")
                ]])
            )
            return
        assigned = {s['id'] for s in db.get_subjects(class_id=class_id)}
        buttons  = [
            [InlineKeyboardButton(
                f"{'✅' if s['id'] in assigned else '⬜'} {s['name']}",
                callback_data=f"adm_toggle_class_subj_{class_id}_{s['id']}"
            )]
            for s in all_subj
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{class_id}")])
        await query.edit_message_text(
            f"📚 *{cls['name']}* — Fanlarni belgilang:\n_(✅ biriktirilgan | ⬜ biriktirish)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_toggle_class_subj_"):
        parts    = data.replace("adm_toggle_class_subj_", "").split("_")
        class_id = int(parts[0])
        subj_id  = int(parts[1])
        if db.is_subject_assigned(subj_id, class_id):
            db.unassign_subject_from_class(subj_id, class_id)
        else:
            db.assign_subject_to_class(subj_id, class_id, school_id)
        # Sahifani yangilash
        cls      = db.get_class(class_id)
        all_subj = db.get_subjects(school_id=school_id)
        assigned = {s['id'] for s in db.get_subjects(class_id=class_id)}
        buttons  = [
            [InlineKeyboardButton(
                f"{'✅' if s['id'] in assigned else '⬜'} {s['name']}",
                callback_data=f"adm_toggle_class_subj_{class_id}_{s['id']}"
            )]
            for s in all_subj
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{class_id}")])
        await query.edit_message_text(
            f"📚 *{cls['name']}* — Fanlarni belgilang:\n_(✅ biriktirilgan | ⬜ biriktirish)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ══════════════════════════════════════════════
    #  SINF → O'QITUVCHI BIRIKTIRISH
    # ══════════════════════════════════════════════

    elif data.startswith("adm_class_tch_"):
        class_id = int(data.split("_")[-1])
        cls      = db.get_class(class_id)
        subjects = db.get_subjects(class_id=class_id)
        if not subjects:
            await query.edit_message_text(
                f"❌ *{cls['name']}* sinfiga avval fan biriktiring.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Fan biriktirish", callback_data=f"adm_class_subj_{class_id}")],
                    [InlineKeyboardButton("🔙 Orqaga",          callback_data=f"adm_class_card_{class_id}")],
                ])
            )
            return
        # Fanlarni ko'rsat — har bir fan uchun o'qituvchi tanlash
        buttons = []
        for s in subjects:
            teachers = db.get_teachers_by_subject_class(s['id'], class_id)
            tch_names = ", ".join(t['full_name'] for t in teachers) if teachers else "_(yo'q)_"
            buttons.append([InlineKeyboardButton(
                f"📚 {s['name']} — 👨‍🏫 {tch_names}",
                callback_data=f"adm_subj_tch_{class_id}_{s['id']}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{class_id}")])
        await query.edit_message_text(
            f"👨‍🏫 *{cls['name']}* — Fan tanlang (o'qituvchi biriktirish):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_subj_tch_"):
        parts    = data.replace("adm_subj_tch_", "").split("_")
        class_id = int(parts[0])
        subj_id  = int(parts[1])
        cls      = db.get_class(class_id)
        subj     = db.get_subject(subj_id)
        teachers = db.get_teachers_by_school(school_id)
        if not teachers:
            await query.edit_message_text(
                "❌ Avval *👨‍🏫 O'qituvchilar* menyusidan o'qituvchi qo'shing.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_tch_{class_id}")
                ]])
            )
            return
        assigned = {t['id'] for t in db.get_teachers_by_subject_class(subj_id, class_id)}
        buttons  = [
            [InlineKeyboardButton(
                f"{'✅' if t['id'] in assigned else '⬜'} {t['full_name']}",
                callback_data=f"adm_toggle_tch_{class_id}_{subj_id}_{t['id']}"
            )]
            for t in teachers
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_tch_{class_id}")])
        await query.edit_message_text(
            f"👨‍🏫 *{cls['name']}* | 📚 *{subj['name']}*\nO'qituvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_toggle_tch_"):
        parts      = data.replace("adm_toggle_tch_", "").split("_")
        class_id   = int(parts[0])
        subj_id    = int(parts[1])
        teacher_id = int(parts[2])
        assigned   = {t['id'] for t in db.get_teachers_by_subject_class(subj_id, class_id)}
        if teacher_id in assigned:
            db.remove_teacher_from_subject_class(teacher_id, class_id, subj_id)
        else:
            db.assign_teacher(teacher_id, class_id, subj_id)
        # Yangilash
        cls      = db.get_class(class_id)
        subj     = db.get_subject(subj_id)
        teachers = db.get_teachers_by_school(school_id)
        assigned2 = {t['id'] for t in db.get_teachers_by_subject_class(subj_id, class_id)}
        buttons  = [
            [InlineKeyboardButton(
                f"{'✅' if t['id'] in assigned2 else '⬜'} {t['full_name']}",
                callback_data=f"adm_toggle_tch_{class_id}_{subj_id}_{t['id']}"
            )]
            for t in teachers
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_tch_{class_id}")])
        await query.edit_message_text(
            f"👨‍🏫 *{cls['name']}* | 📚 *{subj['name']}*\nO'qituvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ══════════════════════════════════════════════
    #  O'QUVCHILAR
    # ══════════════════════════════════════════════

    elif data == "adm_add_student":
        context.user_data['waiting_for'] = 'adm_student_id'
        await query.edit_message_text(
            "👤 O'quvchining *Telegram ID* sini kiriting:",
            parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_classes")
        )

    elif data.startswith("adm_students_of_"):
        cid          = int(data.split("_")[-1])
        cls          = db.get_class(cid)
        students     = db.get_whitelist_by_class(cid)
        archived     = db.get_archived_students(school_id)
        archived_cls = [a for a in archived if a['class_id'] == cid]

        if not students:
            btns = [
                [InlineKeyboardButton("➕ O'quvchi qo'shish", callback_data="adm_add_student")],
            ]
            if archived_cls:
                btns.append([InlineKeyboardButton(f"📦 Arxiv ({len(archived_cls)} ta)", callback_data=f"adm_archived_students_{cid}")])
            btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{cid}")])
            await query.edit_message_text(
                f"❌ *{cls['name']}* sinfida faol o'quvchi yo'q.", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )
            return

        buttons = [
            [
                InlineKeyboardButton(f"👤 {s['full_name']}", callback_data="noop"),
                InlineKeyboardButton("🔄", callback_data=f"adm_move_student_{s['telegram_id']}"),
                InlineKeyboardButton("📦", callback_data=f"adm_del_student_{s['telegram_id']}"),
            ]
            for s in students
        ]
        buttons.append([InlineKeyboardButton("➕ O'quvchi qo'shish", callback_data="adm_add_student")])
        if archived_cls:
            buttons.append([InlineKeyboardButton(f"📦 Arxiv ({len(archived_cls)} ta)", callback_data=f"adm_archived_students_{cid}")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_class_card_{cid}")])
        await query.edit_message_text(
            f"👥 *{cls['name']} — O'quvchilar ({len(students)} ta):*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── Arxivlash (ma'lumotlar saqlanadi) ────────────────────────
    elif data.startswith("adm_archive_student_"):
        tid = int(data.split("_")[-1])
        st  = db.get_whitelist_user_any(tid)
        cid = st['class_id'] if st else None
        db.archive_student(tid)
        await query.edit_message_text(
            f"📦 *{st['full_name'] if st else tid}* arxivlandi.\n"
            f"_Barcha davomat, baho va topshirmalari saqlanib qoldi._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_students_of_{cid}")
            ]])
        )

    # ── Butunlay o'chirish (barchasi o'chadi) ─────────────────────
    elif data.startswith("adm_del_student_ok_"):
        tid  = int(data.split("_")[-1])
        st   = db.get_whitelist_user_any(tid)
        cid  = st['class_id'] if st else None
        db.delete_student(tid)
        await query.edit_message_text(
            f"🗑 *{st['full_name'] if st else tid}* butunlay o'chirildi.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_students_of_{cid}")
            ]])
        )

    # ── O'chirish/arxivlash tanlov ekrani ─────────────────────────
    elif data.startswith("adm_del_student_"):
        tid = int(data.split("_")[-1])
        st  = db.get_whitelist_user_any(tid)
        if not st:
            await query.edit_message_text("❌ O'quvchi topilmadi.")
            return
        await query.edit_message_text(
            f"⚠️ *{st['full_name']}* — nima qilmoqchisiz?\n\n"
            f"📦 *Arxivlash* — ma'lumotlar saqlanadi, o'quvchi botga kira olmaydi\n"
            f"🗑 *Butunlay o'chirish* — barcha ma'lumotlar o'chadi",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Arxivlash",          callback_data=f"adm_archive_student_{tid}")],
                [InlineKeyboardButton("🗑 Butunlay o'chirish",  callback_data=f"adm_del_student_ok_{tid}")],
                [InlineKeyboardButton("❌ Bekor",               callback_data=f"adm_students_of_{st['class_id']}")],
            ])
        )

    # ── Arxivlangan o'quvchilar ro'yxati ──────────────────────────
    elif data.startswith("adm_archived_students_"):
        cid      = int(data.split("_")[-1])
        cls      = db.get_class(cid)
        archived = db.get_archived_students(school_id)
        archived_cls = [a for a in archived if a['class_id'] == cid]
        if not archived_cls:
            await query.edit_message_text(
                f"📦 *{cls['name']}* — Arxiv bo'sh.", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_students_of_{cid}")
                ]])
            )
            return
        buttons = [
            [
                InlineKeyboardButton(f"📦 {s['full_name']}", callback_data="noop"),
                InlineKeyboardButton("♻️ Tiklash", callback_data=f"adm_restore_student_{s['telegram_id']}"),
                InlineKeyboardButton("🗑", callback_data=f"adm_del_student_ok_{s['telegram_id']}"),
            ]
            for s in archived_cls
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_students_of_{cid}")])
        await query.edit_message_text(
            f"📦 *{cls['name']} — Arxiv ({len(archived_cls)} ta):*\n"
            f"_♻️ Tiklash — faollashtiradi | 🗑 — butunlay o'chiradi_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── O'quvchini tikish ─────────────────────────────────────────
    elif data.startswith("adm_restore_student_"):
        tid = int(data.split("_")[-1])
        st  = db.get_whitelist_user_any(tid)
        db.restore_student(tid)
        cid = st['class_id'] if st else None
        await query.edit_message_text(
            f"♻️ *{st['full_name'] if st else tid}* qayta faollashtirildi!\n"
            f"_Barcha ma'lumotlari avtomatik tiklanadi._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 O'quvchilar", callback_data=f"adm_students_of_{cid}")
            ]])
        )

    elif data.startswith("adm_upd_student_id_"):
        old_id = int(data.split("_")[-1])
        st = db.get_whitelist_user(old_id)
        if not st:
            await query.edit_message_text("❌ O'quvchi topilmadi.")
            return
        context.user_data['adm_upd_old_student_id'] = old_id
        context.user_data['waiting_for'] = 'adm_upd_student_id'
        await query.edit_message_text(
            f"🆔 *{st['full_name']}* — yangi Telegram ID kiriting:\n\n"
            f"_Joriy ID: `{old_id}`_\n\n"
            f"⚠️ O'quvchining barcha davomati, baholari va topshirmalari saqlanib qoladi.",
            parse_mode="Markdown",
            reply_markup=kb_cancel(f"adm_students_of_{st['class_id']}")
        )

    elif data.startswith("adm_upd_teacher_id_"):
        old_tid = int(data.split("_")[-1])
        t = db.get_teacher(old_tid)
        if not t:
            await query.edit_message_text("❌ O'qituvchi topilmadi.")
            return
        context.user_data['adm_upd_old_teacher_tid'] = old_tid
        context.user_data['waiting_for'] = 'adm_upd_teacher_id'
        await query.edit_message_text(
            f"🆔 *{t['full_name']}* — yangi Telegram ID kiriting:\n\n"
            f"_Joriy ID: `{old_tid}`_\n\n"
            f"⚠️ O'qituvchining barcha ma'lumotlari saqlanib qoladi.",
            parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_teachers")
        )

    elif data.startswith("adm_move_student_"):
        tid = int(data.split("_")[-1])
        context.user_data['tmp_student_id'] = tid
        classes = db.get_classes(school_id)
        await query.edit_message_text(
            "🏫 *Yangi sinfni tanlang:*", parse_mode="Markdown",
            reply_markup=kb_classes(classes, prefix="adm_move_to")
        )

    elif data.startswith("adm_move_to_"):
        cid = int(data.split("_")[-1])
        tid = context.user_data.pop('tmp_student_id', None)
        if tid:
            with db.conn() as c:
                c.execute("UPDATE whitelist SET class_id=? WHERE telegram_id=?", (cid, tid))
            st  = db.get_whitelist_user(tid)
            cls = db.get_class(cid)
            await query.edit_message_text(
                f"✅ *{st['full_name']}* → *{cls['name']}* sinfiga ko'chirildi.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Sinf", callback_data=f"adm_students_of_{cid}")
                ]])
            )

    elif data.startswith("adm_student_class_"):
        cid  = int(data.split("_")[-1])
        tid  = context.user_data.pop('tmp_student_id', None)
        name = context.user_data.pop('tmp_student_name', None)
        context.user_data.pop('waiting_for', None)
        if tid and name:
            db.add_student(tid, name, cid, school_id)
            cls = db.get_class(cid)
            await query.edit_message_text(
                f"✅ *{name}* — *{cls['name']}* sinfiga qo'shildi!\n🆔 `{tid}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Yana qo'shish", callback_data="adm_add_student")],
                    [InlineKeyboardButton("🔙 Sinf",          callback_data=f"adm_class_card_{cid}")],
                ])
            )
            try:
                await query.message.bot.send_message(
                    tid,
                    f"✅ *Siz ro'yxatga qo'shildingiz!*\n\n"
                    f"👤 *{name}*\n🏫 Sinf: *{cls['name']}*\n\n"
                    f"/start bosing!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # ══════════════════════════════════════════════
    #  FANLAR (global yaratish)
    # ══════════════════════════════════════════════

    elif data == "adm_add_subject":
        # Fan maktab darajasida yaratiladi — sinf kerak emas
        context.user_data['waiting_for'] = 'adm_new_subject'
        await query.edit_message_text(
            "📚 *Yangi fan nomi:*\n_(Masalan: Matematika, Ona tili)_",
            parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_subjects")
        )

    elif data == "adm_list_subjects":
        subjects = db.get_subjects(school_id=school_id)
        if not subjects:
            await query.edit_message_text(
                "❌ Hali fan yaratilmagan.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Fan yaratish", callback_data="adm_add_subject")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")]
                ])
            )
            return
        buttons = []
        for s in subjects:
            assigned_classes = db.get_subject_classes(s['id'])
            cnt   = len(assigned_classes)
            label = f"📚 {s['name']}  ({cnt} sinf)" if cnt else f"📚 {s['name']}"
            buttons.append([
                InlineKeyboardButton(label, callback_data=f"adm_subject_info_{s['id']}"),
                InlineKeyboardButton("✏️",  callback_data=f"adm_rename_subj_{s['id']}"),
                InlineKeyboardButton("🗑️",  callback_data=f"adm_del_subj_{s['id']}"),
            ])
        buttons.append([InlineKeyboardButton("➕ Fan yaratish", callback_data="adm_add_subject")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
        await query.edit_message_text(
            "📚 *Fanlar ro'yxati:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_subject_info_"):
        subj_id = int(data.split("_")[-1])
        subj    = db.get_subject(subj_id)
        classes = db.get_subject_classes(subj_id)
        cls_list = "\n".join(f"  🏫 {c['name']}" for c in classes) if classes else "  _(biriktirilmagan)_"
        await query.edit_message_text(
            f"📚 *{subj['name']}*\n\nBiriktirilgan sinflar:\n{cls_list}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Nomini o'zgartirish", callback_data=f"adm_rename_subj_{subj_id}")],
                [InlineKeyboardButton("🗑️ O'chirish",           callback_data=f"adm_del_subj_{subj_id}")],
                [InlineKeyboardButton("🔙 Ro'yxat",             callback_data="adm_list_subjects")],
            ])
        )

    elif data.startswith("adm_rename_subj_"):
        sid = int(data.split("_")[-1])
        s   = db.get_subject(sid)
        context.user_data['tmp_subject_id'] = sid
        context.user_data['waiting_for']    = 'adm_rename_subject'
        await query.edit_message_text(
            f"✏️ *'{s['name']}'* — yangi nom kiriting:", parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_subjects")
        )

    elif data.startswith("adm_del_subj_ok_"):
        sid = int(data.split("_")[-1])
        s   = db.get_subject(sid)
        db.delete_subject(sid)
        await query.edit_message_text(
            f"✅ *'{s['name']}'* o'chirildi.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Fanlar", callback_data="adm_list_subjects")
            ]])
        )

    elif data.startswith("adm_del_subj_"):
        sid = int(data.split("_")[-1])
        s   = db.get_subject(sid)
        await query.edit_message_text(
            f"⚠️ *'{s['name']}'* fanini o'chirasizmi?\n_(Barcha sinflardan ham o'chadi)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha",   callback_data=f"adm_del_subj_ok_{sid}")],
                [InlineKeyboardButton("❌ Bekor", callback_data="adm_list_subjects")],
            ])
        )

    # ══════════════════════════════════════════════
    #  O'QITUVCHILAR (global yaratish)
    # ══════════════════════════════════════════════

    elif data == "adm_confirm_add_teacher":
        # Boshqa maktabda mavjud o'qituvchini tasdiqlash
        tid = context.user_data.get('tmp_teacher_id')
        name = context.user_data.get('tmp_teacher_name')
        
        if not tid or not name:
            await query.edit_message_text("❌ Ma'lumot topilmadi.")
            return
        
        # Shu maktabda mavjudligini yana tekshirish
        existing = db.get_teacher_with_school(tid, school_id)
        if existing:
            await query.edit_message_text(
                f"⚠️ *{existing['full_name']}* allaqachon sizning maktabingizda mavjud.",
                parse_mode="Markdown"
            )
            context.user_data.pop('waiting_for', None)
            context.user_data.pop('tmp_teacher_id', None)
            context.user_data.pop('tmp_teacher_name', None)
            return
        
        # Qo'shish
        db.add_teacher(tid, school_id, name)
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('tmp_teacher_id', None)
        context.user_data.pop('tmp_teacher_name', None)
        
        await query.edit_message_text(
            f"✅ *{name}* maktabingizga qo'shildi!\n\n"
            f"Endi uni sinf va fanga biriktirishingiz mumkin.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 O'qituvchilar ro'yxati", callback_data="adm_list_teachers")
            ]])
        )

    elif data == "adm_add_teacher":
        context.user_data['waiting_for'] = 'adm_teacher_id'
        await query.edit_message_text(
            "👨‍🏫 O'qituvchining *Telegram ID* sini kiriting:", parse_mode="Markdown",
            reply_markup=kb_cancel("adm_list_teachers")
        )

    elif data == "adm_list_teachers":
        teachers = db.get_teachers_by_school(school_id)
        if not teachers:
            await query.edit_message_text(
                "❌ Hali o'qituvchi qo'shilmagan.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ O'qituvchi qo'shish", callback_data="adm_add_teacher")],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_teachers_menu")]
                ])
            )
            return
        buttons = []
        for t in teachers:
            assignments = db.get_teacher_assignments(t['id'])
            cnt = len(assignments)
            buttons.append([
                InlineKeyboardButton(f"👨‍🏫 {t['full_name']}  ({cnt} ta biriktirma)", callback_data=f"adm_teacher_info_{t['id']}"),
                InlineKeyboardButton("📦", callback_data=f"adm_del_teacher_{t['telegram_id']}"),
            ])
        archived_t = db.get_archived_teachers(school_id)
        buttons.append([InlineKeyboardButton("➕ O'qituvchi qo'shish", callback_data="adm_add_teacher")])
        if archived_t:
            buttons.append([InlineKeyboardButton(f"📦 Arxiv ({len(archived_t)} ta)", callback_data="adm_archived_teachers")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_teachers_menu")])
        await query.edit_message_text(
            "👨‍🏫 *O'qituvchilar:*\n_(sinf biriktirish — Sinflar → Sinf kartasi orqali)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_teacher_info_"):
        tid  = int(data.split("_")[-1])
        t    = db.get_teacher_by_id(tid)
        if not t:
            await query.edit_message_text("❌ Topilmadi.")
            return
        assignments = db.get_teacher_assignments(tid)
        lines = [f"👨‍🏫 *{t['full_name']}*", f"🆔 `{t['telegram_id']}`", ""]
        if assignments:
            by_class = {}
            for a in assignments:
                by_class.setdefault(a['class_name'], []).append(a['subject_name'])
            for cn, subjs in sorted(by_class.items()):
                lines.append(f"🏫 *{cn}*: " + ", ".join(subjs))
        else:
            lines.append("_Hali birorta sinfga biriktirilmagan_")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆔 ID yangilash", callback_data=f"adm_upd_teacher_id_{t['telegram_id']}")],
                [InlineKeyboardButton("📦 Arxivlash / O'chirish", callback_data=f"adm_del_teacher_{t['telegram_id']}")],
                [InlineKeyboardButton("🔙 Orqaga",       callback_data="adm_list_teachers")],
            ])
        )

    # ── O'qituvchini arxivlash ────────────────────────────────────
    elif data.startswith("adm_archive_teacher_"):
        tid = int(data.split("_")[-1])
        t   = db.get_teacher(tid) or db.get_teacher_by_id_any(int(tid))
        # telegram_id yoki teacher.id bo'lishi mumkin — ikkalasini sinab ko'ramiz
        teacher_obj = None
        # tid = telegram_id kelishi mumkin
        import sqlite3 as _sqlite3
        with db.conn() as _c:
            row = _c.execute("SELECT * FROM teachers WHERE telegram_id=? AND school_id=?",
                             (int(tid), school_id)).fetchone()
            if row:
                teacher_obj = row
        if not teacher_obj:
            await query.edit_message_text("❌ O'qituvchi topilmadi.")
            return
        db.archive_teacher(teacher_obj['id'])
        await query.edit_message_text(
            f"📦 *{teacher_obj['full_name']}* arxivlandi.\n"
            f"_Barcha darslar, baholar va davomat ma'lumotlari saqlanib qoldi._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ro'yxat", callback_data="adm_list_teachers")
            ]])
        )

    # ── Butunlay o'chirish ────────────────────────────────────────
    elif data.startswith("adm_del_teacher_ok_"):
        tid  = int(data.split("_")[-1])
        with db.conn() as _c:
            t = _c.execute("SELECT * FROM teachers WHERE telegram_id=? AND school_id=?",
                           (tid, school_id)).fetchone()
        name = t['full_name'] if t else "O'qituvchi"
        teacher_id = t['id'] if t else None
        if teacher_id:
            db.delete_teacher(teacher_id)
        await query.edit_message_text(
            f"🗑 *{name}* butunlay o'chirildi.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ro'yxat", callback_data="adm_list_teachers")
            ]])
        )

    # ── O'chirish/arxivlash tanlov ekrani ─────────────────────────
    elif data.startswith("adm_del_teacher_"):
        tid = int(data.split("_")[-1])
        t   = db.get_teacher(tid)
        if not t:
            await query.edit_message_text("❌ Topilmadi.")
            return
        await query.edit_message_text(
            f"⚠️ *{t['full_name']}* — nima qilmoqchisiz?\n\n"
            f"📦 *Arxivlash* — ma'lumotlar saqlanadi, o'qituvchi botga kira olmaydi\n"
            f"🗑 *Butunlay o'chirish* — barcha darslar, baholar, davomat o'chadi",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Arxivlash",          callback_data=f"adm_archive_teacher_{tid}")],
                [InlineKeyboardButton("🗑 Butunlay o'chirish",  callback_data=f"adm_del_teacher_ok_{tid}")],
                [InlineKeyboardButton("❌ Bekor",               callback_data="adm_list_teachers")],
            ])
        )

    # ── Arxivlangan o'qituvchilar ro'yxati ────────────────────────
    elif data == "adm_archived_teachers":
        archived = db.get_archived_teachers(school_id)
        if not archived:
            await query.edit_message_text(
                "📦 *O'qituvchilar arxivi bo'sh.*", parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="adm_list_teachers")
                ]])
            )
            return
        buttons = []
        for t in archived:
            buttons.append([
                InlineKeyboardButton(f"📦 {t['full_name']}", callback_data="noop"),
                InlineKeyboardButton("♻️ Tiklash", callback_data=f"adm_restore_teacher_{t['id']}"),
                InlineKeyboardButton("🗑", callback_data=f"adm_del_teacher_ok_{t['telegram_id']}"),
            ])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_list_teachers")])
        await query.edit_message_text(
            f"📦 *O'qituvchilar arxivi ({len(archived)} ta):*\n"
            f"_♻️ Tiklash — faollashtiradi | 🗑 — butunlay o'chiradi_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── O'qituvchini tiklash ──────────────────────────────────────
    elif data.startswith("adm_restore_teacher_"):
        teacher_id = int(data.split("_")[-1])
        with db.conn() as _c:
            t = _c.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        db.restore_teacher(teacher_id)
        name = t['full_name'] if t else str(teacher_id)
        await query.edit_message_text(
            f"♻️ *{name}* qayta faollashtirildi!\n"
            f"_Barcha darslar, baholar va davomat ma'lumotlari tiklanadi._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 O'qituvchilar", callback_data="adm_list_teachers")
            ]])
        )

    # ── O'QITUVCHINI BIRIKTIRISH ─────────────────────────────────

    elif data == "adm_assign_teacher":
        teachers = db.get_teachers_by_school(school_id)
        if not teachers:
            await query.edit_message_text(
                "❌ Avval o'qituvchi qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ O'qituvchi qo'shish", callback_data="adm_add_teacher")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(f"👨‍🏫 {t['full_name']}", callback_data=f"adm_assign_t_{t['id']}")]
            for t in teachers
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_teachers_menu")])
        await query.edit_message_text(
            "🔗 *O'qituvchini biriktirish*\n\nO'qituvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_assign_t_"):
        teacher_id = int(data.split("_")[-1])
        context.user_data['tmp_teacher_id'] = teacher_id
        teacher = db.get_teacher_by_id(teacher_id)
        classes = db.get_classes(school_id)
        if not classes:
            await query.edit_message_text(
                "❌ Avval sinf qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="adm_assign_teacher")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"adm_assign_c_{c['id']}")]
            for c in classes
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_assign_teacher")])
        await query.edit_message_text(
            f"🔗 *O'qituvchi:* {teacher['full_name']}\n\nSinf tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_assign_c_"):
        class_id = int(data.split("_")[-1])
        context.user_data['tmp_class_id'] = class_id
        teacher_id = context.user_data.get('tmp_teacher_id')
        teacher = db.get_teacher_by_id(teacher_id)
        cls = db.get_class(class_id)
        subjects = db.get_subjects(class_id=class_id)
        if not subjects:
            await query.edit_message_text(
                f"❌ *{cls['name']}* sinfiga avval fan biriktiring.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_assign_t_{teacher_id}")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(f"📚 {s['name']}", callback_data=f"adm_assign_s_{s['id']}")]
            for s in subjects
        ]
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_assign_t_{teacher_id}")])
        await query.edit_message_text(
            f"🔗 *O'qituvchi:* {teacher['full_name']}\n🏫 *Sinf:* {cls['name']}\n\nFan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_assign_s_"):
        subject_id = int(data.split("_")[-1])
        teacher_id = context.user_data.get('tmp_teacher_id')
        class_id = context.user_data.get('tmp_class_id')
        
        teacher = db.get_teacher_by_id(teacher_id)
        cls = db.get_class(class_id)
        subject = db.get_subject(subject_id)
        
        # Biriktirishdan oldin tekshirish
        existing = db.get_teacher_assignments(teacher_id)
        is_duplicate = any(
            a['class_id'] == class_id and a['subject_id'] == subject_id
            for a in existing
        )
        
        if is_duplicate:
            await query.edit_message_text(
                f"⚠️ *{teacher['full_name']}* allaqachon *{cls['name']}* da *{subject['name']}* fanini o'qitadi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"adm_assign_c_{class_id}")
                ]])
            )
            return
        
        # Biriktirish
        success = db.assign_teacher(teacher_id, class_id, subject_id)
        
        if success:
            await query.edit_message_text(
                f"✅ *Biriktirildi!*\n\n"
                f"👨‍🏫 O'qituvchi: *{teacher['full_name']}*\n"
                f"🏫 Sinf: *{cls['name']}*\n"
                f"📚 Fan: *{subject['name']}*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Yana biriktirish", callback_data="adm_assign_teacher")],
                    [InlineKeyboardButton("📋 O'qituvchilar ro'yxati", callback_data="adm_list_teachers")],
                ])
            )
        else:
            await query.edit_message_text(
                "❌ Xatolik yuz berdi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="adm_assign_teacher")
                ]])
            )
        
        # Tozalash
        context.user_data.pop('tmp_teacher_id', None)
        context.user_data.pop('tmp_class_id', None)

    elif data == "adm_teachers_menu":
        await query.edit_message_text(
            f"👨‍🏫 *O'qituvchilar:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ O'qituvchi qo'shish",   callback_data="adm_add_teacher")],
                [InlineKeyboardButton("📋 O'qituvchilar ro'yxati", callback_data="adm_list_teachers")],
                [InlineKeyboardButton("🔗 O'qituvchini biriktirish", callback_data="adm_assign_teacher")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")],
            ])
        )

    # ══════════════════════════════════════════════
    #  DARS JADVALI
    # ══════════════════════════════════════════════

    elif data == "adm_schedule_list":
        classes = db.get_classes(school_id)
        if not classes:
            await query.edit_message_text(
                "❌ Avval sinf qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
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
        await query.edit_message_text(
            "🗓 *Dars jadvallari:* _(✅ yuklangan | ❌ yuklanmagan)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_schedule_"):
        cid      = int(data.split("_")[-1])
        cls      = db.get_class(cid)
        schedule = db.get_schedule(school_id=school_id, class_id=cid)
        buttons  = [[InlineKeyboardButton("📤 Jadval yuklash", callback_data=f"adm_sched_upload_{cid}")]]
        if schedule:
            buttons.append([InlineKeyboardButton("🗑️ O'chirish", callback_data=f"adm_sched_del_{cid}")])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_schedule_list")])
        await query.edit_message_text(
            f"🗓 *{cls['name']} — Dars jadvali*\n\n"
            f"{'✅ Jadval yuklangan.' if schedule else '❌ Jadval yuklanmagan.'}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("adm_sched_upload_"):
        cid = int(data.split("_")[-1])
        cls = db.get_class(cid)
        context.user_data['waiting_for']  = 'adm_schedule_file'
        context.user_data['tmp_class_id'] = cid
        await query.edit_message_text(
            f"🗓 *{cls['name']}* — dars jadvalini yuboring:\n_(Rasm yoki PDF fayl)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"adm_schedule_{cid}")
            ]])
        )

    elif data.startswith("adm_sched_del_"):
        cid = int(data.split("_")[-1])
        cls = db.get_class(cid)
        with db.conn() as c:
            c.execute("DELETE FROM schedules WHERE class_id=?", (cid,))
        await query.edit_message_text(
            f"✅ *{cls['name']}* jadvali o'chirildi.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="adm_schedule_list")
            ]])
        )

    # ══════════════════════════════════════════════
    #  O'QUVCHILAR DAVOMATI  (adm_att_*)
    # ══════════════════════════════════════════════

    elif data.startswith("adm_att_class_"):
        class_id = int(data.split("_")[-1])
        context.user_data['att_class_id']    = class_id
        context.user_data['att_subject_id']  = 0
        from utils.keyboards import kb_att_dates_for_class
        cls = db.get_class(class_id)
        await query.edit_message_text(
            f"📋 Davomat | 🏫 *{cls['name']}*\n\n📅 Kun tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_att_dates_for_class(class_id)
        )

    elif data.startswith("adm_att_date_"):
        # format: adm_att_date_{class_id}_{YYYY-MM-DD}
        rest     = data[len("adm_att_date_"):]
        # oxirgi 10 belgi — sana
        date_str = rest[-10:]
        class_id = int(rest[:-11])
        context.user_data['att_class_id']   = class_id
        context.user_data['att_subject_id'] = 0
        from handlers.teacher.attendance import start_attendance
        await start_attendance(query, context, date_str)

    elif data.startswith("adm_att_custom_"):
        # "Boshqa sana" tugmasi bosildi — foydalanuvchi sana kiritadi
        class_id = int(data.split("_")[-1])
        context.user_data['att_class_id']   = class_id
        context.user_data['att_subject_id'] = 0
        context.user_data['waiting_for']    = 'adm_att_custom_date'
        cls = db.get_class(class_id)
        await query.edit_message_text(
            f"📋 Davomat | 🏫 *{cls['name']}*\n\n"
            f"📅 Sana kiriting (*KK.OO.YYYY*):\nMasalan: *03.03.2026*",
            parse_mode="Markdown",
            reply_markup=kb_cancel(f"adm_att_class_{class_id}")
        )

    # ══════════════════════════════════════════════
    #  UMUMIY
    # ══════════════════════════════════════════════

    elif data == "adm_main_menu":
        # Asosiy menyuga qaytish - xabarni o'chirish
        await query.delete_message()

    elif data == "adm_done":
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('tmp_class_id', None)
        context.user_data.pop('tmp_subject_id', None)
        await query.edit_message_text("✅ Amal yakunlandi.")

    elif data == "noop":
        pass