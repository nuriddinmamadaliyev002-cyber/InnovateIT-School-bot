"""
handlers/teacher/callbacks.py — O'qituvchi inline callback handlerlari

Prefixlar:
  tch_*       — uyga vazifa / mavzu qo'shish
  att_*       — davomat toggle + saqlash
  tch_att_*   — o'qituvchining o'z davomati (oldingi oy)
  grade_*     — baholash
  rating_*    — reyting ko'rish
  tws_*       — o'qituvchi haftalik jadval (admin sozlaydi)
  tadm_*      — o'qituvchi davomati (admin ko'radi)
"""
from datetime import date, timedelta, datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import db, ATTENDANCE_EMOJI, ATTENDANCE_LABEL, CRITERIA_LABELS, SCORE_EMOJI
from utils.keyboards import kb_cancel
from utils.keyboards import (
    kb_cancel_teacher, kb_teacher_subjects, kb_dates,
    kb_grade_criteria, kb_grade_students, kb_grade_score,
    kb_tws_teachers, kb_tws_classes, kb_tws_subjects, kb_tws_weekdays, kb_tws_view_slots,
    kb_teacher_attendance, kb_teacher_att_dates,
)
from handlers.teacher.attendance import start_attendance, show_attendance, next_status


# ══════════════════════════════════════════════════════════
#  O'QUVCHILAR DAVOMATI (sinf → fan → sana → toggle → save)
# ══════════════════════════════════════════════════════════

