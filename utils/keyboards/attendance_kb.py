"""
utils/keyboards/attendance_kb.py — Davomat klaviaturalari
"""
from datetime import date, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import ATTENDANCE_EMOJI, WEEKDAY_UZ


def kb_student_attendance(students: list, att_data: dict,
                           comments: dict = None) -> InlineKeyboardMarkup:
    """
    students:  whitelist rows
    att_data:  { str(telegram_id): status }
    comments:  { str(telegram_id): comment_text }
    """
    comments = comments or {}
    btns = []
    for s in students:
        sid    = str(s["telegram_id"])
        status = att_data.get(sid, "present")
        emoji  = ATTENDANCE_EMOJI.get(status, "✅")
        cmt    = comments.get(sid, "")
        cmt_icon = " 💬" if cmt else ""
        btns.append([InlineKeyboardButton(
            f"{emoji} {s['full_name'][:28]}{cmt_icon}",
            callback_data=f"att_toggle_{s['telegram_id']}"
        )])
    btns.append([
        InlineKeyboardButton("💾 Saqlash", callback_data="att_save"),
        InlineKeyboardButton("❌ Bekor",   callback_data="teacher_cancel"),
    ])
    return InlineKeyboardMarkup(btns)


def kb_teacher_attendance(teachers_data: list, is_saved: bool = False, editing_id: int = None) -> InlineKeyboardMarkup:
    """
    teachers_data: [{'id', 'full_name', 'status', 'comment'(optional), 'hours'(optional)}, ...]
    is_saved: True bo'lsa, barcha o'qituvchilar saqlangan
    editing_id: Tahrir qilinayotgan o'qituvchi ID'si
    - Har bir o'qituvchi qatorida tahrir/saqlash tugmasi
    - Soat faqat 'present' yoki 'late' statusida ko'rinadi
    """
    btns = []
    for t in teachers_data:
        status  = t.get("status", "present")
        emoji   = ATTENDANCE_EMOJI.get(status, "✅")
        comment = t.get("comment", "") or ""
        hours   = t.get("hours")
        tid     = t['id']

        # Qo'shimcha info: izoh va soat
        extra = ""
        if comment:
            short = comment[:15] + "…" if len(comment) > 15 else comment
            extra += f" 💬{short}"
        # Soat faqat "Keldi" yoki "Kech keldi" da ko'rinsin
        if hours and status in ('present', 'late'):
            extra += f" ⏱{hours}s"  # 's' = 'soat' degan ma'no

        name = t['full_name'][:22]
        
        # Agar shu o'qituvchi tahrir qilinayotgan bo'lsa
        if editing_id == tid:
            # Ism + Saqlash tugmasi
            btns.append([
                InlineKeyboardButton(f"{emoji} {name}{extra}", callback_data=f"tadm_toggle_{tid}"),
                InlineKeyboardButton("💾", callback_data=f"tadm_save_one_{tid}")
            ])
        else:
            # Ism + Tahrir tugmasi
            btns.append([
                InlineKeyboardButton(f"{emoji} {name}{extra}", callback_data=f"tadm_toggle_{tid}"),
                InlineKeyboardButton("✏️", callback_data=f"tadm_edit_one_{tid}")
            ])

    btns.append([
        InlineKeyboardButton("🔙 Orqaga", callback_data="tadm_back_dates"),
    ])
    return InlineKeyboardMarkup(btns)


def kb_teacher_att_dates(school_id: int = None) -> InlineKeyboardMarkup:
    """
    O'qituvchi davomati uchun sana tanlash.
    - Yakshanba kunlari ko'rsatilmaydi
    - Har sanada ✅ (belgilangan) yoki ☐ (belgilanmagan) ko'rsatiladi
    """
    today = date.today()
    btns  = []
    shown = 0
    i     = 0

    while shown < 7 and i < 14:
        d = today - timedelta(days=i)
        i += 1

        # Yakshanba (weekday=6) ni o'tkazib yuboramiz
        if d.weekday() == 6:
            continue

        # Belgilanganlik holati
        if school_id:
            try:
                from config import db
                marked, total = db.get_teacher_attendance_status_for_date(school_id, d.isoformat())
                if total > 0 and marked >= total:
                    check = "✅ "
                else:
                    check = "☐ "
            except Exception:
                check = "☐ "
        else:
            check = ""

        # Label
        if shown == 0:
            label = f"{check}📅 Bugun"
        elif shown == 1:
            label = f"{check}📅 Kecha"
        else:
            en = d.strftime("%A")
            short = {
                "Monday": "Du", "Tuesday": "Se", "Wednesday": "Cho",
                "Thursday": "Pa", "Friday": "Ju", "Saturday": "Sh",
            }
            label = f"{check}{d.strftime('%d.%m')} ({short.get(en, en)})"

        btns.append([InlineKeyboardButton(label, callback_data=f"tadm_date_{d.isoformat()}")])
        shown += 1

    btns.append([InlineKeyboardButton("📊 Oylik statistika / Yuklab olish", callback_data="tadm_monthly_menu")])
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
    return InlineKeyboardMarkup(btns)


def kb_att_dates_for_class(class_id: int) -> InlineKeyboardMarkup:
    """
    Admin — O'quvchilar davomati uchun sana tanlash.
    - Yakshanba kunlari ko'rsatilmaydi
    - Agar shu kunda davomat saqlangan bo'lsa ✅ ko'rsatiladi
    - Oxirgi 7 ish kunini ko'rsatadi (max 14 kun orqaga qaraydi)
    """
    from config import db
    today = date.today()
    btns  = []
    shown = 0
    i     = 0

    while shown < 7 and i < 14:
        d = today - timedelta(days=i)
        i += 1

        # Yakshanba (weekday=6) ni o'tkazib yuboramiz
        if d.weekday() == 6:
            continue

        # Davomat saqlangan kunni tekshiramiz (subject_id=0 — admin rejimi)
        try:
            records = db.get_attendance(class_id, 0, d.isoformat())
            check = "✅ " if records else ""
        except Exception:
            check = ""

        # Label
        if shown == 0:
            label = f"{check}📅 Bugun"
        elif shown == 1:
            label = f"{check}📅 Kecha"
        else:
            en = d.strftime("%A")
            short = {
                "Monday": "Du", "Tuesday": "Se", "Wednesday": "Cho",
                "Thursday": "Pa", "Friday": "Ju", "Saturday": "Sh",
            }
            label = f"{check}{d.strftime('%d.%m')} ({short.get(en, en)})"

        btns.append([InlineKeyboardButton(
            label,
            callback_data=f"adm_att_date_{class_id}_{d.isoformat()}"
        )])
        shown += 1

    btns.append([InlineKeyboardButton("📅 Boshqa sana", callback_data=f"adm_att_custom_{class_id}")])
    btns.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_main_menu")])
    return InlineKeyboardMarkup(btns)