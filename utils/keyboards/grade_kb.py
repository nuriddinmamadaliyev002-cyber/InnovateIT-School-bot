"""
utils/keyboards/grade_kb.py — Baholash va jadval klaviaturalari
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import CRITERIA_LABELS, SCORE_EMOJI, WEEKDAY_LABELS


# ── Baholash ─────────────────────────────────────────────────────

def kb_grade_dates(dates: list, prefix: str, back_data: str = "tch_cancel") -> InlineKeyboardMarkup:
    """
    O'qituvchi dars o'tadigan sanalar uchun keyboard.
    dates: [{'date': 'YYYY-MM-DD', 'weekday': int, 'start_time': str}, ...]
    """
    import datetime
    weekday_uz = {0: "Du", 1: "Se", 2: "Ch", 3: "Pa", 4: "Ju", 5: "Sha", 6: "Ya"}
    btns = []
    today = datetime.date.today().isoformat()
    for d in dates:
        date_str  = d['date']
        wd        = weekday_uz.get(d.get('weekday', 0), '')
        time_info = f" {d['start_time']}" if d.get('start_time') else ""
        d_fmt     = date_str[8:10] + "." + date_str[5:7] + "." + date_str[:4]
        label     = f"{'📅 Bugun' if date_str == today else '🗓 ' + wd}, {d_fmt}{time_info}"
        btns.append([InlineKeyboardButton(label, callback_data=f"{prefix}{date_str}")])
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data=back_data)])
    return InlineKeyboardMarkup(btns)


def kb_grade_criteria(class_id: int, subject_id: int,
                       show_history: bool = True) -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(label,
                              callback_data=f"grade_crit_{class_id}_{subject_id}_{key}")]
        for key, label in CRITERIA_LABELS.items()
    ]
    if show_history:
        btns.append([InlineKeyboardButton(
            "📅 O'tgan kunlar (tarix)",
            callback_data=f"grade_history_{class_id}_{subject_id}"
        )])
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


def kb_grade_criteria_group(group_id: int, subject_id: int,
                             show_history: bool = True) -> InlineKeyboardMarkup:
    """Guruh baholash uchun kriteriya klaviaturasi."""
    btns = [
        [InlineKeyboardButton(label,
                              callback_data=f"grade_gcrit_{group_id}_{subject_id}_{key}")]
        for key, label in CRITERIA_LABELS.items()
    ]
    if show_history:
        btns.append([InlineKeyboardButton(
            "📅 O'tgan kunlar (tarix)",
            callback_data=f"grade_ghistory_{group_id}_{subject_id}"
        )])
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


def kb_grade_students(students: list, grades: dict,
                      class_id: int, subject_id: int,
                      criteria: str, date_str: str) -> InlineKeyboardMarkup:
    btns = []
    for s in students:
        score = grades.get(s["telegram_id"])
        score_str = f" — {SCORE_EMOJI.get(score, str(score))}" if score else " — ✏️"
        btns.append([InlineKeyboardButton(
            f"{s['full_name']}{score_str}",
            callback_data=f"grade_student_{s['telegram_id']}"
        )])
    btns.append([InlineKeyboardButton("💾 Saqlash va orqaga", callback_data="grade_save_back")])
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


def kb_grade_students_group(students: list, grades: dict,
                             group_id: int, subject_id: int,
                             criteria: str, date_str: str) -> InlineKeyboardMarkup:
    """Guruh o'quvchilari uchun baholash klaviaturasi."""
    btns = []
    for s in students:
        score     = grades.get(s["telegram_id"])
        score_str = f" — {SCORE_EMOJI.get(score, str(score))}" if score else " — ✏️"
        # Sinf nomi qo'shamiz (guruhda bir necha sinf bo'lishi mumkin)
        class_label = f" [{s.get('class_name', '')}]" if s.get('class_name') else ""
        btns.append([InlineKeyboardButton(
            f"{s['full_name']}{class_label}{score_str}",
            callback_data=f"grade_student_{s['telegram_id']}"
        )])
    btns.append([InlineKeyboardButton("💾 Saqlash va orqaga", callback_data="grade_save_back")])
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tch_cancel")])
    return InlineKeyboardMarkup(btns)


