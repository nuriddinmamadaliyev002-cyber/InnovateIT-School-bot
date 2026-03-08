"""
panels/super/callbacks.py — Super Admin inline callback handlerlari (sup_*)

Yangiliklar:
  sup_tch_list_{sid}  — maktab o'qituvchilari ro'yxati
  sup_tch_{tid}       — o'qituvchi profili (sinf/fan, davomat, jadval)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone

from config import db, TASHKENT_TZ, WEEKDAY_LABELS, ATTENDANCE_EMOJI, ATTENDANCE_LABEL
from utils.keyboards import kb_super_admin, kb_school_admin, kb_cancel


async def handle_super_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):

    # ── MAKTABLAR ─────────────────────────────────────────────────

    if data == "sup_add_school":
        context.user_data['waiting_for'] = 'sup_new_school'
        await query.edit_message_text(
            "🏫 *Yangi maktab nomini kiriting:*",
            parse_mode="Markdown",
            reply_markup=kb_cancel()
        )

    elif data == "sup_schools_list":
        schools = db.get_schools()
        if not schools:
            await query.edit_message_text(
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
                f"🏫 {s['name']}  ({st['students']} o'quvchilar | {st['teachers']} o'qituvchilar)", callback_data=f"sup_school_{s['id']}"
            )])
        buttons.append([InlineKeyboardButton("➕ Maktab qo'shish", callback_data="sup_add_school")])
        await query.edit_message_text(
            "🏫 *Maktablar:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("sup_school_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        if not school:
            await query.edit_message_text("❌ Maktab topilmadi.")
            return
        st     = db.get_school_stats(sid)
        admins = db.get_school_admins(school_id=sid)
        adm_names = ", ".join(a['full_name'] for a in admins) or "Tayinlanmagan"
        await query.edit_message_text(
            f"🏫 *{school['name']}*\n\n"
            f"👥 O'quvchilar: *{st['students']}* ta\n"
            f"👨‍🏫 O'qituvchilar: *{st['teachers']}* ta\n"
            f"🏫 Sinflar: *{st['classes']}* ta\n"
            f"📚 Fanlar: *{st['subjects']}* ta\n\n"
            f"👨‍💼 Admin: *{adm_names}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 Maktabni boshqarish",  callback_data=f"sup_manage_{sid}")],
                [InlineKeyboardButton("👨‍🏫 O'qituvchilar",       callback_data=f"sup_tch_list_{sid}")],
                [InlineKeyboardButton("👨‍💼 Admin tayinlash",     callback_data=f"sup_assign_admin_{sid}")],
                [
                    InlineKeyboardButton("✏️ Nomini o'zgartirish", callback_data=f"sup_rename_school_{sid}"),
                    InlineKeyboardButton("🗑️ O'chirish",           callback_data=f"sup_del_school_{sid}"),
                ],
                [InlineKeyboardButton("🔙 Maktablar", callback_data="sup_schools_list")],
            ])
        )

    elif data.startswith("sup_manage_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        context.user_data['school_id'] = sid
        await query.message.reply_text(
            f"🔧 *{school['name']}* maktabini boshqarayapsiz\n"
            f"_(Super Admin — to'liq huquq)_\n\n"
            f"Qaytish uchun *'🔙 Super Admin paneli'* tugmasini bosing 👇",
            parse_mode="Markdown",
            reply_markup=kb_school_admin(is_super=True)
        )

    elif data.startswith("sup_rename_school_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        context.user_data['tmp_school_id'] = sid
        context.user_data['waiting_for']   = 'sup_rename_school'
        await query.edit_message_text(
            f"✏️ *'{school['name']}'* — yangi nom kiriting:",
            parse_mode="Markdown",
            reply_markup=kb_cancel(f"sup_school_{sid}")
        )

    elif data.startswith("sup_del_school_ok_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        name   = school['name'] if school else "Maktab"
        try:
            db.delete_school(sid)
            await query.edit_message_text(
                f"✅ *{name}* muvaffaqiyatli o'chirildi.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Maktablar", callback_data="sup_schools_list")
                ]])
            )
        except ValueError as e:
            # User'ga tushunarli xato xabari
            await query.answer(str(e), show_alert=True)
            # Orqaga qaytarish
            st = db.get_school_stats(sid)
            await query.edit_message_text(
                f"⚠️ *{name}* maktabini o'chirasizmi?\n\n"
                f"Birga o'chadi: {st['classes']} sinf, {st['students']} o'quvchi, "
                f"{st['teachers']} o'qituvchi\n\n⚠️ *Qaytarib bo'lmaydi!*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"sup_del_school_ok_{sid}")],
                    [InlineKeyboardButton("❌ Bekor",         callback_data=f"sup_school_{sid}")],
                ])
            )
        except Exception as e:
            await query.answer(f"❌ Xatolik: {str(e)}", show_alert=True)

    elif data.startswith("sup_del_school_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        st     = db.get_school_stats(sid)
        await query.edit_message_text(
            f"⚠️ *{school['name']}* maktabini o'chirasizmi?\n\n"
            f"Birga o'chadi: {st['classes']} sinf, {st['students']} o'quvchi, "
            f"{st['teachers']} o'qituvchi\n\n⚠️ *Qaytarib bo'lmaydi!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"sup_del_school_ok_{sid}")],
                [InlineKeyboardButton("❌ Bekor",         callback_data=f"sup_school_{sid}")],
            ])
        )

    # ── MAKTAB ADMINLARI ──────────────────────────────────────────

    elif data == "sup_add_admin":
        schools = db.get_schools()
        if not schools:
            await query.edit_message_text(
                "❌ Avval maktab qo'shing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Maktab qo'shish", callback_data="sup_add_school")
                ]])
            )
            return
        buttons = [
            [InlineKeyboardButton(f"🏫 {s['name']}", callback_data=f"sup_assign_admin_{s['id']}")]
            for s in schools
        ]
        await query.edit_message_text(
            "👨‍💼 *Admin tayinlash* — maktabni tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("sup_assign_admin_"):
        sid    = int(data.split("_")[-1])
        school = db.get_school(sid)
        context.user_data['tmp_school_id'] = sid
        context.user_data['waiting_for']   = 'sup_admin_id'
        await query.edit_message_text(
            f"👨‍💼 *{school['name']}* — admin Telegram ID sini kiriting:",
            parse_mode="Markdown",
            reply_markup=kb_cancel()
        )

    elif data.startswith("sup_del_admin_"):
        parts = data.replace("sup_del_admin_", "").split("_")
        tid   = int(parts[0])
        sid   = int(parts[1])
        db.delete_school_admin(tid)
        await query.answer("✅ Admin o'chirildi.")
        admins = db.get_school_admins()
        if not admins:
            await query.edit_message_text(
                "👨‍💼 Maktab adminlari yo'q.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Admin tayinlash", callback_data="sup_add_admin")
                ]])
            )
            return
        buttons = [
            [
                InlineKeyboardButton(f"👨‍💼 {a['full_name']}  ({a['school_name']})", callback_data="noop"),
                InlineKeyboardButton("🗑️", callback_data=f"sup_del_admin_{a['telegram_id']}_{a['school_id']}"),
            ]
            for a in admins
        ]
        buttons.append([InlineKeyboardButton("➕ Admin tayinlash", callback_data="sup_add_admin")])
        await query.edit_message_text(
            "👨‍💼 *Maktab adminlari:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── O'QITUVCHILAR RO'YXATI ────────────────────────────────────

    elif data.startswith("sup_tch_list_"):
        sid     = int(data.split("_")[-1])
        school  = db.get_school(sid)
        if not school:
            await query.edit_message_text("❌ Maktab topilmadi.")
            return
        teachers = db.get_teachers_by_school(sid)
        if not teachers:
            await query.edit_message_text(
                f"🏫 *{school['name']}*\n\n👨‍🏫 Hali o'qituvchi yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Maktabga", callback_data=f"sup_school_{sid}")
                ]])
            )
            return

        buttons = []
        for t in teachers:
            assignments = db.get_teacher_assignments(t['id'])
            classes = list({a['class_name'] for a in assignments})
            classes_str = ", ".join(sorted(classes)) if classes else "—"
            buttons.append([InlineKeyboardButton(
                f"👤 {t['full_name']}  |  {classes_str}",
                callback_data=f"sup_tch_{t['id']}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Maktabga", callback_data=f"sup_school_{sid}")])

        await query.edit_message_text(
            f"🏫 *{school['name']}* — O'qituvchilar ({len(teachers)} ta):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── O'QITUVCHI PROFILI ────────────────────────────────────────

    elif data.startswith("sup_tch_"):
        tid     = int(data.split("_")[-1])
        teacher = db.get_teacher_by_id(tid)
        if not teacher:
            await query.edit_message_text("❌ O'qituvchi topilmadi.")
            return

        sid    = teacher['school_id']
        school = db.get_school(sid)

        # ─ 1. Sinf / fan birikmalari ─
        assignments = db.get_teacher_assignments(tid)
        if assignments:
            assign_lines = []
            for a in assignments:
                assign_lines.append(f"   • {a['class_name']} — {a['subject_name']}")
            assign_text = "\n".join(assign_lines)
        else:
            assign_text = "   Biriktirilmagan"

        # ─ 2. Shu oy davomati ─
        now   = datetime.now(TASHKENT_TZ)
        month = now.strftime("%Y-%m")
        att_stats = db.get_teacher_att_stats(tid, month=month)
        total   = att_stats['total']
        present = att_stats['present']
        absent  = att_stats['absent']
        late    = att_stats['late']
        att_pct = round(present / total * 100) if total else 0

        if total:
            att_text = (
                f"✅ Keldi: *{present}* | ❌ Kelmadi: *{absent}* | ⏰ Kech: *{late}*\n"
                f"   Davomat: *{att_pct}%* ({now.strftime('%B %Y')})"
            )
        else:
            att_text = f"   {now.strftime('%B %Y')} da ma'lumot yo'q"

        # ─ 3. Haftalik jadval ─
        slots = db.get_slots(teacher_id=tid)
        if slots:
            schedule_by_day: dict = {}
            for s in slots:
                wd = s['weekday']
                if wd not in schedule_by_day:
                    schedule_by_day[wd] = []
                time_str = ""
                if s['start_time'] and s['end_time']:
                    time_str = f" ({s['start_time']}–{s['end_time']})"
                schedule_by_day[wd].append(
                    f"{s['class_name']} / {s['subject_name']}{time_str}"
                )
            sched_lines = []
            for wd in sorted(schedule_by_day):
                label = WEEKDAY_LABELS.get(wd, f"Kun {wd}")
                for entry in schedule_by_day[wd]:
                    sched_lines.append(f"   {label}: {entry}")
            sched_text = "\n".join(sched_lines)
        else:
            sched_text = "   Jadval kiritilmagan"

        # ─ Profil matni ─
        text = (
            f"👤 *{teacher['full_name']}*\n"
            f"🏫 Maktab: *{school['name'] if school else '—'}*\n"
            f"🆔 Telegram ID: `{teacher['telegram_id']}`\n"
            f"📅 Qo'shilgan: {str(teacher['created_at'])[:10]}\n"
            f"\n"
            f"📚 *Sinf / Fan birikmalari:*\n{assign_text}\n"
            f"\n"
            f"📋 *Davomat ({now.strftime('%B')}):*\n{att_text}\n"
            f"\n"
            f"🗓 *Haftalik jadval:*\n{sched_text}"
        )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 O'qituvchilar", callback_data=f"sup_tch_list_{sid}")]
            ])
        )

    elif data == "noop":
        await query.answer()