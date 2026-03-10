"""
handlers/teacher/waiting.py — O'qituvchi waiting holatlari

Yangiliklar (v2):
  tch_deadline     — ixtiyoriy deadline kiritish (matn/fayl saqlanganidan keyin)
  tch_sub_comment  — topshirmaga izoh + baho (view_sub_ dan)
"""
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import db
from utils.media import extract_file
from utils.keyboards import kb_teacher_files


async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting: str):

    # ── Dars matni/fayl ───────────────────────────────────────────
    if waiting == 'tch_lesson_content':
        teacher    = db.get_teacher(update.effective_user.id)
        teacher_id = teacher['id'] if teacher else None
        class_id   = context.user_data.get('teacher_class')
        subject_id = context.user_data.get('teacher_subject')
        date_str   = context.user_data.get('teacher_date') or context.user_data.get('tch_date')
        content_type = context.user_data.get('content_type') or context.user_data.get('tch_content_type', 'homework')

        file_id, file_type, caption = extract_file(update.message)
        content = caption or update.message.text or ""

        if not content and not file_id:
            await update.message.reply_text("❌ Matn, rasm, video yoki fayl yuboring.")
            return

        lesson_id = db.save_lesson(
            teacher_id, class_id, subject_id, date_str,
            content_type, content, file_id, file_type
        )
        context.user_data['tmp_lesson_id'] = lesson_id

        label = "📝 Uyga vazifa" if content_type == 'homework' else "📖 Mavzu"

        # Homework bo'lsa — deadline so'rash (ixtiyoriy)
        if content_type == 'homework':
            context.user_data['waiting_for'] = 'tch_deadline'
            await update.message.reply_text(
                f"✅ *{label} saqlandi!*\n\n"
                f"⏰ *Deadline belgilaysizmi?* _(ixtiyoriy)_\n\n"
                f"Format: *KK.OO.YYYY HH:MM*\n"
                f"Masalan: *28.02.2026 23:59*\n\n"
                f"_Deadline kerak bo'lmasa — \"Yo'q\" tugmasini bosing._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Yo'q, deadline siz", callback_data="tch_deadline_skip")
                ]])
            )
        else:
            context.user_data['waiting_for'] = 'tch_extra_files'
            await update.message.reply_text(
                f"✅ *{label} saqlandi!*\n\n"
                f"📎 *Yana fayl qo'shmoqchimisiz?*\n"
                f"_(Yuboring yoki ✅ Tayyor tugmasini bosing)_",
                parse_mode="Markdown",
                reply_markup=kb_teacher_files()
            )
    
    # ── GURUHGA vazifa content ────────────────────────────────────
    elif waiting == 'tch_hw_content_group':
        user_id = update.effective_user.id
        teacher_school_id = context.user_data.get('teacher_school_id')
        if teacher_school_id:
            teacher = db.get_teacher_with_school(user_id, teacher_school_id)
        else:
            teacher = db.get_teacher(user_id)
        teacher_id = teacher['id'] if teacher else None
        group_id = context.user_data.get('teacher_group')
        date_str = context.user_data.get('teacher_lesson_date')
        
        group = db.get_group(group_id)
        if not group:
            await update.message.reply_text("❌ Guruh topilmadi.")
            return
        
        file_id, file_type, caption = extract_file(update.message)
        content = caption or update.message.text or ""
        
        if not content and not file_id:
            await update.message.reply_text("❌ Matn, rasm, video yoki fayl yuboring.")
            return
        
        # Guruhdagi barcha sinflarga lesson yaratish
        classes = db.get_group_classes(group_id)
        lesson_ids = []
        
        for cls in classes:
            lesson_id = db.save_lesson(
                teacher_id, cls['id'], group['subject_id'], date_str,
                'homework', content, file_id, file_type
            )
            lesson_ids.append(lesson_id)
        
        # Birinchi lesson_id ni saqlaymiz (deadline uchun)
        context.user_data['tmp_lesson_ids'] = lesson_ids
        context.user_data['tmp_group_id'] = group_id
        
        # Deadline so'rash
        context.user_data['waiting_for'] = 'tch_deadline_group'
        class_names = ", ".join(c['name'] for c in classes)
        
        await update.message.reply_text(
            f"✅ *Vazifa guruhga yuborildi!*\n\n"
            f"👥 Guruh: *{group['group_name']}*\n"
            f"🏫 Sinflar: {class_names}\n"
            f"📚 Fan: {group['subject_name']}\n\n"
            f"⏰ *Deadline belgilaysizmi?* _(ixtiyoriy)_\n\n"
            f"Format: *KK.OO.YYYY HH:MM*\n"
            f"Masalan: *28.02.2026 23:59*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭ Yo'q, deadline siz", callback_data="tch_deadline_group_skip")
            ]])
        )

    # ── Deadline kiritish ─────────────────────────────────────────
    elif waiting == 'tch_deadline':
        text = (update.message.text or "").strip()
        lesson_id = context.user_data.get('tmp_lesson_id')

        try:
            dl = datetime.strptime(text, "%d.%m.%Y %H:%M")
            deadline_str = dl.strftime("%Y-%m-%d %H:%M")
            db.update_lesson_deadline(lesson_id, deadline_str)
            dl_fmt = dl.strftime("%d.%m.%Y %H:%M")
            await update.message.reply_text(
                f"✅ *Deadline belgilandi: {dl_fmt}*\n\n"
                f"📎 *Yana fayl qo'shmoqchimisiz?*",
                parse_mode="Markdown",
                reply_markup=kb_teacher_files()
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Format noto'g'ri. *KK.OO.YYYY HH:MM* ko'rinishida kiriting:\n"
                "Masalan: *28.02.2026 23:59*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Yo'q, deadline siz", callback_data="tch_deadline_skip")
                ]])
            )
            return

        context.user_data['waiting_for'] = 'tch_extra_files'
    
    # ── GURUHGA deadline ──────────────────────────────────────────
    elif waiting == 'tch_deadline_group':
        text = (update.message.text or "").strip()
        lesson_ids = context.user_data.get('tmp_lesson_ids', [])
        group_id = context.user_data.get('tmp_group_id')
        
        try:
            dl = datetime.strptime(text, "%d.%m.%Y %H:%M")
            deadline_str = dl.strftime("%Y-%m-%d %H:%M")
            
            # Barcha lesson'larga deadline qo'yish
            for lesson_id in lesson_ids:
                db.update_lesson_deadline(lesson_id, deadline_str)
            
            group = db.get_group(group_id)
            dl_fmt = dl.strftime("%d.%m.%Y %H:%M")
            
            await update.message.reply_text(
                f"✅ *Tayyor!*\n\n"
                f"👥 Guruh: *{group['group_name']}*\n"
                f"⏰ Deadline: {dl_fmt}\n\n"
                f"_Barcha sinflarga vazifa yuborildi va deadline belgilandi._",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Format noto'g'ri. *KK.OO.YYYY HH:MM* ko'rinishida kiriting:\n"
                "Masalan: *28.02.2026 23:59*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Yo'q, deadline siz", callback_data="tch_deadline_group_skip")
                ]])
            )
            return
        
        # Tozalash
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('tmp_lesson_ids', None)
        context.user_data.pop('tmp_group_id', None)
        context.user_data.pop('teacher_group', None)

    # ── Qo'shimcha fayllar ────────────────────────────────────────
    elif waiting == 'tch_extra_files':
        lesson_id = context.user_data.get('tmp_lesson_id')
        if not lesson_id:
            return
        file_id, file_type, _ = extract_file(update.message)
        if file_id:
            db.add_lesson_file(lesson_id, file_id, file_type)
            await update.message.reply_text(
                "✅ Fayl biriktirildi.",
                reply_markup=kb_teacher_files()
            )
        else:
            await update.message.reply_text(
                "❌ Fayl yuborilmadi.",
                reply_markup=kb_teacher_files()
            )

    # ── Dars sanasini kiritish ────────────────────────────────────
    elif waiting == 'tch_lesson_date':
        text = update.message.text or ""
        try:
            from datetime import date as _date
            d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text(
                "❌ Noto'g'ri format. *KK.OO.YYYY* ko'rinishida kiriting:\nMasalan: *20.02.2026*",
                parse_mode="Markdown"
            )
            return
        context.user_data['tch_date']    = d.isoformat()
        context.user_data['waiting_for'] = 'tch_lesson_content'
        content_type = context.user_data.get('tch_content_type', 'homework')
        label = "📝 Uyga vazifa" if content_type == 'homework' else "📖 Mavzu"
        await update.message.reply_text(
            f"{label} | 📅 *{d.strftime('%d.%m.%Y')}*\n\nMazmunini kiriting (yoki fayl yuboring):",
            parse_mode="Markdown"
        )

    # ── Dars matnini tahrirlash ───────────────────────────────────
    elif waiting == 'tch_edit_content':
        new_text  = update.message.text or ""
        lesson_id = context.user_data.pop('tch_edit_lesson_id', None)
        if not lesson_id:
            context.user_data.pop('waiting_for', None)
            return
        if not new_text.strip():
            await update.message.reply_text("❌ Matn bo'sh bo'lishi mumkin emas.")
            return
        db.update_lesson_content(lesson_id, new_text.strip())
        context.user_data.pop('waiting_for', None)
        lesson = db.get_lesson(lesson_id)
        ctype  = "📝 Uyga vazifa" if lesson and lesson['content_type'] == 'homework' else "📖 Mavzu"
        await update.message.reply_text(
            f"✅ *{ctype} matni yangilandi!*\n\n_{new_text.strip()}_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Vazifaga qaytish", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── Deadline tahrirlash ───────────────────────────────────────
    elif waiting == 'tch_edit_deadline':
        text      = (update.message.text or "").strip()
        lesson_id = context.user_data.pop('tch_edit_lesson_id', None)
        context.user_data.pop('waiting_for', None)
        try:
            dl = datetime.strptime(text, "%d.%m.%Y %H:%M")
            deadline_str = dl.strftime("%Y-%m-%d %H:%M")
            db.update_lesson_deadline(lesson_id, deadline_str)
            dl_fmt = dl.strftime("%d.%m.%Y %H:%M")
            await update.message.reply_text(
                f"✅ *Deadline belgilandi: {dl_fmt}*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Vazifaga qaytish", callback_data=f"tch_lesson_{lesson_id}")
                ]])
            )
        except ValueError:
            context.user_data['tch_edit_lesson_id'] = lesson_id
            context.user_data['waiting_for'] = 'tch_edit_deadline'
            await update.message.reply_text(
                "❌ Format noto'g'ri. *KK.OO.YYYY HH:MM* ko'rinishida kiriting:\n"
                "Masalan: *28.02.2026 23:59*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
                ]])
            )

    # ── Izoh qo'shish/tahrirlash ──────────────────────────────────
    elif waiting == 'tch_edit_comment':
        comment   = (update.message.text or "").strip()
        lesson_id = context.user_data.pop('tch_edit_lesson_id', None)
        context.user_data.pop('waiting_for', None)
        if not comment:
            await update.message.reply_text("❌ Izoh matni bo'sh bo'lishi mumkin emas.")
            return
        db.update_lesson_comment(lesson_id, comment)
        await update.message.reply_text(
            f"✅ *Izoh saqlandi!*\n\n💬 _{comment}_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Vazifaga qaytish", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── Faylni almashtirish ───────────────────────────────────────
    elif waiting == 'tch_replace_file':
        lesson_id = context.user_data.get('tch_edit_lesson_id')
        file_id, file_type, _ = extract_file(update.message)
        if not file_id:
            await update.message.reply_text(
                "❌ Fayl topilmadi. Rasm, video yoki hujjat yuboring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
                ]])
            )
            return
        db.replace_lesson_main_file(lesson_id, file_id, file_type)
        context.user_data.pop('tch_edit_lesson_id', None)
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(
            "✅ *Fayl almashtirildi!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Vazifaga qaytish", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── Topshirmaga izoh (o'qituvchi) ────────────────────────────
    elif waiting == 'tch_sub_comment':
        comment    = (update.message.text or "").strip()
        sub_id     = context.user_data.get('tch_grade_sub_id')
        student_id = context.user_data.get('tch_grade_student_id')
        subject_id = context.user_data.get('tch_grade_subject_id')
        score      = context.user_data.get('tch_grade_score')
        teacher    = db.get_teacher(update.effective_user.id)

        if not comment:
            await update.message.reply_text(
                "❌ Izoh matni bo'sh. Yuboring yoki \"O'tkazib yuborish\" tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ O'tkazib yuborish",
                                         callback_data=f"vsub_skip_cmt_{sub_id}_{score}")
                ]])
            )
            return

        # Izoхni context ga saqlaymiz, file bosqichiga o'tamiz
        context.user_data['tch_grade_comment'] = comment
        context.user_data['waiting_for']        = 'tch_sub_cmt_file'

        wl   = db.get_whitelist_user(student_id) if student_id else None
        subj = db.get_subject(subject_id) if subject_id else None
        await update.message.reply_text(
            f"💬 *Izoh qabul qilindi!*\n"
            f"_{comment}_\n\n"
            f"📎 *Faylni izohga biriktirmoqchimisiz?*\n"
            f"_(Rasm, fayl yuboring yoki \"O'tkazib yuborish\" bosing)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭ Faylsiz saqlash",
                                     callback_data=f"vsub_skip_file_{sub_id}")
            ]])
        )

    # ── Izoh faylini biriktirish (o'qituvchi) ────────────────────
    elif waiting == 'tch_sub_cmt_file':
        sub_id     = context.user_data.pop('tch_grade_sub_id', None)
        student_id = context.user_data.pop('tch_grade_student_id', None)
        subject_id = context.user_data.pop('tch_grade_subject_id', None)
        class_id   = context.user_data.pop('tch_grade_class_id', None)
        score      = context.user_data.pop('tch_grade_score', None)
        date_str   = context.user_data.pop('tch_grade_date', None)
        comment    = context.user_data.pop('tch_grade_comment', None)
        context.user_data.pop('waiting_for', None)

        # Ko'p maktabli qo'llab-quvvatlash
        teacher_school_id = context.user_data.get('teacher_school_id')
        if teacher_school_id:
            teacher = db.get_teacher_with_school(update.effective_user.id, teacher_school_id)
        else:
            teacher = db.get_teacher(update.effective_user.id)
        
        file_id, file_type, _ = extract_file(update.message)

        if not file_id:
            await update.message.reply_text(
                "❌ Fayl yuborilmadi. Rasm yoki hujjat yuboring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Faylsiz saqlash",
                                         callback_data=f"vsub_skip_file_{sub_id}")
                ]])
            )
            # Context ni qayta tiklash (hali saqlana olmadi)
            context.user_data.update({
                'tch_grade_sub_id':     sub_id,
                'tch_grade_student_id': student_id,
                'tch_grade_subject_id': subject_id,
                'tch_grade_class_id':   class_id,
                'tch_grade_score':      score,
                'tch_grade_date':       date_str,
                'tch_grade_comment':    comment,
                'waiting_for':          'tch_sub_cmt_file',
            })
            return

        db.save_grade(
            student_id, teacher['id'], subject_id, class_id,
            'homework', score, date_str,
            comment=comment,
            comment_file_id=file_id,
            comment_file_type=file_type
        )
        wl   = db.get_whitelist_user(student_id)
        subj = db.get_subject(subject_id)
        await update.message.reply_text(
            f"✅ *Baho + izoh + fayl saqlandi!*\n"
            f"👤 {wl['full_name'] if wl else student_id}\n"
            f"📚 {subj['name'] if subj else subject_id}\n"
            f"⭐ *{score} ball*"
            + (f"\n💬 {comment}" if comment else ""),
            parse_mode="Markdown"
        )

    # ── Haftalik jadval vaqti (tws_time) ─────────────────────────
    elif waiting == 'tws_time':
        text = update.message.text or ""
        try:
            start, end = text.strip().split("-")
            start = start.strip(); end = end.strip()
        except ValueError:
            await update.message.reply_text(
                "❌ Format: *HH:MM-HH:MM*\nMasalan: *08:00-09:30*",
                parse_mode="Markdown"
            )
            return
        teacher_id = context.user_data.get('tws_teacher_id')
        class_id   = context.user_data.get('tws_class_id')
        group_id   = context.user_data.get('tws_group_id')
        subject_id = context.user_data.get('tws_subject_id')
        school_id  = context.user_data.get('school_id', 1)
        days       = context.user_data.get('tws_confirm_days', set())

        if group_id:
            # Guruh — barcha sinflarga bir xil slot
            class_ids = db.get_group_class_ids(group_id)
            for day in days:
                for cid in class_ids:
                    db.add_slot(teacher_id, cid, subject_id, day, start, end, school_id)
            group = db.get_group(group_id)
            target_label = f"👥 {group['group_name']} ({len(class_ids)} ta sinf)"
        else:
            for day in days:
                db.add_slot(teacher_id, class_id, subject_id, day, start, end, school_id)
            cls = db.get_class(class_id)
            target_label = f"🏫 {cls['name']}" if cls else "Sinf"

        context.user_data.pop('waiting_for', None)
        context.user_data.pop('tws_group_id', None)
        from config import WEEKDAY_LABELS
        days_str = ", ".join(WEEKDAY_LABELS[d] for d in sorted(days))
        await update.message.reply_text(
            f"✅ *Jadval qo'shildi!*\n{target_label}\n📅 {days_str}\n🕐 *{start}–{end}*",
            parse_mode="Markdown"
        )

    # ── Haftalik jadval vaqti tahrirlash (tws_edit_time) ─────────
    elif waiting == 'tws_edit_time':
        text = update.message.text or ""
        try:
            start, end = text.strip().split("-")
            start = start.strip(); end = end.strip()
        except ValueError:
            await update.message.reply_text(
                "❌ Format: *HH:MM-HH:MM*\nMasalan: *08:00-09:30*",
                parse_mode="Markdown"
            )
            return
        slot_id    = context.user_data.pop('tws_edit_slot_id', None)
        teacher_id = context.user_data.get('tws_teacher_id')
        if not slot_id:
            await update.message.reply_text("❌ Xato.")
            context.user_data.pop('waiting_for', None)
            return
        slot = db.get_slot(slot_id)
        db.update_slot_time(slot_id, start, end)
        context.user_data.pop('waiting_for', None)
        from config import WEEKDAY_LABELS
        from utils.keyboards import kb_tws_view_slots
        day = WEEKDAY_LABELS.get(slot['weekday'], str(slot['weekday'])) if slot else ''
        await update.message.reply_text(
            f"✅ *Vaqt yangilandi!*\n📅 {day} — *{start}–{end}*",
            parse_mode="Markdown"
        )
        if teacher_id:
            slots = db.get_slots(teacher_id=teacher_id)
            if slots:
                await update.message.reply_text(
                    "📅 Joriy jadval:",
                    reply_markup=kb_tws_view_slots(slots, teacher_id)
                )
    # ── O'qituvchi davomati — soat kiritish ──────────────────────
    elif waiting == 'tadm_hours':
        raw       = (update.message.text or "").strip()
        school_id = context.user_data.get('school_id') or context.user_data.get('tadm_school_id')
        date_str      = context.user_data.get('tadm_date')
        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})

        # /skip yoki bo'sh — soatsiz saqlash
        if raw.lower() in ('/skip', 'skip', ''):
            hours = None
        else:
            try:
                hours = float(raw.replace(',', '.'))
                if hours <= 0 or hours > 24:
                    await update.message.reply_text(
                        "❌ Noto'g'ri qiymat. 1–24 orasida son kiriting yoki /skip yuboring."
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "❌ Son kiriting (masalan: 6 yoki 5.5) yoki /skip yuboring."
                )
                return

        context.user_data.pop('waiting_for', None)

        if date_str:
            db.save_teacher_attendance(school_id, date_str, tadm_data, tadm_comments, hours=hours)

        for k in ('tadm_data', 'tadm_comments', 'tadm_teachers',
                  'tadm_date', 'tadm_pending_tid', 'tadm_pending_status', 'tadm_school_id'):
            context.user_data.pop(k, None)

        hours_txt = f"\n⏱ Dars soati: *{hours}* soat" if hours is not None else ""
        await update.message.reply_text(
            f"✅ *O'qituvchilar davomati saqlandi!*{hours_txt}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sanalar", callback_data="tadm_back_dates")
            ]])
        )

    # ── O'qituvchi davomati izoh ──────────────────────────────────
    elif waiting == 'tadm_comment':
        comment     = (update.message.text or "").strip()
        teacher_id  = context.user_data.pop('tadm_pending_tid', None)
        new_status  = context.user_data.pop('tadm_pending_status', 'late')
        context.user_data.pop('waiting_for', None)

        if not teacher_id:
            await update.message.reply_text("❌ Xato. Qaytadan urinib ko'ring.")
            return

        if not comment:
            await update.message.reply_text("❌ Izoh bo'sh bo'lmasin. Qaytadan yozing:")
            context.user_data['tadm_pending_tid']    = teacher_id
            context.user_data['tadm_pending_status'] = new_status
            context.user_data['waiting_for']         = 'tadm_comment'
            return

        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})

        tadm_data[str(teacher_id)]     = new_status
        tadm_comments[str(teacher_id)] = comment

        context.user_data['tadm_data']     = tadm_data
        context.user_data['tadm_comments'] = tadm_comments

        from config import ATTENDANCE_EMOJI, ATTENDANCE_LABEL
        status_emoji = ATTENDANCE_EMOJI.get(new_status, "⏰")
        status_label = ATTENDANCE_LABEL.get(new_status, new_status)
        teacher = db.get_teacher_by_id(teacher_id)
        t_name  = teacher['full_name'] if teacher else str(teacher_id)

        # late uchun soat so'raymiz
        if new_status == 'late':
            context.user_data['tadm_pending_tid'] = teacher_id
            context.user_data['waiting_for']      = 'tadm_hours_single'
            await update.message.reply_text(
                f"{status_emoji} *{t_name}* — {status_label}\n"
                f"💬 Izoh: _{comment}_\n\n"
                f"⏱ *Necha soat dars o'tdi?*\n"
                f"_Son kiriting (masalan: 6 yoki 5.5)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Bekor", callback_data=f"tadm_undo_{teacher_id}")
                ]])
            )
            return

        # excused — soat kerak emas, davomatga qaytamiz
        tadm_hours    = context.user_data.get('tadm_hours_data', {})
        date_str      = context.user_data.get('tadm_date', '')
        teacher_ids   = context.user_data.get('tadm_teachers', [])
        teachers_raw  = [db.get_teacher_by_id(tid) for tid in teacher_ids]
        teachers_data = [
            {
                'id':        t['id'],
                'full_name': t['full_name'],
                'status':    tadm_data.get(str(t['id']), 'present'),
                'comment':   tadm_comments.get(str(t['id']), ''),
                'hours':     tadm_hours.get(str(t['id'])),
            }
            for t in teachers_raw if t
        ]
        from utils.keyboards import kb_teacher_attendance
        await update.message.reply_text(
            f"{status_emoji} *{t_name}* — {status_label}\n💬 Izoh: _{comment}_\n\n"
            f"📋 *O'qituvchilar davomati* | 📅 {date_str}\n"
            f"_(✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli)_",
            parse_mode="Markdown",
            reply_markup=kb_teacher_attendance(teachers_data)
        )

    # ── O'qituvchi davomati — har bir soat kiritish ──────────────
    elif waiting == 'tadm_hours_single':
        raw        = (update.message.text or "").strip()
        teacher_id = context.user_data.pop('tadm_pending_tid', None)

        try:
            hours = float(raw.replace(',', '.'))
            if hours <= 0 or hours > 24:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ To'g'ri son kiriting (masalan: 6 yoki 5.5)"
            )
            if teacher_id:
                context.user_data['tadm_pending_tid'] = teacher_id
            return

        context.user_data.pop('waiting_for', None)

        tadm_hours = context.user_data.get('tadm_hours_data', {})
        if teacher_id:
            tadm_hours[str(teacher_id)] = hours
        context.user_data['tadm_hours_data'] = tadm_hours

        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})
        date_str      = context.user_data.get('tadm_date', '')
        teacher_ids   = context.user_data.get('tadm_teachers', [])
        teachers_raw  = [db.get_teacher_by_id(tid) for tid in teacher_ids]
        teachers_data = [
            {
                'id':        t['id'],
                'full_name': t['full_name'],
                'status':    tadm_data.get(str(t['id']), 'present'),
                'comment':   tadm_comments.get(str(t['id']), ''),
                'hours':     tadm_hours.get(str(t['id'])),
            }
            for t in teachers_raw if t
        ]
        from utils.keyboards import kb_teacher_attendance
        await update.message.reply_text(
            f"⏱ *{hours} soat* saqlandi\n\n"
            f"📋 *O'qituvchilar davomati* | 📅 {date_str}\n"
            f"_(✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli)_",
            parse_mode="Markdown",
            reply_markup=kb_teacher_attendance(teachers_data)
        )

    # ── O'qituvchi davomati — bitta soat kiritib saqlash ──────────
    elif waiting == 'tadm_hours_single_save':
        raw        = (update.message.text or "").strip()
        teacher_id = context.user_data.pop('tadm_pending_tid', None)

        try:
            hours = float(raw.replace(',', '.'))
            if hours <= 0 or hours > 24:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ To'g'ri son kiriting (masalan: 6 yoki 5.5)"
            )
            if teacher_id:
                context.user_data['tadm_pending_tid'] = teacher_id
            return

        context.user_data.pop('waiting_for', None)

        # Soatni saqlash
        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})
        date_str      = context.user_data.get('tadm_date', '')
        school_id     = context.user_data.get('tadm_school_id') or context.user_data.get('school_id')
        
        if teacher_id and date_str:
            status  = tadm_data.get(str(teacher_id), 'present')
            comment = tadm_comments.get(str(teacher_id), '')
            
            # Bazaga saqlash
            single_data = {str(teacher_id): status}
            single_comments = {str(teacher_id): comment} if comment else {}
            db.save_teacher_attendance(school_id, date_str, single_data, single_comments, hours=hours)
        
        # Tahrir rejimidan chiqish
        context.user_data.pop('tadm_editing_id', None)
        
        # Davomatni yangilash
        teacher_ids   = context.user_data.get('tadm_teachers', [])
        teachers_raw  = [db.get_teacher_by_id(tid) for tid in teacher_ids]
        
        # Yangi ma'lumotlarni yuklash
        attendance_records = db.get_teacher_attendance(school_id, date_str)
        existing = {r['teacher_id']: r['status'] for r in attendance_records}
        existing_comments = {
            r['teacher_id']: r['comment']
            for r in attendance_records
            if r.get('comment')
        }
        existing_hours = {
            r['teacher_id']: r['hours']
            for r in attendance_records
            if r.get('hours')
        }
        tadm_data = {str(t['id']): existing.get(t['id'], 'present') for t in teachers_raw}
        tadm_comments = {str(t['id']): existing_comments.get(t['id'], '') for t in teachers_raw}
        tadm_hours = {str(t['id']): existing_hours.get(t['id']) for t in teachers_raw}
        
        context.user_data['tadm_data']       = tadm_data
        context.user_data['tadm_comments']   = tadm_comments
        context.user_data['tadm_hours_data'] = tadm_hours
        
        teachers_data = [
            {
                'id':        t['id'],
                'full_name': t['full_name'],
                'status':    tadm_data.get(str(t['id']), 'present'),
                'comment':   tadm_comments.get(str(t['id']), ''),
                'hours':     tadm_hours.get(str(t['id'])),
            }
            for t in teachers_raw if t
        ]
        from utils.keyboards import kb_teacher_attendance
        await update.message.reply_text(
            f"✅ *{hours} soat* saqlandi\n\n"
            f"📋 *O'qituvchilar davomati* | 📅 {date_str}\n"
            f"_(✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli)_",
            parse_mode="Markdown",
            reply_markup=kb_teacher_attendance(teachers_data, editing_id=None)
        )

    # ── O'qituvchi davomati — umumiy soat (saqlash) ───────────────
    elif waiting == 'tadm_hours_global':
        raw = (update.message.text or "").strip()
        try:
            hours = float(raw.replace(',', '.'))
            if hours <= 0 or hours > 24:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ To'g'ri son kiriting (masalan: 6 yoki 5.5)"
            )
            return

        context.user_data.pop('waiting_for', None)

        school_id     = context.user_data.get('tadm_school_id') or context.user_data.get('school_id')
        date_str      = context.user_data.get('tadm_date')
        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})

        if date_str:
            db.save_teacher_attendance(school_id, date_str, tadm_data, tadm_comments, hours=hours)

        for k in ('tadm_data', 'tadm_comments', 'tadm_teachers',
                  'tadm_date', 'tadm_pending_tid', 'tadm_pending_status',
                  'tadm_school_id', 'tadm_hours_data'):
            context.user_data.pop(k, None)

        await update.message.reply_text(
            f"✅ *O'qituvchilar davomati saqlandi!*\n⏱ Dars soati: *{hours}* soat",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sanalar", callback_data="tadm_back_dates")
            ]])
        )

    # ── O'quvchi davomati izoh ───────────────────────────────────
    elif waiting == 'att_comment':
        comment    = (update.message.text or "").strip()
        student_id = context.user_data.pop('att_pending_student_id', None)
        new_status = context.user_data.pop('att_pending_status', 'late')
        context.user_data.pop('waiting_for', None)

        if not student_id:
            await update.message.reply_text("❌ Xato. Qaytadan urinib ko'ring.")
            return

        att_data = context.user_data.get('attendance_data', {})
        comments = context.user_data.get('attendance_comments', {})

        att_data[str(student_id)] = new_status
        if comment:
            comments[str(student_id)] = comment
        else:
            comments.pop(str(student_id), None)

        context.user_data['attendance_data']     = att_data
        context.user_data['attendance_comments'] = comments

        from config import ATTENDANCE_EMOJI, ATTENDANCE_LABEL
        status_emoji = ATTENDANCE_EMOJI.get(new_status, "⏰")
        status_label = ATTENDANCE_LABEL.get(new_status, new_status)

        wl     = db.get_whitelist_user(student_id)
        s_name = wl['full_name'] if wl else str(student_id)

        class_id = context.user_data.get('att_class_id') or context.user_data.get('teacher_class')
        date_str = context.user_data.get('attendance_date', '')
        students = db.get_whitelist_by_class(class_id)

        from utils.keyboards import kb_student_attendance
        d_fmt = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4] if date_str else ""

        cmt_line = f"\n💬 Izoh: _{comment}_" if comment else ""
        await update.message.reply_text(
            f"{status_emoji} *{s_name}* — {status_label}{cmt_line}\n\n"
            f"📋 *Davomat* | 📅 {d_fmt}\n"
            f"_(✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli)_\n"
            f"_💬 — izoh kiritilgan_",
            parse_mode="Markdown",
            reply_markup=kb_student_attendance(students, att_data, comments)
        )