def kb_grade_score(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(SCORE_EMOJI[i],
                              callback_data=f"grade_score_{student_id}_{i}")
         for i in range(1, 6)],
        [InlineKeyboardButton("🔙 Orqaga (saqlash)", callback_data="grade_back_to_list")],
    ])


# ── O'qituvchi haftalik jadval ────────────────────────────────────

def kb_tws_teachers(teachers: list) -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(f"👨‍🏫 {t['full_name']}", callback_data=f"tws_teacher_{t['id']}")]
        for t in teachers
    ]
    btns.append([InlineKeyboardButton("❌ Bekor", callback_data="tws_cancel")])
    return InlineKeyboardMarkup(btns)


def kb_tws_classes(classes: list, groups: list = None) -> InlineKeyboardMarkup:
    """
    Yakka sinflar VA guruhlarni ko'rsatadi.
    groups: [{'id': .., 'group_name': .., 'class_count': .., 'subject_name': ..}, ...]
    """
    btns = []

    # Yakka sinflar bo'limi
    if classes:
        btns.append([InlineKeyboardButton("📚 Yakka sinflar ⬇", callback_data="noop")])
        for c in classes:
            btns.append([InlineKeyboardButton(f"🏫 {c['name']}", callback_data=f"tws_class_{c['id']}")])

    # Guruhlar bo'limi
    if groups:
        btns.append([InlineKeyboardButton("👥 Sinf guruhlari ⬇", callback_data="noop")])
        for g in groups:
            btns.append([InlineKeyboardButton(
                f"👥 {g['group_name']} ({g['class_count']} ta sinf)",
                callback_data=f"tws_group_{g['id']}"
            )])

    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="tws_back_teachers")])
    return InlineKeyboardMarkup(btns)


def kb_tws_subjects(subjects: list) -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton(f"📚 {s['name']}", callback_data=f"tws_subj_{s['id']}")]
        for s in subjects
    ]
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="tws_back_classes")])
    return InlineKeyboardMarkup(btns)


def kb_tws_weekdays(existing: set = None, selected: set = None) -> InlineKeyboardMarkup:
    existing = existing or set()
    selected = selected or set()
    btns = []
    for day, label in WEEKDAY_LABELS.items():
        if day in selected:    emoji = "✅"
        elif day in existing:  emoji = "☑️"
        else:                  emoji = "⬜"
        btns.append([InlineKeyboardButton(
            f"{emoji} {label}", callback_data=f"tws_day_{day}"
        )])
    if selected:
        btns.append([InlineKeyboardButton(
            f"✅ Tasdiqlash ({len(selected)} kun)", callback_data="tws_days_confirm"
        )])
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="tws_back_subjects")])
    return InlineKeyboardMarkup(btns)


def kb_tws_view_slots(slots: list, teacher_id: int) -> InlineKeyboardMarkup:
    btns = []
    for slot in slots:
        day   = WEEKDAY_LABELS.get(slot["weekday"], str(slot["weekday"]))
        label = f"{day} | {slot['class_name']} | {slot['subject_name']} {slot['start_time']}-{slot['end_time']}"
        btns.append([
            # Slotga bosish — vaqtni tahrirlash
            InlineKeyboardButton(f"✏️ {label[:35]}", callback_data=f"tws_edit_{slot['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"tws_del_{slot['id']}"),
        ])
    btns.append([
        InlineKeyboardButton("➕ Slot qo'shish", callback_data=f"tws_add_slot_{teacher_id}"),
        InlineKeyboardButton("🔙 Orqaga",        callback_data="tws_back_teachers"),
    ])
    return InlineKeyboardMarkup(btns)