async def handle_attendance_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):

    if data.startswith("att_toggle_"):
        student_id = int(data.split("_")[-1])
        att_data   = context.user_data.get('attendance_data', {})
        current    = att_data.get(str(student_id), 'present')
        new_status = next_status(current)
        att_data[str(student_id)] = new_status
        context.user_data['attendance_data'] = att_data

        # late yoki excused — izoh so'rash
        if new_status in ('late', 'excused'):
            context.user_data['att_pending_student_id'] = student_id
            context.user_data['att_pending_status']     = new_status
            context.user_data['waiting_for']            = 'att_comment'
            wl = db.get_whitelist_user(student_id)
            name   = wl['full_name'] if wl else str(student_id)
            s_label = "⏰ Kech keldi" if new_status == 'late' else "📝 Sababli"
            hint    = ("⏰ Qancha vaqt kech qoldi? _(masalan: 15 daqiqa)_"
                       if new_status == 'late'
                       else "📝 Sabab nima? _(izoh yozing)_")
            prompt  = f"*{name}* — {s_label}\n\n{hint}"
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            await query.edit_message_text(
                prompt,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Izohlarsiz qoldirish",
                                         callback_data=f"att_no_comment_{student_id}"),
                    InlineKeyboardButton("❌ Bekor", callback_data=f"att_undo_{student_id}"),
                ]])
            )
        else:
            # present yoki absent — izoh kerak emas, tozalaymiz
            comments = context.user_data.get('attendance_comments', {})
            if new_status == 'present':
                comments.pop(str(student_id), None)
            context.user_data['attendance_comments'] = comments

            class_id = context.user_data.get('att_class_id')
            date_str = context.user_data.get('attendance_date')
            students = db.get_whitelist_by_class(class_id)
            await show_attendance(query, context, students, date_str, is_new=False)

    # ── Izohlarsiz qoldirish ──────────────────────────────────
    elif data.startswith("att_no_comment_"):
        student_id = int(data.split("_")[-1])
        context.user_data.pop('att_pending_student_id', None)
        context.user_data.pop('att_pending_status', None)
        context.user_data.pop('waiting_for', None)

        class_id = context.user_data.get('att_class_id')
        date_str = context.user_data.get('attendance_date')
        students = db.get_whitelist_by_class(class_id)
        await show_attendance(query, context, students, date_str, is_new=False)

    # ── Toggle ni bekor qilish (holat qaytariladi) ────────────
    elif data.startswith("att_undo_"):
        student_id = int(data.split("_")[-1])
        att_data   = context.user_data.get('attendance_data', {})
        # Avvalgi statusga qaytarish — next_status ni teskari aylantirish
        reverse = {'absent': 'present', 'late': 'absent', 'excused': 'late', 'present': 'excused'}
        current = att_data.get(str(student_id), 'present')
        att_data[str(student_id)] = reverse.get(current, 'present')
        context.user_data['attendance_data'] = att_data
        context.user_data.pop('att_pending_student_id', None)
        context.user_data.pop('att_pending_status', None)
        context.user_data.pop('waiting_for', None)

        class_id = context.user_data.get('att_class_id')
        date_str = context.user_data.get('attendance_date')
        students = db.get_whitelist_by_class(class_id)
        await show_attendance(query, context, students, date_str, is_new=False)

    elif data == "att_save":
        class_id   = context.user_data.get('att_class_id')
        subject_id = context.user_data.get('att_subject_id', 0)
        date_str   = context.user_data.get('attendance_date')
        att_data   = context.user_data.get('attendance_data', {})
        comments   = context.user_data.get('attendance_comments', {})
        if class_id and date_str:
            db.save_attendance(class_id, subject_id, date_str, att_data, comments)
        context.user_data.pop('attendance_data', None)
        context.user_data.pop('attendance_comments', None)
        await query.edit_message_text("✅ *Davomat saqlandi!*", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════
#  BAHOLASH
# ══════════════════════════════════════════════════════════

async def handle_grading_callback(query, context: ContextTypes.DEFAULT_TYPE,
                                   data: str, user_id: int):
    # Ko'p maktabli qo'llab-quvvatlash
    teacher_school_id = context.user_data.get('teacher_school_id')
    if teacher_school_id:
        teacher = db.get_teacher_with_school(user_id, teacher_school_id)
    else:
        teacher = db.get_teacher(user_id)
    
    if not teacher:
        return

    if data.startswith("grade_class_"):
        class_id = int(data.split("_")[-1])
        context.user_data['grade_class_id'] = class_id
        subjects = db.get_teacher_subjects_for_class(teacher['id'], class_id)
        cls = db.get_class(class_id)
        btns = [
            [InlineKeyboardButton(s['name'], callback_data=f"grade_subj_{s['id']}")]
            for s in subjects
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        await query.edit_message_text(
            f"⭐ Baholash | 🏫 *{cls['name']}* — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif data.startswith("grade_subj_"):
        subject_id = int(data.split("_")[-1])
        class_id   = context.user_data.get('grade_class_id')
        context.user_data['grade_subject_id'] = subject_id
        await query.edit_message_text(
            "⭐ Baholash — Kriteriya tanlang:",
            reply_markup=kb_grade_criteria(class_id, subject_id)
        )

    elif data.startswith("grade_crit_"):
        parts = data.replace("grade_crit_", "").split("_")
        class_id   = int(parts[0])
        subject_id = int(parts[1])
        criteria   = parts[2]
        # Agar oldin sana tanlangan bo'lsa (grade_history oqimi) — uni ishlatamiz
        today = context.user_data.get('grade_date') or date.today().isoformat()
        context.user_data.update({
            'grade_class_id': class_id, 'grade_subject_id': subject_id,
            'grade_criteria': criteria, 'grade_date': today,
        })
        students = db.get_whitelist_by_class(class_id)
        existing = db.get_grades_for_class(class_id, subject_id, criteria, today)
        grades = {r['student_id']: r['score'] for r in existing}
        context.user_data['grade_scores'] = grades
        await query.edit_message_text(
            f"⭐ *{CRITERIA_LABELS.get(criteria, criteria)}* — O'quvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_grade_students(students, grades, class_id, subject_id, criteria, today)
        )

    elif data.startswith("grade_student_"):
        student_id = int(data.split("_")[-1])
        context.user_data['grade_current_student'] = student_id
        wl = db.get_whitelist_user(student_id)
        await query.edit_message_text(
            f"⭐ *{wl['full_name']}* — Baho tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_grade_score(student_id)
        )

    elif data.startswith("grade_score_"):
        parts    = data.replace("grade_score_", "").split("_")
        student_id = int(parts[0])
        score      = int(parts[1])
        grades = context.user_data.get('grade_scores', {})
        grades[student_id] = score
        context.user_data['grade_scores'] = grades
        # O'quvchilar ro'yxatiga qayt
        class_id   = context.user_data.get('grade_class_id')
        subject_id = context.user_data.get('grade_subject_id')
        criteria   = context.user_data.get('grade_criteria')
        today      = context.user_data.get('grade_date')
        students   = db.get_whitelist_by_class(class_id)
        await query.edit_message_text(
            f"⭐ *{CRITERIA_LABELS.get(criteria, criteria)}* — O'quvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_grade_students(students, grades, class_id, subject_id, criteria, today)
        )

    elif data.startswith("grade_history_"):
        # Eski baholarni o'zgartirish — sana tanlash
        parts      = data.replace("grade_history_", "").split("_")
        class_id   = int(parts[0])
        subject_id = int(parts[1])
        context.user_data['grade_class_id']   = class_id
        context.user_data['grade_subject_id'] = subject_id
        from utils.keyboards import kb_dates
        await query.edit_message_text(
            "📅 Qaysi kungi baholarni o'zgartirmoqchisiz?",
            reply_markup=kb_dates(prefix=f"grade_hist_date_{class_id}_{subject_id}")
        )

    elif data.startswith("grade_hist_date_"):
        # Format: grade_hist_date_{class_id}_{subject_id}_{date}
        rest       = data.replace("grade_hist_date_", "")
        # Oxirgi 10 belgi = sana (YYYY-MM-DD)
        date_str   = rest[-10:]
        ids_part   = rest[:-11]  # "class_id_subject_id"
        parts      = ids_part.split("_")
        class_id   = int(parts[0])
        subject_id = int(parts[1])
        context.user_data['grade_class_id']   = class_id
        context.user_data['grade_subject_id'] = subject_id
        subj = db.get_subject(subject_id)
        cls  = db.get_class(class_id)
        d_fmt = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4]
        await query.edit_message_text(
            f"⭐ *{cls['name']} | {subj['name']} | {d_fmt}*\nKriteriya tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_grade_criteria(class_id, subject_id, show_history=False)
        )
        # Kriteriya bosilganda bu sanani ishlatishi uchun
        context.user_data['grade_date'] = date_str

    elif data in ("grade_save_back", "grade_back_to_list"):
        class_id   = context.user_data.get('grade_class_id')
        subject_id = context.user_data.get('grade_subject_id')
        criteria   = context.user_data.get('grade_criteria')
        today      = context.user_data.get('grade_date')
        grades     = context.user_data.get('grade_scores', {})
        for student_id, score in grades.items():
            db.save_grade(student_id, teacher['id'], subject_id, class_id, criteria, score, today)
        # Kriteriya tanlash menyusiga qaytish
        subj = db.get_subject(subject_id)
        cls  = db.get_class(class_id)
        await query.edit_message_text(
            f"✅ *{CRITERIA_LABELS.get(criteria, criteria)}* — baholar saqlandi!\n\n"
            f"⭐ *{cls['name']} — {subj['name']}*\nBoshqa kriteriyani tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_grade_criteria(class_id, subject_id)
        )


# ══════════════════════════════════════════════════════════
#  REYTING
# ══════════════════════════════════════════════════════════

async def handle_rating_callback(query, context: ContextTypes.DEFAULT_TYPE,
                                  data: str, user_id: int):
    # Ko'p maktabli qo'llab-quvvatlash
    teacher_school_id = context.user_data.get('teacher_school_id')
    if teacher_school_id:
        teacher = db.get_teacher_with_school(user_id, teacher_school_id)
    else:
        teacher = db.get_teacher(user_id)
    
    if not teacher:
        return

    if data.startswith("rating_class_"):
        class_id = int(data.split("_")[-1])
        subjects = db.get_teacher_subjects_for_class(teacher['id'], class_id)
        cls = db.get_class(class_id)
        btns = [
            [InlineKeyboardButton(s['name'], callback_data=f"rating_subj_{class_id}_{s['id']}")]
            for s in subjects
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        await query.edit_message_text(
            f"🏆 Reyting | 🏫 *{cls['name']}* — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif data.startswith("rating_subj_"):
        parts      = data.replace("rating_subj_", "").split("_")
        class_id   = int(parts[0])
        subject_id = int(parts[1])
        ratings    = db.get_class_rating(class_id, subject_id)
        cls     = db.get_class(class_id)
        subject = db.get_subject(subject_id)
        MEDAL = {1: '🥇', 2: '🥈', 3: '🥉'}
        lines = [f"🏆 *{cls['name']} — {subject['name']} reytingi:*\n"]
        for i, r in enumerate(ratings, 1):
            medal = MEDAL.get(i, f"{i}.")
            avg   = r['avg_score'] or 0
            lines.append(f"{medal} {r['full_name']} — *{avg}* ball")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════════════════
#  O'QITUVCHI HAFTALIK JADVAL (tws_*)
# ══════════════════════════════════════════════════════════

async def handle_tws_callback(query, context: ContextTypes.DEFAULT_TYPE,
                               data: str, user_id: int):
    school_id = context.user_data.get('school_id', 1)

    if data in ("tws_start", "tws_back_teachers"):
        teachers = db.get_teachers_by_school(school_id)
        await query.edit_message_text(
            "📅 *Haftalik jadval* — O'qituvchi tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_tws_teachers(teachers)
        )

    elif data == "tws_view":
        slots = db.get_slots(school_id=school_id)
        if not slots:
            await query.edit_message_text("❌ Jadval hali kiritilmagan.")
            return
        
        # Jadval formatini tayyorlash
        from config import WEEKDAY_LABELS
        grouped = {}
        for s in slots:
            grouped.setdefault(s['weekday'], []).append(s)
        
        lines = ["📅 *Haftalik jadval:*\n"]
        for day in sorted(grouped):
            lines.append(f"\n*{WEEKDAY_LABELS[day]}:*")
            for s in grouped[day]:
                # Emoji larni olib tashlash - oddiy format
                lines.append(
                    f"  • {s['teacher_name']} | {s['class_name']} | "
                    f"{s['subject_name']} | {s['start_time']}-{s['end_time']}"
                )
        
        # Yuklab olish tugmalari
        await query.edit_message_text(
            "\n".join(lines), 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Yuklab olish", callback_data="tws_download_menu")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")],
            ])
        )
    
    elif data == "tws_download_menu":
        await query.edit_message_text(
            "📥 *Yuklab olish formati:*\n\nQaysi formatda yuklab olmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data="tws_download_excel")],
                [InlineKeyboardButton("📄 PDF", callback_data="tws_download_pdf")],
                [InlineKeyboardButton("🖼 Rasm (.png)", callback_data="tws_download_image")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="tws_view")],
            ])
        )
    
    elif data == "tws_download_excel":
        await query.edit_message_text("⏳ Excel fayl tayyorlanmoqda...")
        
        slots = db.get_slots(school_id=school_id)
        if not slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_excel
            excel_file = generate_schedule_excel(slots)
            
            # Faylni yuborish
            school = db.get_school(school_id)
            filename = f"Jadval_{school['name'] if school else 'Maktab'}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            await query.message.reply_document(
                document=excel_file,
                filename=filename,
                caption="📊 *O'qituvchilar haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ Excel fayl yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tws_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install openpyxl`",
                parse_mode="Markdown"
            )
    
    elif data == "tws_download_pdf":
        await query.edit_message_text("⏳ PDF fayl tayyorlanmoqda...")
        
        slots = db.get_slots(school_id=school_id)
        if not slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_pdf
            pdf_file = generate_schedule_pdf(slots)
            
            school = db.get_school(school_id)
            filename = f"Jadval_{school['name'] if school else 'Maktab'}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            await query.message.reply_document(
                document=pdf_file,
                filename=filename,
                caption="📄 *O'qituvchilar haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ PDF fayl yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tws_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install reportlab`",
                parse_mode="Markdown"
            )
    
    elif data == "tws_download_image":
        await query.edit_message_text("⏳ Rasm tayyorlanmoqda...")
        
        slots = db.get_slots(school_id=school_id)
        if not slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_image
            image_file = generate_schedule_image(slots)
            
            school = db.get_school(school_id)
            filename = f"Jadval_{school['name'] if school else 'Maktab'}_{datetime.now().strftime('%Y%m%d')}.png"
            
            await query.message.reply_photo(
                photo=image_file,
                caption="🖼 *O'qituvchilar haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ Rasm yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tws_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install Pillow`",
                parse_mode="Markdown"
            )

    elif data.startswith("tws_teacher_"):
        teacher_id = int(data.split("_")[-1])
        context.user_data['tws_teacher_id'] = teacher_id
        slots = db.get_slots(teacher_id=teacher_id)
        if slots:
            await query.edit_message_text(
                "📅 O'qituvchi jadvali:",
                reply_markup=kb_tws_view_slots(slots, teacher_id)
            )
        else:
            classes = db.get_teacher_classes(teacher_id)
            await query.edit_message_text(
                "🏫 Sinf tanlang:",
                reply_markup=kb_tws_classes(classes)
            )

    elif data.startswith("tws_add_slot_"):
        teacher_id = int(data.split("_")[-1])
        context.user_data['tws_teacher_id'] = teacher_id
        classes = db.get_teacher_classes(teacher_id)
        await query.edit_message_text("🏫 Sinf tanlang:", reply_markup=kb_tws_classes(classes))

    elif data.startswith("tws_class_"):
        class_id = int(data.split("_")[-1])
        context.user_data['tws_class_id'] = class_id
        teacher_id = context.user_data.get('tws_teacher_id')
        subjects = db.get_teacher_subjects_for_class(teacher_id, class_id)
        await query.edit_message_text("📚 Fan tanlang:", reply_markup=kb_tws_subjects(subjects))

    elif data.startswith("tws_subj_"):
        subject_id = int(data.split("_")[-1])
        context.user_data['tws_subject_id'] = subject_id
        teacher_id = context.user_data.get('tws_teacher_id')
        class_id   = context.user_data.get('tws_class_id')
        existing_slots = db.get_slots(teacher_id=teacher_id)
        existing_days = {s['weekday'] for s in existing_slots
                         if s['class_id'] == class_id and s['subject_id'] == subject_id}
        context.user_data['tws_existing_days'] = existing_days
        context.user_data['tws_selected_days'] = set()
        await query.edit_message_text(
            "📅 Dars kunlarini tanlang:",
            reply_markup=kb_tws_weekdays(existing_days, set())
        )

    elif data.startswith("tws_day_"):
        day = int(data.split("_")[-1])
        selected = context.user_data.get('tws_selected_days', set())
        selected ^= {day}
        context.user_data['tws_selected_days'] = selected
        existing = context.user_data.get('tws_existing_days', set())
        await query.edit_message_text(
            "📅 Dars kunlarini tanlang:",
            reply_markup=kb_tws_weekdays(existing, selected)
        )

    elif data == "tws_days_confirm":
        context.user_data['waiting_for'] = 'tws_time'
        selected = context.user_data.get('tws_selected_days', set())
        context.user_data['tws_confirm_days'] = selected
        from config import WEEKDAY_LABELS
        days_str = ", ".join(WEEKDAY_LABELS[d] for d in sorted(selected))
        await query.edit_message_text(
            f"✅ Tanlangan kunlar: *{days_str}*\n\n"
            f"Vaqtni kiriting (*HH:MM-HH:MM*):\nMasalan: *08:00-09:30*",
            parse_mode="Markdown"
        )

    elif data.startswith("tws_edit_"):
        slot_id = int(data.split("_")[-1])
        slot    = db.get_slot(slot_id)
        if not slot:
            await query.edit_message_text("❌ Slot topilmadi.")
            return
        context.user_data['tws_edit_slot_id'] = slot_id
        context.user_data['waiting_for']      = 'tws_edit_time'
        from config import WEEKDAY_LABELS
        day = WEEKDAY_LABELS.get(slot['weekday'], str(slot['weekday']))
        await query.edit_message_text(
            f"✏️ *Vaqtni tahrirlash*\n\n"
            f"📅 {day}\n"
            f"🏫 {slot['class_name']} | 📚 {slot['subject_name']}\n"
            f"🕐 Joriy vaqt: *{slot['start_time']}–{slot['end_time']}*\n\n"
            f"Yangi vaqtni kiriting (*HH:MM-HH:MM*):\n"
            f"Masalan: *08:00-09:30*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"tws_teacher_{slot['teacher_id']}")
            ]])
        )

    elif data.startswith("tws_del_"):
        slot_id = int(data.split("_")[-1])
        db.delete_slot(slot_id)
        teacher_id = context.user_data.get('tws_teacher_id')
        slots = db.get_slots(teacher_id=teacher_id)
        if slots:
            await query.edit_message_text(
                "✅ O'chirildi. Joriy jadval:",
                reply_markup=kb_tws_view_slots(slots, teacher_id)
            )
        else:
            await query.edit_message_text("✅ O'chirildi. Jadval bo'sh.")

    elif data == "tws_cancel":
        context.user_data.pop('waiting_for', None)
        await query.edit_message_text("❌ Bekor qilindi.")


