"""
handlers/start.py — /start buyrug'i
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import db, logger
from utils.auth import is_super_admin
from utils.keyboards import kb_super_admin, kb_school_admin, kb_teacher, kb_student


def _safe_kb_teacher(kb_teacher_fn, multi_school: bool):
    """kb_teacher() multi_school parametrini qabul qilmasa ham xato chiqarmaydi."""
    import inspect
    if "multi_school" in inspect.signature(kb_teacher_fn).parameters:
        return kb_teacher_fn(multi_school=multi_school)
    return kb_teacher_fn()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "")

    # 1. Super Admin
    if is_super_admin(user.id):
        context.user_data.pop("school_id", None)
        schools = db.get_schools()
        await update.message.reply_text(
            f"👋 Salom, *{user.first_name}*!\n"
            f"🔑 *Super Admin* sifatida kirgansiz\n"
            f"🏫 Maktablar: *{len(schools)}* ta",
            parse_mode="Markdown",
            reply_markup=kb_super_admin()
        )
        return

    # 2. Maktab Admin
    sa = db.get_school_admin(user.id)
    if sa:
        context.user_data["school_id"] = sa["school_id"]
        stats = db.get_school_stats(sa["school_id"])
        await update.message.reply_text(
            f"👋 Salom, *{sa['full_name']}*!\n"
            f"🏫 Maktab: *{sa['school_name']}*\n"
            f"👥 O'quvchilar: *{stats['students']}* | "
            f"👨‍🏫 O'qituvchilar: *{stats['teachers']}*",
            parse_mode="Markdown",
            reply_markup=kb_school_admin()
        )
        return

    # 3. O'qituvchi (ko'p maktabli qo'llab-quvvatlash)
    teachers = db.get_teachers_by_telegram_id(user.id)
    if teachers:
        is_multi = len(teachers) > 1

        # Agar faqat 1 ta maktab bo'lsa
        if not is_multi:
            teacher = teachers[0]
            context.user_data["teacher_school_id"] = teacher["school_id"]
            context.user_data["teacher_id"] = teacher["id"]

            assignments = db.get_teacher_assignments(teacher["id"])
            classes_str = (
                ", ".join(set(a["class_name"] for a in assignments))
                if assignments else "Biriktirilmagan"
            )
            await update.message.reply_text(
                f"👋 Salom, *{teacher['full_name']}*!\nSiz o'qituvchi sifatida tizimga kirdingiz\n"
                f"🏫 Maktab: *{teacher['school_name']}*\n"
                f"📚 Sinflar: *{classes_str}*",
                parse_mode="Markdown",
                reply_markup=_safe_kb_teacher(kb_teacher, False)
            )
            return

        # 2+ maktab — avvalgi tanlangan maktab bormi?
        saved_school_id = context.user_data.get("teacher_school_id")
        if saved_school_id:
            teacher = next(
                (t for t in teachers if t["school_id"] == saved_school_id), None
            )
            if teacher:
                context.user_data["teacher_id"] = teacher["id"]
                assignments = db.get_teacher_assignments(teacher["id"])
                classes_str = (
                    ", ".join(set(a["class_name"] for a in assignments))
                    if assignments else "Biriktirilmagan"
                )
                await update.message.reply_text(
                    f"👋 Salom, *{teacher['full_name']}*!\n"
                    f"🏫 Maktab: *{teacher['school_name']}*\n"
                    f"📚 Sinflar: *{classes_str}*\n"
                    f"_Maktabni almashtirish uchun: 🔄 Maktabni almashtirish_",
                    parse_mode="Markdown",
                    reply_markup=_safe_kb_teacher(kb_teacher, True)
                )
                return

        # Yangi sessiya — maktab tanlash ekranini ko'rsat
        buttons = [
            [InlineKeyboardButton(
                f"🏫 {t['school_name']}",
                callback_data=f"select_school_{t['school_id']}"
            )]
            for t in teachers
        ]
        await update.message.reply_text(
            f"👋 Salom, *{teachers[0]['full_name']}*!\n\n"
            f"Siz bir nechta maktabda ishlaysiz.\n"
            f"Maktabni tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    # Agar faol o'qituvchi topilmasa, arxivlanganligini tekshirish
    archived_teacher = db.get_teacher_any(user.id)
    if archived_teacher and archived_teacher.get('is_active') == 0:
        await update.message.reply_text(
            f"📦 Salom, *{archived_teacher['full_name']}*!\n\n"
            f"⚠️ *Sizning o'qituvchi akkauntingiz arxivlangan.*\n\n"
            f"Bu degani:\n"
            f"   • Siz hozirda faol o'qituvchilar ro'yxatida yo'qsiz\n"
            f"   • Sizning barcha darslar va uyga vazifalar ma'lumotlaringiz saqlanib qolgan\n"
            f"   • Yangi darslar yarata olmaysiz\n\n"
            f"📞 *Qayta faollashtirish uchun:*\n"
            f"👉 Maktab adminingizga murojaat qiling\n\n"
            f"🏫 Maktab: *{archived_teacher.get('school_name', 'N/A')}*\n"
            f"📋 Telegram ID: `{user.id}`",
            parse_mode="Markdown"
        )
        return

    # 4. O'quvchi
    wl = db.get_whitelist_user(user.id)
    if wl:
        # Arxivlangan o'quvchini tekshirish
        if wl.get('is_active') == 0:
            await update.message.reply_text(
                f"📦 Salom, *{wl['full_name']}*!\n\n"
                f"⚠️ *Sizning akkauntingiz arxivlangan.*\n\n"
                f"Bu degani:\n"
                f"   • Siz hozirda faol o'quvchi ro'yxatida yo'qsiz\n"
                f"   • Davomat va baholaringiz saqlanib qolgan\n"
                f"   • Yangi topshiriqlar ko'rinmaydi\n\n"
                f"📞 *Qayta faollashtirish uchun:*\n"
                f"👉 Maktab adminingizga murojaat qiling\n\n"
                f"📋 Telegram ID: `{user.id}`",
                parse_mode="Markdown"
            )
            return
        
        # Faol o'quvchi
        await update.message.reply_text(
    f"👋 Salom, *{wl['full_name']}*!\n"
    f"🏫 *{wl['school_name']}* ning rasmiy ta'lim botiga xush kelibsiz!\n\n"
    f"📌 *Sizning ma'lumotlaringiz:*\n"
    f"   • Maktab: *{wl['school_name']}*\n"
    f"   • Sinf: *{wl['class_name']}*\n\n"
    f"📚 *Bu bot orqali siz:*\n"
    f"   ✅ Uyga vazifalar va mavzularni ko'rishingiz\n"
    f"   ✅ Davomat va baholaringizni kuzatishingiz\n"
    f"   ✅ Dars jadvali bilan tanishishingiz mumkin\n\n"
    f"⚠️ Ma'lumotlarda xatolik bo'lsa:\n"
    f"👉 @InnovateIT\_School\_Manager ga murojaat qiling",
    parse_mode="Markdown",
    reply_markup=kb_student()
)
        return

    # 5. Noma'lum
    await update.message.reply_text(
        "🚫 *Kechirasiz, siz ro'yxatda yo'qsiz!*\n\n"
        "Bu bot faqat ruxsat berilgan foydalanuvchilar uchun.\n"
        "Maktab adminingizdan ruxsat so'rang.\n\n"
        f"📋 Sizning Telegram ID: `{user.id}`",
        parse_mode="Markdown"
    )