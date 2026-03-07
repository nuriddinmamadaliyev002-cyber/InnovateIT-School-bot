"""
handlers/student/callbacks.py — O'quvchi inline callback handlerlari

Yangiliklar (v2):
  stu_hw_dates          — homework bo'lgan sanalar ro'yxati
  stu_hw_date_{date}    — shu sanada fanlar + topshirish + baho
  stu_hw_subj_{sid}_{date} — fan tanlanganda detail ko'rish
  stu_submit_{sid}_{date}  — topshirish boshlash
  stu_resubmit_{sid}_{date} — qayta topshirish

Yangiliklar (v3) — Hamma mavzu va vazifalar yangi flow:
  hmv_hw                — Vazifalar bo'limi: topshirilgan / topshirilmagan
  hmv_topics            — Mavzular ro'yxati
  hmv_done              — Topshirilgan fanlar ro'yxati
  hmv_pend              — Topshirilmagan fanlar ro'yxati (deadline o'tmagan)
  hmv_done_s_{sid}      — Topshirilgan vazifalar (fan bo'yicha detail)
  hmv_pend_s_{sid}      — Topshirilmagan vazifalar (fan bo'yicha detail + yuklash tugmasi)
"""
from datetime import datetime, date
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import db, TASHKENT_TZ
from utils.media import send_media