# ══════════════════════════════════════════════════════════
#  ADMIN — O'QITUVCHI DAVOMATI (tadm_*)
# ══════════════════════════════════════════════════════════

def _tadm_teachers_data(context) -> list:
    """context dagi tadm_data, tadm_comments → teachers_data ro'yxatini qaytaradi"""
    teacher_ids  = context.user_data.get('tadm_teachers', [])
    tadm_data    = context.user_data.get('tadm_data', {})
    tadm_comments = context.user_data.get('tadm_comments', {})
    teachers_raw = [db.get_teacher_by_id(tid) for tid in teacher_ids]
    return [
        {
            'id':       t['id'],
            'full_name': t['full_name'],
            'status':   tadm_data.get(str(t['id']), 'present'),
            'comment':  tadm_comments.get(str(t['id']), ''),
        }
        for t in teachers_raw if t
    ]


async def _refresh_tadm_keyboard(query, context):
    """Davomat klaviaturasini yangilaydi"""
    date_str      = context.user_data.get('tadm_date', '')
    teachers_data = _tadm_teachers_data(context)
    tadm_data     = context.user_data.get('tadm_data', {})

    # Hamma belgilanganmi?
    all_done = all(
        tadm_data.get(str(t['id']), 'present') != 'present' or True
        for t in teachers_data
    )
    # Faqat saqlangan statuslar bo'yicha "barchasi belgilangan" tekshiruvi
    non_default_count = sum(
        1 for v in tadm_data.values() if v != 'present'
    )
    total = len(teachers_data)
    header_icon = "✅ " if (total > 0 and non_default_count == total) else "📋 "

    await query.edit_message_text(
        f"{header_icon}*O'qituvchilar davomati* | 📅 {date_str}",
        parse_mode="Markdown",
        reply_markup=kb_teacher_attendance(teachers_data)
    )


