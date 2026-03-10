"""
callbacks_router.py — Barcha inline callback'larni to'g'ri modulga yo'naltiradi

Faqat routing — logika yo'q.
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import db, logger
from utils.auth import is_super_admin, resolve_school_admin


def _safe_kb_teacher(kb_teacher_fn, multi_school: bool):
    """kb_teacher() multi_school parametrini qabul qilmasa ham xato chiqarmaydi."""
    import inspect
    if "multi_school" in inspect.signature(kb_teacher_fn).parameters:
        return kb_teacher_fn(multi_school=multi_school)
    return kb_teacher_fn()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = update.effective_user.id

    # ── Maktab tanlash (ko'p maktabli o'qituvchilar uchun) ────────
    if data.startswith("select_school_"):
        school_id = int(data.split("_")[-1])
        context.user_data["teacher_school_id"] = school_id

        teacher = db.get_teacher_with_school(user_id, school_id)
        if teacher:
            context.user_data["teacher_id"] = teacher["id"]
            assignments = db.get_teacher_assignments(teacher["id"])
            classes_str = (
                ", ".join(set(a["class_name"] for a in assignments))
                if assignments else "Biriktirilmagan"
            )
            # Ko'p maktabda ishlayaptimi?
            all_teachers = db.get_teachers_by_telegram_id(user_id)
            is_multi = len(all_teachers) > 1

            from utils.keyboards import kb_teacher
            await query.message.delete()
            switch_hint = "\n_Maktabni almashtirish uchun: 🔄 Maktabni almashtirish_" if is_multi else ""
            await query.message.reply_text(
                f"👋 Salom, *{teacher['full_name']}*!\n"
                f"🏫 Maktab: *{teacher['school_name']}*\n"
                f"📚 Sinflar: *{classes_str}*"
                f"{switch_hint}",
                parse_mode="Markdown",
                reply_markup=_safe_kb_teacher(kb_teacher, is_multi)
            )
        return

    # ── Bekor qilish ──────────────────────────────────────────────
    if data in ("cancel", "tch_cancel", "teacher_cancel"):
        for key in ("waiting_for", "tmp_lesson_id", "tmp_content_type",
                    "tmp_submission_id", "att_class_id", "att_subject_id",
                    "attendance_date", "attendance_data"):
            context.user_data.pop(key, None)
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    if data == "sub_done":
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("tmp_submission_id", None)
        await query.edit_message_text("✅ *Vazifa muvaffaqiyatli yuborildi!*", parse_mode="Markdown")
        return

    if data == "tch_files_done":
        for key in ("waiting_for", "tmp_lesson_id", "tmp_content_type"):
            context.user_data.pop(key, None)
        await query.edit_message_text("✅ Saqlandi! Fayllar biriktirildi.")
        return

    if data == "tch_deadline_skip":
        context.user_data['waiting_for'] = 'tch_extra_files'
        from utils.keyboards import kb_teacher_files
        await query.edit_message_text(
            "⏭ Deadline belgilanmadi.\n\n"
            "📎 *Yana fayl qo'shmoqchimisiz?*\n"
            "_(Yuboring yoki ✅ Tayyor tugmasini bosing)_",
            parse_mode="Markdown",
            reply_markup=kb_teacher_files()
        )
        return
    
    if data == "tch_deadline_group_skip":
        group_id = context.user_data.get('tmp_group_id')
        group = db.get_group(group_id)
        
        await query.edit_message_text(
            f"✅ *Tayyor!*\n\n"
            f"👥 Guruh: *{group['group_name']}*\n"
            f"⏰ Deadline: _belgilanmagan_\n\n"
            f"_Barcha sinflarga vazifa yuborildi._",
            parse_mode="Markdown"
        )
        
        # Tozalash
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('tmp_lesson_ids', None)
        context.user_data.pop('tmp_group_id', None)
        context.user_data.pop('teacher_group', None)
        return

    if data == "back_main":
        context.user_data.pop("waiting_for", None)
        await query.edit_message_text("🏠 Asosiy menyu.")
        return

    if data == "back_dates":
        from utils.keyboards import kb_dates
        await query.edit_message_text(
            "📅 *Sanani tanlang:*", parse_mode="Markdown", reply_markup=kb_dates()
        )
        return

    if data == "custom_date":
        from utils.keyboards import kb_cancel
        context.user_data["waiting_for"] = "custom_date"
        await query.edit_message_text(
            "📋 Sana kiriting (*KK/OO/YYYY*):\nMasalan: *20/02/2026*",
            parse_mode="Markdown",
            reply_markup=kb_cancel("back_dates")
        )
        return

    if data == "noop":
        return

    # ── Super Admin ───────────────────────────────────────────────
    if data.startswith("sup_") and is_super_admin(user_id):
        from panels.super.callbacks import handle_super_callback
        await handle_super_callback(query, context, data)
        return

    # ── Admin: Ota-ona label tanlash (inline button) ──────────────
    if data.startswith("adm_parent_lbl_"):
        label       = data[len("adm_parent_lbl_"):]
        parent_tid  = context.user_data.pop('tmp_parent_telegram_id', None)
        student_tid = context.user_data.pop('tmp_parent_student_tid', None)
        context.user_data.pop('waiting_for', None)
        if not parent_tid or not student_tid:
            await query.edit_message_text("❌ Xatolik. Qaytadan boshlang.")
            return
        ok = db.add_student_parent(student_tid, parent_tid, label)
        st = db.get_whitelist_user(student_tid)
        if ok:
            await query.edit_message_text(
                f"✅ *{label}* (`{parent_tid}`) muvaffaqiyatli biriktirildi!\n\n"
                f"👤 O'quvchi: *{st['full_name'] if st else student_tid}*\n\n"
                f"Endi {label} /start buyrug'ini bosib farzandining ma'lumotlarini ko'rishi mumkin.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ Biriktirishda xatolik. Bu ID allaqachon biriktirilgan bo'lishi mumkin."
            )
        return

    # ── Admin ─────────────────────────────────────────────────────
    if data.startswith(("adm_", "adm_student_class_")):
        resolve_school_admin(context, user_id, db)
        from panels.admin.callbacks import handle_admin_callback
        await handle_admin_callback(query, context, data)
        return

    # ── O'qituvchi haftalik jadval ────────────────────────────────
    if data.startswith("tws_"):
        resolve_school_admin(context, user_id, db)
        from handlers.teacher.callbacks import handle_tws_callback
        await handle_tws_callback(query, context, data, user_id)
        return

    # ── O'qituvchi davomati (admin boshqaruvi) ────────────────────
    if data.startswith(("tadm_", "tadm_no_comment_", "tadm_export_", "tadm_xl_", "tadm_pdf_")):
        resolve_school_admin(context, user_id, db)
        from handlers.teacher.callbacks import handle_tadm_callback
        await handle_tadm_callback(query, context, data, user_id)
        return

    # ── Baholash ─────────────────────────────────────────────────
    if data.startswith(("grade_", "grade_hist", "grade_group_", "grade_gcrit_", "grade_gdate_", "grade_date_")):
        from handlers.teacher.callbacks import handle_grading_callback
        await handle_grading_callback(query, context, data, user_id)
        return

    # ── Reyting ───────────────────────────────────────────────────
    if data.startswith("rating_"):
        from handlers.teacher.callbacks import handle_rating_callback
        await handle_rating_callback(query, context, data, user_id)
        return

    # ── O'qituvchi jadval yuklab olish ────────────────────────────
    if data.startswith("tch_schedule_download"):
        from handlers.teacher.callbacks import handle_teacher_schedule_download
        await handle_teacher_schedule_download(query, context, data)
        return

    # ── O'qituvchi: dars, mavzu, topshirmalar, baho ───────────────
    if data.startswith((
        "tch_class_",     "tch_sub_class_",   "tch_sub_subj_",
        "tch_sub_lesson_", "tch_sub_group_",   "tch_subj_",
        "tch_group_",     "tch_group_date_",
        "tch_date_",      "tch_hw_",            "tch_edit_date_",
        "tch_lesson_",    "tch_topic_",         "tch_att_",
        "tch_grade_",     "view_sub_",          "vsub_",
        "tch_lesson_edit_", "tch_lesson_replace_file_", "tch_lesson_deadline_",
        "tch_lesson_del_deadline_", "tch_lesson_comment_", "tch_lesson_del_",
        "tch_lesson_view_files_", "tch_lesson_del_ok_",
    )) or data in ("tch_hw_add", "tch_hw_edit_list"):
        from handlers.teacher.callbacks import handle_teacher_callback
        await handle_teacher_callback(query, context, data, user_id)
        return

    # ── O'quvchi davomati (att_toggle, att_save) ──────────────────
    if data.startswith("att_"):
        from handlers.teacher.callbacks import handle_attendance_callback
        await handle_attendance_callback(query, context, data)
        return

    # ── O'quvchi baholar ──────────────────────────────────────────
    if data.startswith("stu_grades_"):
        from handlers.student.callbacks import handle_student_grades_callback
        await handle_student_grades_callback(query, context, data)
        return

    # ── O'quvchi: darslar, mavzular, topshirish ───────────────────
    if data.startswith((
        "view_hw_",      "view_topic_",    "cls_",           "subj_",
        "date_",         "stu_browse_",    "stu_topic_view_",
        "stu_subj_list_","stu_hw_",        "stu_submit_",    "stu_hw_subj_",
        "hmv_",          "stu_submitl_",
    )) or data in ("stu_browse_topics", "stu_browse_hw", "stu_hw_dates"):
        from handlers.student.callbacks import handle_lesson_callback
        await handle_lesson_callback(query, context, data)
        return

    logger.warning("Unhandled callback: %s from %s", data, user_id)