def _deadline_text(deadline: str | None) -> str:
    """Deadline matni: '⏰ Deadline: 28.02 23:59 (2 soat qoldi)' yoki ''"""
    if not deadline:
        return ""
    try:
        dl = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        dl_fmt = dl.strftime("%d.%m %H:%M")
        diff = dl - now
        if diff.total_seconds() < 0:
            return f"⏰ Deadline: {dl_fmt} _(o'tib ketdi)_"
        hours = int(diff.total_seconds() // 3600)
        mins  = int((diff.total_seconds() % 3600) // 60)
        if hours >= 24:
            days = hours // 24
            return f"⏰ Deadline: {dl_fmt} _({days} kun qoldi)_"
        elif hours > 0:
            return f"⏰ Deadline: {dl_fmt} _({hours} soat {mins} daqiqa qoldi)_"
        else:
            return f"⏰ Deadline: {dl_fmt} _({mins} daqiqa qoldi!)_"
    except Exception:
        return f"⏰ Deadline: {deadline}"


def _is_deadline_passed(deadline: str | None) -> bool:
    """Deadline o'tib ketganini tekshirish"""
    if not deadline:
        return False
    try:
        dl  = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        return now > dl
    except Exception:
        return False


def _get_pending_homeworks(class_id: int, student_id: int) -> list:
    """
    O'quvchi hali topshirmagan va deadline o'tmagan vazifalar.
    Qaytaradi: hw dictlar ro'yxati (get_all_homeworks_for_class formatida)
    """
    homeworks = db.get_all_homeworks_for_class(class_id)
    result = []
    for hw in homeworks:
        if _is_deadline_passed(hw['deadline']):
            continue   # muddati o'tgan — ko'rinmaydi
        existing = db.get_student_submission(student_id, hw['subject_id'], hw['date'])
        if not existing:
            result.append(hw)
    return result


def _get_submitted_homeworks(class_id: int, student_id: int) -> list:
    """
    O'quvchi topshirgan vazifalar (submission bilan birgalikda).
    Qaytaradi: [(hw_dict, submission_row), ...]
    """
    homeworks = db.get_all_homeworks_for_class(class_id)
    result = []
    for hw in homeworks:
        existing = db.get_student_submission(student_id, hw['subject_id'], hw['date'])
        if existing:
            result.append((hw, existing))
    return result


# ══════════════════════════════════════════════════════════
#  HAMMA VAZIFALAR — sanalar ro'yxati
# ══════════════════════════════════════════════════════════

async def handle_lesson_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    user_id = query.from_user.id
    wl = db.get_whitelist_user(user_id)
    if not wl:
        await query.edit_message_text(
            "❌ Siz ro'yxatda yo'qsiz.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
            ]])
        )
        return
    class_id   = wl['class_id']
    student_id = wl['telegram_id']

    # ══════════════════════════════════════════════════════════
    # HMV — Hamma mavzu va vazifalar (yangi flow v3)
    # ══════════════════════════════════════════════════════════

    # ── hmv_hw — Vazifalar bo'limi ────────────────────────────
    if data == "hmv_hw":
        pending   = _get_pending_homeworks(class_id, student_id)
        submitted = _get_submitted_homeworks(class_id, student_id)
        pend_count = len(pending)
        await query.edit_message_text(
            "📝 *Vazifalar*\n\nQaysi bo'limni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"✅ Topshirilgan vazifalar ({len(submitted)} ta)",
                    callback_data="hmv_done"
                )],
                [InlineKeyboardButton(
                    f"⬜️ Topshirilmagan vazifalar ({pend_count} ta)",
                    callback_data="hmv_pend"
                )],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_back_main")],
            ])
        )
        return

    # ── hmv_back_main — Asosiy 2 tugmaga qaytish ─────────────
    if data == "hmv_back_main":
        await query.edit_message_text(
            "📋 *Hamma mavzu va vazifalar*\n\nQaysi bo'limni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Vazifalar",  callback_data="hmv_hw")],
                [InlineKeyboardButton("📖 Mavzular",   callback_data="hmv_topics")],
            ])
        )
        return

    # ── hmv_topics — Mavzular ro'yxati ───────────────────────
    if data == "hmv_topics":
        topics = db.get_topics_for_class(class_id)
        if not topics:
            await query.edit_message_text(
                "📖 *Mavzular ro'yxati*\n\n❌ Hozircha hech qanday mavzu yuklanmagan.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_back_main")
                ]])
            )
            return
        btns = []
        for t in topics[:30]:
            d_fmt   = date.fromisoformat(t['date']).strftime("%d.%m")
            preview = t['content'][:25] + "…" if t['content'] and len(t['content']) > 25 \
                      else (t['content'] or "📎 fayl")
            label   = f"📖 {t['subject_name']} | {d_fmt} — {preview}"
            btns.append([InlineKeyboardButton(label[:64], callback_data=f"stu_topic_view_{t['id']}")])
        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_back_main")])
        await query.edit_message_text(
            "📖 *Mavzular ro'yxati:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    # ── hmv_done — Topshirilgan vazifalar: fanlar ro'yxati ───
    if data == "hmv_done":
        submitted = _get_submitted_homeworks(class_id, student_id)
        if not submitted:
            await query.edit_message_text(
                "✅ *Topshirilgan vazifalar*\n\n❌ Hozircha hech qanday vazifa topshirmagansiz.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_hw")
                ]])
            )
            return
        # Fanlar bo'yicha guruhlash
        subjects_map: dict[int, dict] = {}
        for hw, sub in submitted:
            sid = hw['subject_id']
            if sid not in subjects_map:
                subjects_map[sid] = {'name': hw['subject_name'], 'count': 0}
            subjects_map[sid]['count'] += 1
        btns = []
        for sid, info in subjects_map.items():
            btns.append([InlineKeyboardButton(
                f"✅ 📚 {info['name']} ({info['count']} ta)",
                callback_data=f"hmv_done_s_{sid}"
            )])
        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_hw")])
        await query.edit_message_text(
            "✅ *Topshirilgan vazifalar*\n\nFan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    # ── hmv_done_s_{sid} — Topshirilgan, bitta fan detail ────
    if data.startswith("hmv_done_s_"):
        sid       = int(data[len("hmv_done_s_"):])
        submitted = _get_submitted_homeworks(class_id, student_id)
        subject   = db.get_subject(sid)
        # Faqat shu fanga tegishlilari
        my_subs   = [(hw, sub) for hw, sub in submitted if hw['subject_id'] == sid]
        if not my_subs:
            await query.edit_message_text(
                "❌ Bu fan bo'yicha topshirma topilmadi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_done")
                ]])
            )
            return

        await query.edit_message_text(
            f"✅ *{subject['name']} — topshirilgan vazifalar:*",
            parse_mode="Markdown"
        )

        for hw, sub in my_subs:
            d_fmt     = date.fromisoformat(hw['date']).strftime("%d.%m.%Y")
            grade_row = db.get_submission_grade(student_id, sid, hw['date'])
            sub_files = db.get_submission_files(sub['id'])

            # ── O'qituvchi vazifasi ──
            hw_cap   = f"📝 O'qituvchi vazifasi | {subject['name']} | {d_fmt}"
            hw_id    = hw['id']
            files    = db.get_lesson_files(hw_id) if hw_id else []
            hw_content  = hw['content'] or ""
            hw_file_id  = hw['file_id'] or ""
            hw_file_type = hw['file_type'] or ""
            if hw_content or hw_file_id:
                await send_media(query.message, hw_content, hw_file_id or None,
                                 hw_file_type, hw_cap)
            for lf in files:
                await send_media(query.message, "", lf['file_id'], lf['file_type'], hw_cap)

            # ── O'quvchi topshirmasi ──
            sub_submitted = sub['submitted_at'] or ""
            from config import utc_to_tashkent
            sub_time = utc_to_tashkent(sub_submitted) if sub_submitted else ""
            late_txt = " ⚠️ _kech_" if sub['is_late'] else ""
            sub_cap  = f"📤 Sizning topshirmangiz | {d_fmt}{late_txt}"
            sub_content  = sub['content'] or ""
            sub_file_id  = sub['file_id'] or ""
            sub_file_type = sub['file_type'] or ""
            if sub_content or sub_file_id:
                await send_media(query.message, sub_content, sub_file_id or None,
                                 sub_file_type, sub_cap)
            for sf in sub_files:
                await send_media(query.message, "", sf['file_id'], sf['file_type'], sub_cap)

            # ── Baho va izoh ──
            info_lines = [f"📅 *Sana:* {d_fmt}  |  🕐 *Topshirildi:* {sub_time}{late_txt}"]
            if grade_row:
                info_lines.append(f"⭐ *Baho: {grade_row['score']} ball*")
                comment = grade_row['comment'] or ""
                if comment:
                    info_lines.append(f"💬 *O'qituvchi izohi:* {comment}")
            else:
                info_lines.append("⏳ _Baho hali qo'yilmagan_")
            await query.message.reply_text(
                "\n".join(info_lines),
                parse_mode="Markdown"
            )
            # O'qituvchi izoh faylini ko'rsatish
            if grade_row and grade_row['comment_file_id']:
                await send_media(
                    query.message, "",
                    grade_row['comment_file_id'],
                    grade_row['comment_file_type'] or "document",
                    "📎 O'qituvchi izohi fayli"
                )

        await query.message.reply_text(
            "🔙",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Topshirilgan vazifalar", callback_data="hmv_done")
            ]])
        )
        return

    # ── hmv_pend — Topshirilmagan vazifalar: fanlar ro'yxati ─
    if data == "hmv_pend":
        pending = _get_pending_homeworks(class_id, student_id)
        if not pending:
            await query.edit_message_text(
                "⬜️ *Topshirilmagan vazifalar*\n\n✅ Barcha vazifalar topshirilgan!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_hw")
                ]])
            )
            return
        # Fanlar bo'yicha guruhlash
        subjects_map: dict[int, dict] = {}
        for hw in pending:
            sid = hw['subject_id']
            if sid not in subjects_map:
                subjects_map[sid] = {'name': hw['subject_name'], 'count': 0}
            subjects_map[sid]['count'] += 1
        btns = []
        for sid, info in subjects_map.items():
            btns.append([InlineKeyboardButton(
                f"⬜️ 📚 {info['name']} ({info['count']} ta)",
                callback_data=f"hmv_pend_s_{sid}"
            )])
        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_hw")])
        await query.edit_message_text(
            "⬜️ *Topshirilmagan vazifalar*\n\nFan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    # ── hmv_pend_s_{sid} — Topshirilmagan, bitta fan detail ──
    if data.startswith("hmv_pend_s_"):
        sid     = int(data[len("hmv_pend_s_"):])
        pending = _get_pending_homeworks(class_id, student_id)
        subject = db.get_subject(sid)
        my_pend = [hw for hw in pending if hw['subject_id'] == sid]
        if not my_pend:
            await query.edit_message_text(
                "✅ Bu fan bo'yicha barcha vazifalar topshirilgan.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_pend")
                ]])
            )
            return

        await query.edit_message_text(
            f"⬜️ *{subject['name']} — topshirilmagan vazifalar:*",
            parse_mode="Markdown"
        )

        for hw in my_pend:
            d_fmt    = date.fromisoformat(hw['date']).strftime("%d.%m.%Y")
            dl_text  = _deadline_text(hw['deadline'])

            # ── O'qituvchi vazifasi ──
            hw_cap  = f"📝 Uyga vazifa | {subject['name']} | {d_fmt}"
            lessons = db.get_lessons(class_id, sid, hw['date'], "homework")
            if lessons:
                lesson = lessons[0]
                files  = db.get_lesson_files(lesson['id'])
                l_content  = lesson['content'] or ""
                l_file_id  = lesson['file_id'] or ""
                l_file_type = lesson['file_type'] or ""
                if l_content or l_file_id:
                    await send_media(query.message, l_content,
                                     l_file_id or None, l_file_type, hw_cap)
                for lf in files:
                    await send_media(query.message, "", lf['file_id'], lf['file_type'], hw_cap)

            # ── Ma'lumot va topshirish tugmasi (lesson_id orqali) ──
            info_lines = [f"📅 *Yuklangan sana:* {d_fmt}"]
            if dl_text:
                info_lines.append(dl_text)
            else:
                info_lines.append("⏳ _Deadline belgilanmagan_")

            # lesson_id ni callback ga qo'shish
            lesson_id_for_cb = hw['id']  # lessons jadvalidagi id
            await query.message.reply_text(
                "\n".join(info_lines),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "📤 Vazifa yuklash",
                        callback_data=f"stu_submit_{sid}_{hw['date']}"
                    )],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data="hmv_pend")],
                ])
            )

        return

    # ── stu_subj_list_{type}_{date} — Fan tanlash menyusiga qaytish ──
    if data.startswith("stu_subj_list_"):
        # format: stu_subj_list_hw_2026-02-27  yoki  stu_subj_list_topic_2026-02-27
        rest         = data[len("stu_subj_list_"):]
        # content_type: hw yoki topic
        if rest.startswith("hw_"):
            content_type = "hw"
            date_str     = rest[3:]
            label        = "📚 *Bugungi vazifalar*"
            prefix       = f"view_hw_{date_str}"
        else:
            content_type = "topic"
            date_str     = rest[6:]   # "topic_" = 6 belgi
            label        = "📖 *Bugungi mavzular*"
            prefix       = f"view_topic_{date_str}"

        subjects = db.get_subjects(class_id=class_id)
        if not subjects:
            await query.edit_message_text("❌ Bu sinfda fan qo'shilmagan.")
            return

        from utils.keyboards import kb_subjects
        back_cb = f"stu_subj_list_{content_type}_{date_str}"
        await query.edit_message_text(
            f"{label} — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_subjects(subjects, prefix=prefix, back=back_cb)
        )
        return

    # ── stu_hw_dates — homework bo'lgan sanalar ro'yxati ──────────
    if data == "stu_hw_dates":
        rows = db.get_homework_dates(class_id)
        if not rows:
            await query.edit_message_text(
                "❌ Hozircha hech qanday vazifa yuklangan emas.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
                ]])
            )
            return

        # Sanalarni birlashtir (bir sanada bir necha fan bo'lishi mumkin)
        dates_seen = {}
        for r in rows:
            d = r['date']
            if d not in dates_seen:
                dates_seen[d] = r['deadline']  # birinchi deadline (yoki None)

        btns = []
        today_str = date.today().isoformat()
        for d_str, deadline in list(dates_seen.items())[:20]:  # max 20 sana
            d_obj   = date.fromisoformat(d_str)
            label   = d_obj.strftime("%d.%m.%Y")
            if d_str == today_str:
                label = f"📅 Bugun ({label})"
            else:
                label = f"📅 {label}"
            # Deadline yaqin bo'lsa belgi qo'y
            if deadline:
                try:
                    dl = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                    if datetime.now() > dl:
                        label += " ⚠️"
                except Exception:
                    pass
            btns.append([InlineKeyboardButton(label, callback_data=f"stu_hw_date_{d_str}")])

        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
        await query.edit_message_text(
            "📝 *Vazifalar — Sana tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    # ── stu_hw_date_{date} — Sana tanlandi: o'sha sanada fanlar ──
    if data.startswith("stu_hw_date_"):
        date_str = data[len("stu_hw_date_"):]
        lessons  = db.get_homework_subjects_for_date(class_id, date_str)
        if not lessons:
            await query.edit_message_text(
                f"❌ {date_str} sanasida vazifa yo'q.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="stu_hw_dates")
                ]])
            )
            return

        d_fmt = date.fromisoformat(date_str).strftime("%d.%m.%Y")
        btns  = []
        for lesson in lessons:
            subj_name = lesson['subject_name']
            # O'quvchi topshirganmi?
            existing = db.get_student_submission(student_id, lesson['subject_id'], date_str)
            if existing:
                status = "⚠️ Kech" if existing['is_late'] else "✅"
                label  = f"{status} {subj_name}"
            else:
                label = f"📚 {subj_name}"
            btns.append([InlineKeyboardButton(
                label,
                callback_data=f"stu_hw_subj_{lesson['subject_id']}_{date_str}"
            )])

        btns.append([InlineKeyboardButton("🔙 Sanalar", callback_data="stu_hw_dates")])
        await query.edit_message_text(
            f"📝 *Vazifalar — {d_fmt}*\nFan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    # ── stu_hw_subj_{subject_id}_{date} — Fan detail sahifasi ────
    if data.startswith("stu_hw_subj_"):
        rest       = data[len("stu_hw_subj_"):]
        last_under = rest.rfind("_")
        subject_id = int(rest[:last_under])
        date_str   = rest[last_under + 1:]

        lessons = db.get_lessons(class_id, subject_id, date_str, "homework")
        subject = db.get_subject(subject_id)
        d_fmt   = date.fromisoformat(date_str).strftime("%d.%m.%Y")

        if not lessons:
            await query.edit_message_text(
                f"❌ {subject['name']} | {d_fmt} — vazifa yo'q.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"stu_hw_date_{date_str}")
                ]])
            )
            return

        await query.edit_message_text(
            f"📝 *{subject['name']} | {d_fmt}*\n\n"
            f"Bu kunda {len(lessons)} ta vazifa yuklangan:",
            parse_mode="Markdown"
        )

        # Har bir lesson uchun alohida blok
        for idx, lesson in enumerate(lessons, 1):
            lesson_id = lesson['id']
            deadline  = lesson['deadline']
            dl_text   = _deadline_text(deadline)

            # O'qituvchi vazifa matni va fayllarini ko'rsatish
            cap = f"📝 Vazifa #{idx} | {subject['name']} | {d_fmt}"
            files = db.get_lesson_files(lesson_id)
            if lesson['content'] or lesson['file_id']:
                await send_media(query.message, lesson['content'] or "",
                                 lesson['file_id'], lesson['file_type'] or "", cap)
            for f in files:
                await send_media(query.message, "", f['file_id'], f['file_type'], cap)

            # O'quvchi bu lesson uchun topshirganmi?
            existing = db.get_student_submission(student_id, subject_id, date_str,
                                                  lesson_id=lesson_id)
            grade    = db.get_submission_grade(student_id, subject_id, date_str) \
                       if not existing else None

            info_lines = [f"📌 *Vazifa #{idx}*"]
            if dl_text:
                info_lines.append(dl_text)

            if existing:
                from config import utc_to_tashkent
                sub_time = utc_to_tashkent(existing['submitted_at']) if existing['submitted_at'] else ""
                late_txt = " _(kech ⚠️)_" if existing['is_late'] else ""
                info_lines.append(f"✅ *Topshirildi:* {sub_time}{late_txt}")

                # Topshirma fayllarini ko'rsatish
                sub_files = db.get_submission_files(existing['id'])
                if existing['content'] or existing['file_id']:
                    await send_media(query.message,
                                     existing['content'] or "",
                                     existing['file_id'],
                                     existing['file_type'] or "",
                                     f"📤 Sizning javobingiz #{idx}")
                for sf in sub_files:
                    await send_media(query.message, "", sf['file_id'], sf['file_type'], "")

                # Baho
                sub_grade = db.get_submission_grade(student_id, subject_id, date_str)
                if sub_grade:
                    info_lines.append(f"⭐ *Baho: {sub_grade['score']} ball*")
                    if sub_grade['comment']:
                        info_lines.append(f"💬 _{sub_grade['comment']}_")

                btn_label = "🔄 Qayta topshirish"
            else:
                info_lines.append("⬜️ _Hali topshirilmagan_")
                btn_label = "📤 Topshirish"

            await query.message.reply_text(
                "\n".join(info_lines),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        btn_label,
                        callback_data=f"stu_submitl_{lesson_id}"   # lesson_id bo'yicha
                    )],
                    [InlineKeyboardButton("🔙 Orqaga", callback_data=f"stu_hw_date_{date_str}")]
                ])
            )
        return

    # ── stu_submitl_{lesson_id} — lesson_id bo'yicha topshirish ──
    if data.startswith("stu_submitl_"):
        lesson_id  = int(data[len("stu_submitl_"):])
        lesson     = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text("❌ Vazifa topilmadi.")
            return

        subject_id = lesson['subject_id']
        date_str   = lesson['date']
        deadline   = lesson['deadline']
        subject    = db.get_subject(subject_id)
        dl_text    = _deadline_text(deadline)

        context.user_data['submit_subject_id'] = subject_id
        context.user_data['submit_class_id']   = class_id
        context.user_data['submit_date']        = date_str
        context.user_data['submit_deadline']    = deadline
        context.user_data['submit_lesson_id']   = lesson_id
        context.user_data['waiting_for']        = 'homework_submission'

        d_fmt = date.fromisoformat(date_str).strftime("%d.%m.%Y")
        msg   = f"📤 *Vazifa topshirish*\n📚 {subject['name']} | 📅 {d_fmt}\n"
        if dl_text:
            msg += f"{dl_text}\n"
        msg += "\nMatn, rasm, video yoki fayl yuboring:"

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
            ]])
        )
        return

    # ── stu_submit_{subject_id}_{date} — Topshirishni boshlash ───
    if data.startswith("stu_submit_"):
        rest       = data[len("stu_submit_"):]
        last_under = rest.rfind("_")
        subject_id = int(rest[:last_under])
        date_str   = rest[last_under + 1:]

        # Deadline olish — lesson_id ni ham saqlash
        lessons  = db.get_lessons(class_id, subject_id, date_str, "homework")
        deadline = lessons[0]['deadline'] if lessons else None
        lesson_id = lessons[0]['id'] if lessons else None

        subject = db.get_subject(subject_id)
        dl_text = _deadline_text(deadline)

        context.user_data['submit_subject_id'] = subject_id
        context.user_data['submit_class_id']   = class_id
        context.user_data['submit_date']        = date_str
        context.user_data['submit_deadline']    = deadline
        context.user_data['submit_lesson_id']   = lesson_id
        context.user_data['waiting_for']        = 'homework_submission'

        msg = (
            f"📤 *Vazifa topshirish*\n"
            f"📚 {subject['name']} | 📅 {date_str}\n"
        )
        if dl_text:
            msg += f"{dl_text}\n"
        msg += "\nMatn, rasm, video yoki fayl yuboring:"

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
            ]])
        )
        return

    # ── view_hw_{date}_{subj_id} — Bugungi vazifalar ─────────────
    if data.startswith("view_hw_") or data.startswith("view_topic_"):
        content_type = "homework" if data.startswith("view_hw_") else "topic"
        rest         = data.replace("view_hw_", "").replace("view_topic_", "")
        last_under   = rest.rfind("_")
        date_str     = rest[:last_under]
        subject_id   = int(rest[last_under + 1:])

        lessons = db.get_lessons(class_id, subject_id, date_str, content_type)
        subject = db.get_subject(subject_id)
        label   = "📝 Uyga vazifa" if content_type == "homework" else "📖 Mavzu"
        d_fmt   = date.fromisoformat(date_str).strftime("%d.%m.%Y")

        if not lessons:
            await query.edit_message_text(
                f"{label} | 📚 {subject['name']} | 📅 {d_fmt}\n\n❌ Bu kunda ma'lumot yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
                ]])
            )
            return

        # Sarlavha
        await query.edit_message_text(
            f"{label} | 📚 *{subject['name']}* | 📅 {d_fmt}\n"
            f"{'📌 ' + str(len(lessons)) + ' ta vazifa' if len(lessons) > 1 else ''}",
            parse_mode="Markdown"
        )

        if content_type == "homework":
            # Har bir lesson uchun alohida blok
            for idx, lesson in enumerate(lessons, 1):
                lesson_id = lesson['id']
                dl_text   = _deadline_text(lesson['deadline'])
                cap       = f"📝 {'Vazifa #' + str(idx) + ' | ' if len(lessons) > 1 else ''}{subject['name']} | {d_fmt}"

                # O'qituvchi fayli
                files = db.get_lesson_files(lesson_id)
                if lesson['content'] or lesson['file_id']:
                    await send_media(query.message, lesson['content'] or "",
                                     lesson['file_id'], lesson['file_type'] or "", cap)
                for f in files:
                    await send_media(query.message, "", f['file_id'], f['file_type'], cap)

                # Holat: topshirilganmi?
                existing = db.get_student_submission(student_id, subject_id, date_str,
                                                      lesson_id=lesson_id)
                info_lines = []
                if len(lessons) > 1:
                    info_lines.append(f"📌 *Vazifa #{idx}*")
                if dl_text:
                    info_lines.append(dl_text)

                if existing:
                    from config import utc_to_tashkent
                    sub_time = utc_to_tashkent(existing['submitted_at']) if existing['submitted_at'] else ""
                    late_txt = " _(kech ⚠️)_" if existing['is_late'] else ""
                    info_lines.append(f"✅ *Topshirildi:* {sub_time}{late_txt}")

                    sub_files = db.get_submission_files(existing['id'])
                    if existing['content'] or existing['file_id']:
                        await send_media(query.message,
                                         existing['content'] or "",
                                         existing['file_id'],
                                         existing['file_type'] or "",
                                         f"📤 Sizning javobingiz")
                    for sf in sub_files:
                        await send_media(query.message, "", sf['file_id'], sf['file_type'], "")

                    sub_grade = db.get_submission_grade(student_id, subject_id, date_str)
                    if sub_grade:
                        info_lines.append(f"⭐ *Baho: {sub_grade['score']} ball*")
                        if sub_grade['comment']:
                            info_lines.append(f"💬 _{sub_grade['comment']}_")
                    btn_label = "🔄 Qayta topshirish"
                else:
                    info_lines.append("⬜️ _Hali topshirilmagan_")
                    btn_label = "📤 Topshirish"

                await query.message.reply_text(
                    "\n".join(info_lines) if info_lines else "👆 Vazifani ko'rdingiz:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(btn_label,
                                              callback_data=f"stu_submitl_{lesson_id}")],
                        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]
                    ])
                )
        else:
            # Mavzu — faqat fayllarni ko'rsatish
            cap = f"📖 {subject['name']} | {d_fmt}"
            for lesson in lessons:
                files = db.get_lesson_files(lesson['id'])
                if lesson['content'] or lesson['file_id']:
                    await send_media(query.message, lesson['content'] or "",
                                     lesson['file_id'], lesson['file_type'] or "", cap)
                for f in files:
                    await send_media(query.message, "", f['file_id'], f['file_type'], cap)
            await query.message.reply_text(
                "👆 Mavzu ko'rsatildi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
                ]])
            )
        return

    # ── stu_browse_topics / stu_browse_hw ─────────────────────────
    if data in ("stu_browse_topics", "stu_browse_hw"):
        content_type = "topic" if "topic" in data else "homework"
        if content_type == "homework":
            # Yangi flow — sanalar ro'yxati
            await handle_lesson_callback.__wrapped__(query, context, "stu_hw_dates") \
                if hasattr(handle_lesson_callback, '__wrapped__') else None
            # To'g'ridan-to'g'ri chaqirish
            rows = db.get_homework_dates(class_id)
            if not rows:
                await query.edit_message_text(
                    "❌ Hozircha hech qanday vazifa yuklangan emas.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
                    ]])
                )
                return
            dates_seen = {}
            for r in rows:
                d = r['date']
                if d not in dates_seen:
                    dates_seen[d] = r['deadline']
            btns = []
            today_str = date.today().isoformat()
            for d_str, deadline in list(dates_seen.items())[:20]:
                d_obj  = date.fromisoformat(d_str)
                label  = d_obj.strftime("%d.%m.%Y")
                label  = f"📅 Bugun ({label})" if d_str == today_str else f"📅 {label}"
                if deadline:
                    try:
                        dl = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                        if datetime.now() > dl:
                            label += " ⚠️"
                    except Exception:
                        pass
                btns.append([InlineKeyboardButton(label, callback_data=f"stu_hw_date_{d_str}")])
            btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
            await query.edit_message_text(
                "📝 *Vazifalar — Sana tanlang:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )
            return
        else:
            # Mavzular — to'g'ridan-to'g'ri mavzu nomi + sana ro'yxati
            topics = db.get_topics_for_class(class_id)
            if not topics:
                await query.edit_message_text(
                    "📖 *Mavzular ro'yxati*\n\n❌ Hozircha hech qanday mavzu yuklanmagan.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
                    ]])
                )
                return
            btns = []
            for t in topics[:30]:  # max 30 ta
                d_fmt   = date.fromisoformat(t['date']).strftime("%d.%m")
                # Mavzu matni yoki fayl belgisi
                if t['content']:
                    preview = t['content'][:25] + ("…" if len(t['content']) > 25 else "")
                else:
                    preview = "📎 fayl"
                label = f"📖 {t['subject_name']} | {d_fmt} — {preview}"
                btns.append([InlineKeyboardButton(
                    label[:60],
                    callback_data=f"stu_topic_view_{t['id']}"
                )])
            btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
            await query.edit_message_text(
                "📖 *Mavzular ro'yxati:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )
            return

    # ── stu_topic_view_{id} — Bitta mavzuni ko'rish ───────────────
    if data.startswith("stu_topic_view_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text(
                "❌ Mavzu topilmadi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="stu_browse_topics")
                ]])
            )
            return
        d_fmt = date.fromisoformat(lesson['date']).strftime("%d.%m.%Y")
        header = (
            f"📖 *Mavzu*\n"
            f"📚 {lesson['subject_name']} | 📅 {d_fmt}\n\n"
        )
        await query.edit_message_text(header, parse_mode="Markdown")
        files = db.get_lesson_files(lesson_id)
        cap   = f"📖 {lesson['subject_name']} | {d_fmt}"
        if lesson['content'] or lesson['file_id']:
            await send_media(query.message, lesson['content'] or "", lesson['file_id'], lesson['file_type'] or "", cap)
        for f in files:
            await send_media(query.message, "", f['file_id'], f['file_type'], cap)
        await query.message.reply_text(
            "🔙",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Mavzular ro'yxati", callback_data="stu_browse_topics")
            ]])
        )
        return