async def handle_tadm_callback(query, context: ContextTypes.DEFAULT_TYPE,
                                data: str, user_id: int):
    school_id = context.user_data.get('school_id', 1)

    if data == "tadm_cancel":
        for k in ('waiting_for','tadm_data','tadm_comments','tadm_teachers',
                  'tadm_date','tadm_pending_tid','tadm_pending_status'):
            context.user_data.pop(k, None)
        await query.edit_message_text("❌ Bekor qilindi.")

    # ── Sana tanlash ─────────────────────────────────────────────
    elif data.startswith("tadm_date_"):
        date_str = data.replace("tadm_date_", "")
        today_wd = date.fromisoformat(date_str).weekday()
        teachers = db.get_today_teachers(school_id, today_wd)
        if not teachers:
            await query.edit_message_text(
                f"❌ *{date_str}* kunda jadval bo'yicha o'qituvchi yo'q.\n"
                f"_Haftalik jadval kiritilmagan bo'lishi mumkin._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tadm_back_dates")
                ]])
            )
            return
        existing = {r['teacher_id']: r['status'] for r in db.get_teacher_attendance(school_id, date_str)}
        existing_comments = {
            r['teacher_id']: r['comment']
            for r in db.get_teacher_attendance(school_id, date_str)
            if r.get('comment')
        }
        tadm_data = {str(t['id']): existing.get(t['id'], 'present') for t in teachers}
        tadm_comments = {str(t['id']): existing_comments.get(t['id'], '') for t in teachers}

        context.user_data['tadm_date']     = date_str
        context.user_data['tadm_data']     = tadm_data
        context.user_data['tadm_comments'] = tadm_comments
        context.user_data['tadm_teachers'] = [t['id'] for t in teachers]

        teachers_data = [
            {'id': t['id'], 'full_name': t['full_name'],
             'status': tadm_data.get(str(t['id']), 'present'),
             'comment': tadm_comments.get(str(t['id']), '')}
            for t in teachers
        ]
        await query.edit_message_text(
            f"📋 *O'qituvchilar davomati* | 📅 {date_str}\n"
            f"_(✅ Keldi | ❌ Kelmadi | ⏰ Kech keldi | 📝 Sababli)_",
            parse_mode="Markdown",
            reply_markup=kb_teacher_attendance(teachers_data)
        )

    # ── Toggle ────────────────────────────────────────────────────
    elif data.startswith("tadm_toggle_"):
        teacher_id = int(data.split("_")[-1])
        tadm_data  = context.user_data.get('tadm_data', {})
        current    = tadm_data.get(str(teacher_id), 'present')

        # present → absent → late → excused → present
        cycle = {'present': 'absent', 'absent': 'late', 'late': 'excused', 'excused': 'present'}
        new_status = cycle.get(current, 'present')

        if new_status in ('late', 'excused'):
            # Izoh so'rash
            context.user_data['tadm_pending_tid']    = teacher_id
            context.user_data['tadm_pending_status'] = new_status
            context.user_data['waiting_for']         = 'tadm_comment'
            teacher = db.get_teacher_by_id(teacher_id)
            t_name  = teacher['full_name'] if teacher else str(teacher_id)
            status_label = "⏰ Kech keldi" if new_status == 'late' else "📝 Sababli"
            prompt = (
                f"*{t_name}* — {status_label}\n\n"
                + ("⏰ Qancha vaqt kech qoldi? _(masalan: 15 daqiqa)_"
                   if new_status == 'late'
                   else "📝 Sabab nima? _(izoh yozing)_")
            )
            await query.edit_message_text(
                prompt,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏭ Izohlarsiz qoldirish", callback_data=f"tadm_no_comment_{teacher_id}"),
                    InlineKeyboardButton("❌ Bekor", callback_data=f"tadm_undo_{teacher_id}"),
                ]])
            )
        else:
            # Izoh kerak emas — to'g'ridan toggle
            tadm_data[str(teacher_id)] = new_status
            # Agar present ga qaytsa — izohni tozala
            if new_status == 'present':
                context.user_data.get('tadm_comments', {}).pop(str(teacher_id), None)
            context.user_data['tadm_data'] = tadm_data
            await _refresh_tadm_keyboard(query, context)

    # ── Izohlarsiz qoldirish ──────────────────────────────────────
    elif data.startswith("tadm_no_comment_"):
        teacher_id  = int(data.split("_")[-1])
        new_status  = context.user_data.pop('tadm_pending_status', 'late')
        context.user_data.pop('tadm_pending_tid', None)
        context.user_data.pop('waiting_for', None)
        tadm_data   = context.user_data.get('tadm_data', {})
        tadm_data[str(teacher_id)] = new_status
        context.user_data['tadm_data'] = tadm_data
        await _refresh_tadm_keyboard(query, context)

    # ── Statusni avvalgi holatiga qaytarish (sessiya saqlanadi) ──
    elif data.startswith("tadm_undo_"):
        teacher_id = int(data.split("_")[-1])
        # Pending ma'lumotlarni tozalash
        context.user_data.pop('tadm_pending_tid', None)
        context.user_data.pop('tadm_pending_status', None)
        context.user_data.pop('waiting_for', None)
        # Statusni avvalgi holatiga qaytarish (teskari cycle)
        reverse = {'absent': 'present', 'late': 'absent', 'excused': 'late', 'present': 'excused'}
        tadm_data = context.user_data.get('tadm_data', {})
        current = tadm_data.get(str(teacher_id), 'present')
        tadm_data[str(teacher_id)] = reverse.get(current, 'present')
        context.user_data['tadm_data'] = tadm_data
        await _refresh_tadm_keyboard(query, context)

    # ── Saqlash ───────────────────────────────────────────────────
    elif data == "tadm_save":
        date_str      = context.user_data.get('tadm_date')
        tadm_data     = context.user_data.get('tadm_data', {})
        tadm_comments = context.user_data.get('tadm_comments', {})
        if date_str:
            db.save_teacher_attendance(school_id, date_str, tadm_data, tadm_comments)
        for k in ('tadm_data', 'tadm_comments', 'tadm_teachers',
                  'tadm_date', 'tadm_pending_tid', 'tadm_pending_status'):
            context.user_data.pop(k, None)
        await query.edit_message_text(
            "✅ *O'qituvchilar davomati saqlandi!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sanalar", callback_data="tadm_back_dates")
            ]])
        )

    # ── Sanalar menyusiga qaytish ─────────────────────────────────
    elif data == "tadm_back_dates":
        from utils.keyboards import kb_teacher_att_dates
        await query.edit_message_text(
            "📋 *O'qituvchi davomati*\n\nKun tanlang:",
            parse_mode="Markdown",
            reply_markup=kb_teacher_att_dates(school_id=school_id)
        )

    # ── Oylik menyu ───────────────────────────────────────────────
    elif data == "tadm_monthly_menu":
        from datetime import datetime as dt
        now   = dt.now()
        month = now.strftime("%Y-%m")
        prev  = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        await query.edit_message_text(
            "📊 *Oylik davomat — yuklab olish*\n\nOyni tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📅 Joriy oy ({month})", callback_data=f"tadm_export_menu_{month}")],
                [InlineKeyboardButton(f"📅 O'tgan oy ({prev})",  callback_data=f"tadm_export_menu_{prev}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="tadm_back_dates")],
            ])
        )

    # ── Export format tanlash ─────────────────────────────────────
    elif data.startswith("tadm_export_menu_"):
        month = data.replace("tadm_export_menu_", "")
        await query.edit_message_text(
            f"📥 *{month}* — format tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data=f"tadm_xl_{month}")],
                [InlineKeyboardButton("📄 PDF",           callback_data=f"tadm_pdf_{month}")],
                [InlineKeyboardButton("🔙 Orqaga",         callback_data="tadm_monthly_menu")],
            ])
        )

    # ── Excel export ──────────────────────────────────────────────
    elif data.startswith("tadm_xl_"):
        month = data.replace("tadm_xl_", "")
        await query.answer("📊 Excel tayyorlanmoqda...")
        records = db.get_teacher_monthly_attendance(school_id, month)
        if not records:
            await query.edit_message_text(f"❌ *{month}* uchun davomat ma'lumoti yo'q.", parse_mode="Markdown")
            return
        school = db.get_school(school_id)
        school_name = school['name'] if school else "Maktab"
        from utils.attendance_export import generate_attendance_excel
        buf = generate_attendance_excel(records, month, school_name)
        await query.message.reply_document(
            document=buf,
            filename=f"davomat_{school_name}_{month}.xlsx",
            caption=f"📊 *{school_name}* — {month} davomati",
            parse_mode="Markdown"
        )

    # ── PDF export ────────────────────────────────────────────────
    elif data.startswith("tadm_pdf_"):
        month = data.replace("tadm_pdf_", "")
        await query.answer("📄 PDF tayyorlanmoqda...")
        records = db.get_teacher_monthly_attendance(school_id, month)
        if not records:
            await query.edit_message_text(f"❌ *{month}* uchun davomat ma'lumoti yo'q.", parse_mode="Markdown")
            return
        school = db.get_school(school_id)
        school_name = school['name'] if school else "Maktab"
        from utils.attendance_export import generate_attendance_pdf
        buf = generate_attendance_pdf(records, month, school_name)
        await query.message.reply_document(
            document=buf,
            filename=f"davomat_{school_name}_{month}.pdf",
            caption=f"📄 *{school_name}* — {month} davomati",
            parse_mode="Markdown"
        )

    elif data == "tadm_stats":
        # Eski — monthly_menu ga yo'naltirish
        school_id = context.user_data.get('school_id', 1)
        from datetime import datetime as dt
        now   = dt.now()
        month = now.strftime("%Y-%m")
        prev  = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        await query.edit_message_text(
            "📊 *Oylik davomat — yuklab olish*\n\nOyni tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📅 Joriy oy ({month})", callback_data=f"tadm_export_menu_{month}")],
                [InlineKeyboardButton(f"📅 O'tgan oy ({prev})",  callback_data=f"tadm_export_menu_{prev}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="tadm_back_dates")],
            ])
        )


# ══════════════════════════════════════════════════════════
#  O'QITUVCHI UMUMIY: dars, mavzu, topshirmalar
# ══════════════════════════════════════════════════════════

