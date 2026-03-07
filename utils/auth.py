"""
utils/auth.py — Rol tekshiruv funksiyalari
"""
from config import ADMIN_IDS


def is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def get_school_id(context, user_id: int, db) -> int:
    """
    school_id olish tartibi:
    1. context.user_data da saqlangan bo'lsa
    2. Maktab admin bo'lsa — bazadan
    3. Default → 1
    """
    sid = context.user_data.get("school_id")
    if sid:
        return sid
    sa = db.get_school_admin(user_id)
    if sa:
        context.user_data["school_id"] = sa["school_id"]
        return sa["school_id"]
    return 1


def resolve_school_admin(context, user_id: int, db):
    """
    Super admin yoki maktab admin uchun school_id ni context ga yozadi.
    Qaytaradi: school_id yoki None
    """
    if is_super_admin(user_id):
        return context.user_data.get("school_id")
    sa = db.get_school_admin(user_id)
    if sa:
        context.user_data["school_id"] = sa["school_id"]
        return sa["school_id"]
    return None