# ══════════════════════════════════════════════════════════
#  O'QUVCHI BAHOLAR
# ══════════════════════════════════════════════════════════

async def handle_student_grades_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    user_id = query.from_user.id
    wl = db.get_whitelist_user(user_id)
    if not wl:
        return

    if data.startswith("stu_grades_date_"):
        date_str   = data.replace("stu_grades_date_", "")
        student_id = wl['telegram_id']

        records  = db.get_student_grades(student_id)
        today_rs = [r for r in records if r['date'] == date_str]
        d_fmt    = date.fromisoformat(date_str).strftime('%d.%m.%Y')

        if not today_rs:
            await query.edit_message_text(
                f"⭐ *Baholarim — {d_fmt}*\n\n❌ Bu kunda baholanmadingiz.",
                parse_mode="Markdown"
            )
            return

        by_subj = {}
        for r in today_rs:
            by_subj.setdefault(r['subject_name'], []).append(r)

        CRITERIA_LABEL = {
            'homework':      '📝 Uyga vazifa',
            'participation': '🙋 Darsda faollik',
            'discipline':    '🧑‍💻 Intizom',
        }
        lines = [f"⭐ *Baholarim — {d_fmt}*\n"]
        for subj_name, items in by_subj.items():
            lines.append(f"📚 *{subj_name}:*")
            for item in items:
                label = CRITERIA_LABEL.get(item['criteria'], item['criteria'])
                lines.append(f"  {label}: *{item['score']}* ball")
                if item['comment']:
                    lines.append(f"  💬 _{item['comment']}_")
            lines.append("")

        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")