async def handle_teacher_callback(query, context: ContextTypes.DEFAULT_TYPE,
                                   data: str, user_id: int):
    # Ko'p maktabli qo'llab-quvvatlash
    teacher_school_id = context.user_data.get('teacher_school_id')
    if teacher_school_id:
        teacher = db.get_teacher_with_school(user_id, teacher_school_id)
    else:
        teacher = db.get_teacher(user_id)
    
    if not teacher:
        return

    # ── tch_sub_class_{id} — O'quvchi vazifalari: sinf tanlandi ──
    if data.startswith("tch_sub_class_"):
        class_id = int(data.split("_")[-1])
        cls      = db.get_class(class_id)
        context.user_data['sub_view_class_id'] = class_id

        subjects = db.get_teacher_subjects_for_class(teacher['id'], class_id)
        if not subjects:
            await query.edit_message_text(
                f"❌ *{cls['name']}* sinfida sizga fan biriktirilmagan.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_cancel")
                ]])
            )
            return

        btns = [
            [InlineKeyboardButton(s['name'], callback_data=f"tch_sub_subj_{s['id']}")]
            for s in subjects
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        await query.edit_message_text(
            f"📨 *O'quvchi vazifalari | {cls['name']}*\nFan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_sub_subj_{id} — Fan tanlandi → darslar ro'yxati ──────
    elif data.startswith("tch_sub_subj_"):
        subject_id = int(data.split("_")[-1])
        class_id   = context.user_data.get('sub_view_class_id')
        context.user_data['sub_view_subject_id'] = subject_id
        subj = db.get_subject(subject_id)
        cls  = db.get_class(class_id)

        # O'qituvchi bu sinfga yuklagan darslar (homework)
        lessons = db.get_lessons_by_teacher_class_subject(
            teacher['id'], class_id, subject_id, content_type='homework'
        )
        if not lessons:
            await query.edit_message_text(
                f"📭 *{cls['name']} | {subj['name']}*\n\n"
                f"Hali hech qanday uyga vazifa yuklanmagan.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"tch_sub_class_{class_id}")
                ]])
            )
            return

        btns = []
        for l in lessons:
            d          = l['date']
            d_fmt      = d[8:10] + "." + d[5:7] + "." + d[:4]   # 27.02.2026
            subs_count = db.count_submissions(class_id=class_id, subject_id=subject_id, date=d)
            preview    = (l['content'] or "")[:20] + ("…" if l['content'] and len(l['content']) > 20 else "")
            sub_badge  = f"  📨{subs_count}" if subs_count else ""
            label      = f"📅 {d_fmt} | {preview or '📎 fayl'}{sub_badge}"
            btns.append([InlineKeyboardButton(label, callback_data=f"tch_sub_lesson_{l['id']}")])

        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"tch_sub_class_{class_id}")])
        await query.edit_message_text(
            f"📨 *{cls['name']} | {subj['name']}*\nVazifani tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_sub_lesson_{id} — Dars tanlandi → topshirmalar ro'yxati ─
    elif data.startswith("tch_sub_lesson_"):
        lesson_id  = int(data.split("_")[-1])
        lesson     = db.get_lesson(lesson_id)
        class_id   = context.user_data.get('sub_view_class_id')
        subject_id = lesson['subject_id'] if lesson else context.user_data.get('sub_view_subject_id')
        subj       = db.get_subject(subject_id)
        cls        = db.get_class(class_id)
        date_str   = lesson['date'] if lesson else ""
        d_fmt      = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4] if date_str else ""

        subs = db.get_submissions(class_id=class_id, subject_id=subject_id, date=date_str)
        if not subs:
            await query.edit_message_text(
                f"📭 *{cls['name']} | {subj['name']} | {d_fmt}*\n\n"
                f"Hali hech kim topshirmadi.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data=f"tch_sub_subj_{subject_id}")
                ]])
            )
            return

        btns = [
            [InlineKeyboardButton(f"👤 {s['student_name']}", callback_data=f"view_sub_{s['id']}")]
            for s in subs
        ]
        btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"tch_sub_subj_{subject_id}")])
        await query.edit_message_text(
            f"📨 *{cls['name']} | {subj['name']} | {d_fmt}*\n"
            f"*{len(subs)}* ta topshirma:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── view_sub_{id} — Topshirmani ko'rish + baholash ───────────
    elif data.startswith("view_sub_"):
        sub_id = int(data.split("_")[-1])
        with db.conn() as c:
            sub = c.execute("""
                SELECT s.*, w.full_name AS student_name, sub2.name AS subject_name
                FROM submissions s
                JOIN whitelist w   ON s.student_id = w.telegram_id
                JOIN subjects sub2 ON s.subject_id = sub2.id
                WHERE s.id = ?
            """, (sub_id,)).fetchone()
        if not sub:
            await query.edit_message_text("❌ Topshirma topilmadi.")
            return

        from utils.media import send_media
        class_id   = sub['class_id']
        subject_id = sub['subject_id']
        date_str   = sub['date']
        student_id = sub['student_id']
        d_fmt      = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4]

        # ── 1. O'qituvchi vazifasini ko'rsatish ─────────────────
        lessons = db.get_lessons(class_id, subject_id, date_str, "homework")
        await query.edit_message_text(
            f"📨 *{sub['student_name']}* — topshirma\n"
            f"📚 {sub['subject_name']} | 📅 {d_fmt}",
            parse_mode="Markdown"
        )
        if lessons:
            lesson     = lessons[0]
            lesson_files = db.get_lesson_files(lesson['id'])
            hw_cap     = f"📝 O'qituvchi vazifasi | {sub['subject_name']} | {d_fmt}"
            if lesson['content'] or lesson['file_id']:
                await send_media(query.message,
                                 lesson['content'] or "",
                                 lesson['file_id'],
                                 lesson['file_type'] or "", hw_cap)
            for lf in lesson_files:
                await send_media(query.message, "", lf['file_id'], lf['file_type'], hw_cap)

        # ── 2. O'quvchi topshirmasini ko'rsatish ─────────────────
        sub_files  = db.get_submission_files(sub_id)
        late_txt   = " ⚠️ _(kech)_" if sub['is_late'] else ""
        sub_time   = (sub['submitted_at'] or "")[:16]
        sub_cap    = f"📤 {sub['student_name']} topshirmasi | {d_fmt}{late_txt}"
        if sub['content'] or sub['file_id']:
            await send_media(query.message,
                             sub['content'] or "",
                             sub['file_id'],
                             sub['file_type'] or "", sub_cap)
        for sf in sub_files:
            await send_media(query.message, "", sf['file_id'], sf['file_type'], sub_cap)

        # ── 3. Mavjud baho va baholash tugmalari ─────────────────
        grade_row = db.get_submission_grade(student_id, subject_id, date_str)
        score_btns = [
            InlineKeyboardButton(
                f"{'✅ ' if grade_row and grade_row['score'] == s else ''}{s}⭐",
                callback_data=f"vsub_score_{sub_id}_{s}"
            )
            for s in range(1, 6)
        ]
        kb = InlineKeyboardMarkup([
            score_btns,
            [InlineKeyboardButton(
                "🔙 Orqaga",
                callback_data=f"tch_sub_subj_{subject_id}"
            )],
        ])

        grade_info = ""
        if grade_row:
            grade_info = f"\n\n⭐ *Hozirgi baho: {grade_row['score']} ball*"
            if grade_row['comment']:
                grade_info += f"\n💬 _{grade_row['comment']}_"

        from config import utc_to_tashkent
        sub_time_tash = utc_to_tashkent(sub['submitted_at'])

        await query.message.reply_text(
            f"🕐 *Topshirildi:* {sub_time_tash}{late_txt}{grade_info}\n\n"
            f"⬇️ *Baho qo'yish uchun raqamni bosing:*",
            parse_mode="Markdown",
            reply_markup=kb
        )

    # ── vsub_score_{sub_id}_{score} — Ball tanlandi ───────────────
    elif data.startswith("vsub_score_"):
        parts  = data.replace("vsub_score_", "").split("_")
        sub_id = int(parts[0])
        score  = int(parts[1])

        with db.conn() as c:
            sub = c.execute("""
                SELECT s.*, w.full_name AS student_name, sub2.name AS subject_name
                FROM submissions s
                JOIN whitelist w   ON s.student_id = w.telegram_id
                JOIN subjects sub2 ON s.subject_id = sub2.id
                WHERE s.id = ?
            """, (sub_id,)).fetchone()
        if not sub:
            await query.edit_message_text("❌ Topshirma topilmadi.")
            return

        # Context ga saqlash
        context.user_data.update({
            'tch_grade_sub_id':     sub_id,
            'tch_grade_student_id': sub['student_id'],
            'tch_grade_subject_id': sub['subject_id'],
            'tch_grade_class_id':   sub['class_id'],
            'tch_grade_score':      score,
            'tch_grade_date':       sub['date'],
            'waiting_for':          'tch_sub_comment',
        })
        d_fmt = sub['date'][8:10] + "." + sub['date'][5:7] + "." + sub['date'][:4]
        await query.edit_message_text(
            f"⭐ *{score} ball* — {sub['student_name']}\n"
            f"📚 {sub['subject_name']} | 📅 {d_fmt}\n\n"
            f"💬 *Izoh yozing* _(ixtiyoriy)_\n"
            f"_Izoh kerak bo'lmasa — \"O'tkazib yuborish\" tugmasini bosing._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data=f"vsub_skip_cmt_{sub_id}_{score}")
            ]])
        )

    # ── vsub_skip_cmt_{sub_id}_{score} — Izoхsiz saqlash ─────────
    elif data.startswith("vsub_skip_cmt_"):
        parts  = data.replace("vsub_skip_cmt_", "").split("_")
        sub_id = int(parts[0])
        score  = int(parts[1])
        # Context dan ma'lumot olish
        student_id = context.user_data.get('tch_grade_student_id')
        subject_id = context.user_data.get('tch_grade_subject_id')
        class_id   = context.user_data.get('tch_grade_class_id')
        date_str   = context.user_data.get('tch_grade_date')
        for k in ('tch_grade_sub_id','tch_grade_student_id','tch_grade_subject_id',
                  'tch_grade_class_id','tch_grade_score','tch_grade_date','waiting_for'):
            context.user_data.pop(k, None)
        db.save_grade(student_id, teacher['id'], subject_id, class_id,
                      'homework', score, date_str)
        wl   = db.get_whitelist_user(student_id)
        subj = db.get_subject(subject_id)
        await query.edit_message_text(
            f"✅ *Baho saqlandi!*\n"
            f"👤 {wl['full_name'] if wl else student_id}\n"
            f"📚 {subj['name'] if subj else subject_id}\n"
            f"⭐ *{score} ball*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Topshirmalar", callback_data=f"tch_sub_subj_{subject_id}")
            ]])
        )

    # ── vsub_skip_file_{sub_id} — Faylsiz saqlash ────────────────
    elif data.startswith("vsub_skip_file_"):
        sub_id     = int(data.replace("vsub_skip_file_", ""))
        student_id = context.user_data.pop('tch_grade_student_id', None)
        subject_id = context.user_data.pop('tch_grade_subject_id', None)
        class_id   = context.user_data.pop('tch_grade_class_id', None)
        score      = context.user_data.pop('tch_grade_score', None)
        date_str   = context.user_data.pop('tch_grade_date', None)
        comment    = context.user_data.pop('tch_grade_comment', None)
        context.user_data.pop('tch_grade_sub_id', None)
        context.user_data.pop('waiting_for', None)
        db.save_grade(student_id, teacher['id'], subject_id, class_id,
                      'homework', score, date_str, comment=comment)
        wl   = db.get_whitelist_user(student_id)
        subj = db.get_subject(subject_id)
        await query.edit_message_text(
            f"✅ *Baho saqlandi!*\n"
            f"👤 {wl['full_name'] if wl else student_id}\n"
            f"📚 {subj['name'] if subj else subject_id}\n"
            f"⭐ *{score} ball*"
            + (f"\n💬 {comment}" if comment else ""),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Topshirmalar", callback_data=f"tch_sub_subj_{subject_id}")
            ]])
        )

    # ── tch_hw_add — Uyga vazifa qo'shish ───────────────────────
    elif data in ("tch_hw_add", "tch_hw_edit_list"):
        if data == "tch_hw_add":
            context.user_data['teacher_action'] = 'add_homework'
            classes = db.get_teacher_classes(teacher['id'])
            if not classes:
                await query.edit_message_text(
                    "❌ Sizga hali sinf biriktirilmagan.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")
                    ]])
                )
                return
            btns = [
                [InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"tch_class_{c['id']}")]
                for c in classes
            ]
            btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
            await query.edit_message_text(
                "📝 *Uyga vazifa qo'shish* — Sinf tanlang:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )
        else:  # tch_hw_edit_list — o'qituvchi o'zi qo'shgan barcha homeworklar
            from config import WEEKDAY_UZ
            homeworks = db.get_all_teacher_homeworks(teacher['id'])

            if not homeworks:
                await query.edit_message_text(
                    "📭 *Siz hali hech qanday uyga vazifa qo'shmagansiz.*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="tch_hw_add"),
                        InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel"),
                    ]])
                )
                return

            btns = []
            for l in homeworks:
                d = l['date']  # YYYY-MM-DD
                try:
                    from datetime import date as _date
                    wd_en  = _date.fromisoformat(d).strftime("%A")  # 'Monday' etc.
                    wd_uz  = WEEKDAY_UZ.get(wd_en, wd_en)
                except Exception:
                    wd_uz = ""
                d_fmt   = d[8:10] + "." + d[5:7] + "." + d[:4]    # DD.MM.YYYY
                content = (l['content'] or "").strip()
                if not content:
                    content = "📎 fayl"
                label = f"📅 {d_fmt} ({wd_uz}) — {content}"
                # Telegram button uchun max 64 belgi (callback_data cheklovi yo'q, label cheklovi bor)
                btns.append([
                    InlineKeyboardButton(label[:80], callback_data=f"tch_lesson_{l['id']}")
                ])

            btns.append([
                InlineKeyboardButton("➕ Yangi vazifa qo'shish", callback_data="tch_hw_add"),
                InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel"),
            ])
            await query.edit_message_text(
                f"✏️ *Uyga vazifalar ro'yxati* ({len(homeworks)} ta)\n\n"
                f"Tahrirlash uchun bosing:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )

    # ── tch_edit_date_{date} — Sana tanlandi → darslar ro'yxati ─
    elif data.startswith("tch_edit_date_"):
        date_str = data[len("tch_edit_date_"):]
        lessons  = db.get_lessons_by_teacher_date(teacher['id'], date_str)
        d_fmt    = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4]

        if not lessons:
            await query.edit_message_text(
                f"📭 *{d_fmt}* — bu kunda hech qanday dars yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_hw_edit_list")
                ]])
            )
            return

        btns = []
        for l in lessons:
            ctype  = "📝" if l['content_type'] == 'homework' else "📖"
            preview = (l['content'] or "")[:20] + ("…" if l['content'] and len(l['content']) > 20 else "")
            label  = f"{ctype} {l['class_name']} | {l['subject_name']}"
            if preview:
                label += f" — {preview}"
            btns.append([
                InlineKeyboardButton(label[:50], callback_data=f"tch_lesson_{l['id']}"),
            ])
        btns.append([
            InlineKeyboardButton("➕ Yangi vazifa qo'shish", callback_data="tch_hw_add"),
            InlineKeyboardButton("🔙 Orqaga", callback_data="tch_hw_edit_list"),
        ])
        await query.edit_message_text(
            f"✏️ *{d_fmt} — Darslar ro'yxati ({len(lessons)} ta)*\n\nTahrirlash uchun bosing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_lesson_{id} — Bitta darsni boshqarish ────────────────
    elif (data.startswith("tch_lesson_")
          and not data.startswith("tch_lesson_del_")
          and not data.startswith("tch_lesson_edit_")
          and not data.startswith("tch_lesson_deadline_")
          and not data.startswith("tch_lesson_comment_")
          and not data.startswith("tch_lesson_view_files_")
          and not data.startswith("tch_lesson_replace_file_")
          and not data.startswith("tch_lesson_del_deadline_")):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text("❌ Dars topilmadi.")
            return

        ctype  = "📝 Uyga vazifa" if lesson['content_type'] == 'homework' else "📖 Mavzu"
        d      = lesson['date']
        d_fmt  = d[8:10] + "." + d[5:7] + "." + d[:4]
        files  = db.get_lesson_files(lesson_id)
        f_count = len(files) + (1 if lesson['file_id'] else 0)

        from config import WEEKDAY_UZ
        from datetime import date as _date
        try:
            wd_uz = WEEKDAY_UZ.get(_date.fromisoformat(d).strftime("%A"), "")
            d_fmt_full = f"{d_fmt} ({wd_uz})"
        except Exception:
            d_fmt_full = d_fmt

        lines = [f"{ctype}",
                 f"🏫 {lesson['class_name']} | 📚 {lesson['subject_name']} | 📅 {d_fmt_full}",
                 ""]
        if lesson['content']:
            lines.append(f"📝 _{lesson['content']}_")
        if f_count:
            lines.append(f"📎 {f_count} ta fayl")
        if lesson.get('deadline'):
            from config import utc_to_tashkent
            dl_fmt = utc_to_tashkent(lesson['deadline'], "%d.%m.%Y %H:%M")
            lines.append(f"⏰ Deadline: *{dl_fmt}*")
        else:
            lines.append("⏰ Deadline: _belgilanmagan_")
        if lesson.get('comment'):
            lines.append(f"💬 Izoh: _{lesson['comment']}_")

        context.user_data['tch_edit_lesson_id'] = lesson_id
        context.user_data['tch_edit_date']       = lesson['date']

        # Tugmalar
        kb = [
            [InlineKeyboardButton("✏️ Matnni tahrirlash",
                                  callback_data=f"tch_lesson_edit_{lesson_id}")],
        ]
        if f_count:
            kb.append([InlineKeyboardButton("👁 Faylni ko'rish",
                                            callback_data=f"tch_lesson_view_files_{lesson_id}")])
        kb.append([InlineKeyboardButton("🔄 Faylni almashtirish",
                                        callback_data=f"tch_lesson_replace_file_{lesson_id}")])
        if lesson.get('deadline'):
            kb.append([
                InlineKeyboardButton("⏰ Deadlineni o'zgartirish",
                                     callback_data=f"tch_lesson_deadline_{lesson_id}"),
                InlineKeyboardButton("🗑 Deadline o'chirish",
                                     callback_data=f"tch_lesson_del_deadline_{lesson_id}"),
            ])
        else:
            kb.append([InlineKeyboardButton("⏰ Deadline belgilash",
                                            callback_data=f"tch_lesson_deadline_{lesson_id}")])
        if lesson.get('comment'):
            kb.append([InlineKeyboardButton("💬 Izohni tahrirlash",
                                            callback_data=f"tch_lesson_comment_{lesson_id}")])
        else:
            kb.append([InlineKeyboardButton("💬 Izoh qo'shish",
                                            callback_data=f"tch_lesson_comment_{lesson_id}")])
        kb.append([InlineKeyboardButton("🗑 O'chirish",
                                        callback_data=f"tch_lesson_del_{lesson_id}")])
        kb.append([InlineKeyboardButton("🔙 Ro'yxatga qaytish",
                                        callback_data="tch_hw_edit_list")])

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── tch_lesson_view_files_{id} — Fayllarni ko'rish ───────────
    elif data.startswith("tch_lesson_view_files_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text("❌ Dars topilmadi.")
            return
        from utils.media import send_media
        files = db.get_lesson_files(lesson_id)
        sent  = 0
        d_fmt = lesson['date'][8:10] + "." + lesson['date'][5:7] + "." + lesson['date'][:4]
        cap   = f"📎 {lesson['class_name']} | {lesson['subject_name']} | {d_fmt}"
        if lesson['file_id']:
            await send_media(query.message, lesson['content'] or "", lesson['file_id'],
                             lesson['file_type'] or "", cap)
            sent += 1
        for f in files:
            await send_media(query.message, "", f['file_id'], f['file_type'], cap)
            sent += 1
        if not sent:
            await query.answer("❌ Fayl topilmadi", show_alert=True)
        else:
            await query.answer(f"✅ {sent} ta fayl yuborildi")

    # ── tch_lesson_replace_file_{id} — Faylni almashtirish ───────
    elif data.startswith("tch_lesson_replace_file_"):
        lesson_id = int(data.split("_")[-1])
        context.user_data['tch_edit_lesson_id'] = lesson_id
        context.user_data['waiting_for']         = 'tch_replace_file'
        await query.edit_message_text(
            "🔄 *Yangi faylni yuboring*\n\n"
            "_(Rasm, video yoki hujjat — joriy fayl almashtiriladi)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── tch_lesson_deadline_{id} — Deadline qo'shish/o'zgartirish
    elif data.startswith("tch_lesson_deadline_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        context.user_data['tch_edit_lesson_id'] = lesson_id
        context.user_data['waiting_for']         = 'tch_edit_deadline'
        cur = ""
        if lesson and lesson.get('deadline'):
            from config import utc_to_tashkent
            cur = f"\nJoriy deadline: *{utc_to_tashkent(lesson['deadline'], '%d.%m.%Y %H:%M')}*"
        await query.edit_message_text(
            f"⏰ *Deadline belgilash*{cur}\n\n"
            f"Format: *KK.OO.YYYY HH:MM*\n"
            f"Masalan: *28.02.2026 23:59*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── tch_lesson_del_deadline_{id} — Deadlineni o'chirish ──────
    elif data.startswith("tch_lesson_del_deadline_"):
        lesson_id = int(data.split("_")[-1])
        db.update_lesson_deadline(lesson_id, None)
        lesson = db.get_lesson(lesson_id)
        await query.answer("✅ Deadline o'chirildi", show_alert=False)
        # Lesson boshqaruv menyusini qayta ko'rsat
        data = f"tch_lesson_{lesson_id}"
        # Rekursiv chaqiruv o'rniga to'g'ri yo'naltirish
        context.user_data['tch_edit_lesson_id'] = lesson_id
        if lesson:
            d     = lesson['date']
            d_fmt = d[8:10] + "." + d[5:7] + "." + d[:4]
            files = db.get_lesson_files(lesson_id)
            f_count = len(files) + (1 if lesson['file_id'] else 0)
            ctype = "📝 Uyga vazifa" if lesson['content_type'] == 'homework' else "📖 Mavzu"
            lines = [ctype,
                     f"🏫 {lesson['class_name']} | 📚 {lesson['subject_name']} | 📅 {d_fmt}", ""]
            if lesson['content']:
                lines.append(f"📝 _{lesson['content']}_")
            if f_count:
                lines.append(f"📎 {f_count} ta fayl")
            lines.append("⏰ Deadline: _belgilanmagan_")
            if lesson.get('comment'):
                lines.append(f"💬 Izoh: _{lesson['comment']}_")
            kb = [
                [InlineKeyboardButton("✏️ Matnni tahrirlash",
                                      callback_data=f"tch_lesson_edit_{lesson_id}")],
            ]
            if f_count:
                kb.append([InlineKeyboardButton("👁 Faylni ko'rish",
                                                callback_data=f"tch_lesson_view_files_{lesson_id}")])
            kb.append([InlineKeyboardButton("🔄 Faylni almashtirish",
                                            callback_data=f"tch_lesson_replace_file_{lesson_id}")])
            kb.append([InlineKeyboardButton("⏰ Deadline belgilash",
                                            callback_data=f"tch_lesson_deadline_{lesson_id}")])
            if lesson.get('comment'):
                kb.append([InlineKeyboardButton("💬 Izohni tahrirlash",
                                                callback_data=f"tch_lesson_comment_{lesson_id}")])
            else:
                kb.append([InlineKeyboardButton("💬 Izoh qo'shish",
                                                callback_data=f"tch_lesson_comment_{lesson_id}")])
            kb.append([InlineKeyboardButton("🗑 O'chirish",
                                            callback_data=f"tch_lesson_del_{lesson_id}")])
            kb.append([InlineKeyboardButton("🔙 Ro'yxatga qaytish",
                                            callback_data="tch_hw_edit_list")])
            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    # ── tch_lesson_comment_{id} — Izoh qo'shish/tahrirlash ───────
    elif data.startswith("tch_lesson_comment_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        context.user_data['tch_edit_lesson_id'] = lesson_id
        context.user_data['waiting_for']         = 'tch_edit_comment'
        cur = f"\nJoriy izoh: _{lesson['comment']}_" if lesson and lesson.get('comment') else ""
        await query.edit_message_text(
            f"💬 *Izoh qo'shish/tahrirlash*{cur}\n\n"
            f"Izoh matnini yuboring:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── tch_lesson_edit_{id} — Matnni tahrirlash ─────────────────
    elif data.startswith("tch_lesson_edit_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text("❌ Dars topilmadi.")
            return

        context.user_data['tch_edit_lesson_id'] = lesson_id
        context.user_data['waiting_for']         = 'tch_edit_content'
        old_text = lesson['content'] or "_(matn yo'q)_"
        await query.edit_message_text(
            f"✏️ *Matnni tahrirlash*\n\n"
            f"Joriy matn:\n{old_text}\n\n"
            f"Yangi matnni yuboring:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data=f"tch_lesson_{lesson_id}")
            ]])
        )

    # ── tch_lesson_del_ok_{id} — O'chirishni amalga oshirish ─────
    elif data.startswith("tch_lesson_del_ok_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        db.delete_lesson(lesson_id)

        # O'qituvchining qolgan barcha homeworklarini ko'rsat
        from config import WEEKDAY_UZ
        homeworks = db.get_all_teacher_homeworks(teacher['id'])

        if not homeworks:
            await query.edit_message_text(
                "✅ O'chirildi. Boshqa uyga vazifalar yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="tch_hw_add"),
                    InlineKeyboardButton("🔙 Bosh menyu", callback_data="tch_cancel"),
                ]])
            )
            return

        btns = []
        for l in homeworks:
            d = l['date']
            try:
                from datetime import date as _date
                wd_en = _date.fromisoformat(d).strftime("%A")
                wd_uz = WEEKDAY_UZ.get(wd_en, wd_en)
            except Exception:
                wd_uz = ""
            d_fmt   = d[8:10] + "." + d[5:7] + "." + d[:4]
            content = (l['content'] or "").strip() or "📎 fayl"
            label   = f"📅 {d_fmt} ({wd_uz}) — {content}"
            btns.append([InlineKeyboardButton(label[:80], callback_data=f"tch_lesson_{l['id']}")])

        btns.append([
            InlineKeyboardButton("➕ Yangi vazifa qo'shish", callback_data="tch_hw_add"),
            InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel"),
        ])
        await query.edit_message_text(
            f"✅ O'chirildi. ✏️ *Uyga vazifalar ro'yxati* ({len(homeworks)} ta)\n\n"
            f"Tahrirlash uchun bosing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_lesson_del_{id} — O'chirish tasdiqi ──────────────────
    elif data.startswith("tch_lesson_del_") and not data.startswith("tch_lesson_del_ok_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        if not lesson:
            await query.edit_message_text("❌ Dars topilmadi.")
            return

        ctype = "📝 Uyga vazifa" if lesson['content_type'] == 'homework' else "📖 Mavzu"
        await query.edit_message_text(
            f"🗑 *O'chirishni tasdiqlaysizmi?*\n\n"
            f"{ctype} | {lesson['class_name']} | {lesson['subject_name']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, o'chir",  callback_data=f"tch_lesson_del_ok_{lesson_id}")],
                [InlineKeyboardButton("❌ Yo'q",         callback_data=f"tch_lesson_{lesson_id}")],
            ])
        )

    # ── tch_lesson_del_ok_{id} — O'chirishni amalga oshirish ─────
    elif data.startswith("tch_lesson_del_ok_"):
        lesson_id = int(data.split("_")[-1])
        lesson    = db.get_lesson(lesson_id)
        db.delete_lesson(lesson_id)

        # O'qituvchining qolgan barcha homeworklarini ko'rsat
        from config import WEEKDAY_UZ
        homeworks = db.get_all_teacher_homeworks(teacher['id'])

        if not homeworks:
            await query.edit_message_text(
                "✅ O'chirildi. Boshqa uyga vazifalar yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="tch_hw_add"),
                    InlineKeyboardButton("🔙 Bosh menyu", callback_data="tch_cancel"),
                ]])
            )
            return

        btns = []
        for l in homeworks:
            d = l['date']
            try:
                from datetime import date as _date
                wd_en = _date.fromisoformat(d).strftime("%A")
                wd_uz = WEEKDAY_UZ.get(wd_en, wd_en)
            except Exception:
                wd_uz = ""
            d_fmt   = d[8:10] + "." + d[5:7] + "." + d[:4]
            content = (l['content'] or "").strip() or "📎 fayl"
            label   = f"📅 {d_fmt} ({wd_uz}) — {content}"
            btns.append([InlineKeyboardButton(label[:80], callback_data=f"tch_lesson_{l['id']}")])

        btns.append([
            InlineKeyboardButton("➕ Yangi vazifa qo'shish", callback_data="tch_hw_add"),
            InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel"),
        ])
        await query.edit_message_text(
            f"✅ O'chirildi. ✏️ *Uyga vazifalar ro'yxati* ({len(homeworks)} ta)\n\n"
            f"Tahrirlash uchun bosing:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_class_{id} — Mavzu/Dars qo'shish: sinf tanlandi ─────
    elif data.startswith("tch_class_"):
        class_id = int(data.split("_")[-1])
        cls      = db.get_class(class_id)
        context.user_data['teacher_class'] = class_id

        subjects = db.get_teacher_subjects_for_class(teacher['id'], class_id)
        if not subjects:
            await query.edit_message_text(
                f"❌ *{cls['name']}* sinfida sizga fan biriktirilmagan.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_cancel")
                ]])
            )
            return

        btns = [
            [InlineKeyboardButton(s['name'], callback_data=f"tch_subj_{s['id']}")]
            for s in subjects
        ]
        btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
        action = context.user_data.get('teacher_action', '')
        label  = "📖 Mavzu" if action == 'add_topic' else "📝 Uyga vazifa"
        await query.edit_message_text(
            f"{label} | *{cls['name']}* — Fan tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    # ── tch_subj_{id} — Fan tanlandi → jadval bo'yicha sanalar ────
    elif data.startswith("tch_subj_"):
        subject_id = int(data.split("_")[-1])
        context.user_data['teacher_subject'] = subject_id
        class_id   = context.user_data.get('teacher_class')
        action     = context.user_data.get('teacher_action', 'add_homework')
        subj       = db.get_subject(subject_id)
        cls        = db.get_class(class_id)
        label      = "📖 Mavzu" if action == 'add_topic' else "📝 Uyga vazifa"

        # Haftalik jadval asosida dars sanalarini olish
        from utils.keyboards import kb_schedule_dates, kb_dates
        sched_dates = db.get_teacher_class_subject_dates(
            teacher['id'], class_id, subject_id
        )

        if sched_dates:
            await query.edit_message_text(
                f"{label} | 🏫 *{cls['name']}* — 📚 *{subj['name']}*\n\n"
                f"📅 *Dars o'tgan kunlardan birini tanlang:*\n"
                f"_(Faqat jadvalidagi dars kunlari ko'rsatilmoqda)_",
                parse_mode="Markdown",
                reply_markup=kb_schedule_dates(sched_dates, prefix="tch_date")
            )
        else:
            # Jadval kiritilmagan — oddiy sana tanlash
            await query.edit_message_text(
                f"{label} | 🏫 *{cls['name']}* — 📚 *{subj['name']}*\n\n"
                f"📅 *Sana tanlang:*\n"
                f"⚠️ _(Bu sinf uchun haftalik jadval kiritilmagan)_",
                parse_mode="Markdown",
                reply_markup=kb_dates(prefix="tch_date")
            )

    # ── tch_date_{date} — Sana tanlandi → content kiritish ───────
    elif data.startswith("tch_date_"):
        date_str   = data[len("tch_date_"):]
        class_id   = context.user_data.get('teacher_class')
        subject_id = context.user_data.get('teacher_subject')
        action     = context.user_data.get('teacher_action', 'add_homework')
        subj       = db.get_subject(subject_id)
        cls        = db.get_class(class_id)

        # Sanani formatlash: DD.MM.YYYY (HaftaKuni)
        from datetime import date as _date
        from config import WEEKDAY_UZ
        try:
            _d     = _date.fromisoformat(date_str)
            wd_uz  = WEEKDAY_UZ.get(_d.strftime("%A"), "")
            d_fmt  = _d.strftime("%d.%m.%Y") + f" ({wd_uz})"
        except Exception:
            d_fmt  = date_str

        context.user_data['teacher_date']    = date_str
        context.user_data['content_type']    = 'topic' if action == 'add_topic' else 'homework'
        context.user_data['waiting_for']     = 'tch_lesson_content'
        label = "📖 Mavzu matni" if action == 'add_topic' else "📝 Uyga vazifa matni"
        await query.edit_message_text(
            f"{label}\n🏫 *{cls['name']}* | 📚 *{subj['name']}*\n📅 *{d_fmt}*\n\n"
            f"Matn yoki fayl yuboring:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")
            ]])
        )

    # ── tch_att_prev_{teacher_id} — Oldingi oy davomati ──────────
    elif data.startswith("tch_att_prev_"):
        from datetime import date
        current_month = context.user_data.get('tch_att_month', date.today().strftime("%Y-%m"))
        parts = current_month.split("-")
        year, month = int(parts[0]), int(parts[1])
        # Oldingi oy — standart datetime
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
        prev = f"{year}-{month:02d}"
        context.user_data['tch_att_month'] = prev

        records = db.get_teacher_attendance_for_teacher(teacher['id'], prev)
        STATUS_EMOJI = {'present': '✅', 'absent': '❌', 'late': '⏰'}
        STATUS_LABEL = {'present': 'Keldi', 'absent': 'Kelmadi', 'late': 'Kech keldi'}
        lines = [f"📊 *Mening davomatim — {prev}*\n"]
        if records:
            for r in records:
                emoji = STATUS_EMOJI.get(r['status'], '?')
                label = STATUS_LABEL.get(r['status'], r['status'])
                lines.append(f"  {emoji} {r['date']} — {label}")
        else:
            lines.append("❌ Bu oy uchun ma'lumot yo'q.")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Oldingi oy", callback_data=f"tch_att_prev_{teacher['id']}")
            ]])
        )

