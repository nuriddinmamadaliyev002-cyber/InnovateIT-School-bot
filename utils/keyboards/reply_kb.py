"""
utils/keyboards/reply_kb.py — Asosiy Reply klaviaturalar (rol bo'yicha)
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def kb_super_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("🏫 Maktablar"),       KeyboardButton("👨‍💼 Maktab adminlari")],
        [KeyboardButton("📊 Umumiy statistika")],
    ], resize_keyboard=True)


def kb_school_admin(is_super: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        # 1-qator: Asosiy strukturaviy bo'limlar
        [KeyboardButton("🏫 Sinflar"),             KeyboardButton("📚 Fanlar")],
        # 2-qator: Odamlar
        [KeyboardButton("👥 O'quvchilar"),         KeyboardButton("👨‍🏫 O'qituvchilar")],
        # 3-qator: Jadvallar
        [KeyboardButton("🗓 Sinf dars jadvali"),   KeyboardButton("📅 O'qituvchi jadvali")],
        # 4-qator: Davomat
        [KeyboardButton("📋 O'quvchi davomati"),   KeyboardButton("📋 O'qituvchi davomati")],
        # 5-qator: Statistika
        [KeyboardButton("📊 Statistika")],
    ]
    if is_super:
        rows.append([KeyboardButton("🔙 Super Admin paneli")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_teacher(multi_school: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("📖 Mavzu"),               KeyboardButton("📨 O'quvchi vazifalari")],
        [KeyboardButton("📝 Uyga vazifa"),         KeyboardButton("🗓 Dars jadvali")],
        [KeyboardButton("⭐ O'quvchilarni baholash"), KeyboardButton("🏆 Reyting")],
        [KeyboardButton("📊 Mening davomatim")],
    ]
    if multi_school:
        rows.append([KeyboardButton("🔄 Maktabni almashtirish")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def kb_student() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📚 Bugungi vazifalar"), KeyboardButton("📖 Bugungi mavzular")],
        [KeyboardButton("📋 Hamma mavzu va vazifalar"), KeyboardButton("🗓 Dars jadvali")],
        [KeyboardButton("📊 Mening davomatim")],
        [KeyboardButton("⭐ Baholarim"),          KeyboardButton("🏆 Mening reytingim")],
    ], resize_keyboard=True)