# ═══════════════════════════════════════════════════════════════
#  O'QITUVCHI JADVAL YUKLAB OLISH
# ═══════════════════════════════════════════════════════════════

async def handle_teacher_schedule_download(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """O'qituvchi o'z jadvalini yuklab olish"""
    from config import db
    from datetime import datetime
    
    # O'qituvchining barcha maktablardagi yozuvlarini olish
    teachers = db.get_teachers_by_telegram_id(query.from_user.id)
    if not teachers:
        await query.edit_message_text("❌ Siz o'qituvchi ro'yxatida yo'qsiz.")
        return
    
    # Barcha maktablar uchun jadvallarni yig'ish
    all_slots = []
    for t in teachers:
        slots = db.get_slots(teacher_id=t['id'])
        all_slots.extend(slots)
    
    if data == "tch_schedule_download_menu":
        await query.edit_message_text(
            "📥 *Yuklab olish formati:*\n\nQaysi formatda yuklab olmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data="tch_schedule_download_excel")],
                [InlineKeyboardButton("📄 PDF", callback_data="tch_schedule_download_pdf")],
                [InlineKeyboardButton("🖼 Rasm (.png)", callback_data="tch_schedule_download_image")],
            ])
        )
    
    elif data == "tch_schedule_download_excel":
        await query.edit_message_text("⏳ Excel fayl tayyorlanmoqda...")
        
        if not all_slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_excel
            excel_file = generate_schedule_excel(all_slots)
            
            filename = f"Jadval_{teachers[0]['full_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            await query.message.reply_document(
                document=excel_file,
                filename=filename,
                caption=f"📊 *{teachers[0]['full_name']} — Haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ Excel fayl yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_schedule_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install openpyxl`",
                parse_mode="Markdown"
            )
    
    elif data == "tch_schedule_download_pdf":
        await query.edit_message_text("⏳ PDF fayl tayyorlanmoqda...")
        
        if not all_slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_pdf
            pdf_file = generate_schedule_pdf(all_slots)
            
            filename = f"Jadval_{teachers[0]['full_name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            await query.message.reply_document(
                document=pdf_file,
                filename=filename,
                caption=f"📄 *{teachers[0]['full_name']} — Haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ PDF fayl yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_schedule_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install reportlab`",
                parse_mode="Markdown"
            )
    
    elif data == "tch_schedule_download_image":
        await query.edit_message_text("⏳ Rasm tayyorlanmoqda...")
        
        if not all_slots:
            await query.edit_message_text("❌ Jadval bo'sh.")
            return
        
        try:
            from utils.schedule_export import generate_schedule_image
            image_file = generate_schedule_image(all_slots)
            
            filename = f"Jadval_{teachers[0]['full_name']}_{datetime.now().strftime('%Y%m%d')}.png"
            
            await query.message.reply_photo(
                photo=image_file,
                caption=f"🖼 *{teachers[0]['full_name']} — Haftalik dars jadvali*",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ Rasm yuborildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="tch_schedule_download_menu")
                ]])
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Kutubxonalar o'rnatilganligini tekshiring:\n"
                f"`pip install Pillow`",
                parse_mode="Markdown"
            )