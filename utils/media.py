"""
utils/media.py — Fayl yuborish va olish yordamchilari
"""
from telegram import Message
from config import FILE_TYPE_EMOJI


def extract_file(message: Message) -> tuple:
    """
    Xabardan fayl ma'lumotlarini olish.
    Qaytaradi: (file_id, file_type, caption)
    """
    caption = message.caption or ""
    if message.photo:
        return message.photo[-1].file_id, "photo", caption
    if message.video:
        return message.video.file_id, "video", caption
    if message.document:
        return message.document.file_id, "document", caption
    return None, None, message.text or ""


def _build_caption(content: str, file_type: str, caption: str) -> str:
    emoji = FILE_TYPE_EMOJI.get(file_type, "")
    if content:
        return f"{caption}\n\n{emoji} {content}" if caption else f"{emoji} {content}"
    return f"{emoji} {caption}" if caption else ""


async def send_media(message: Message, content: str, file_id: str,
                     file_type: str, caption: str = ""):
    """Reply sifatida media yoki matn yuborish"""
    text = _build_caption(content, file_type, caption)
    if file_id and file_type == "photo":
        await message.reply_photo(file_id, caption=text, parse_mode="Markdown")
    elif file_id and file_type == "video":
        await message.reply_video(file_id, caption=text, parse_mode="Markdown")
    elif file_id and file_type == "document":
        await message.reply_document(file_id, caption=text, parse_mode="Markdown")
    elif text:
        await message.reply_text(text, parse_mode="Markdown")


async def edit_or_send_media(query, content: str, file_id: str,
                              file_type: str, caption: str = ""):
    """Callback ichida media yoki matn yuborish"""
    text = _build_caption(content, file_type, caption)
    if file_id and file_type == "photo":
        await query.message.reply_photo(file_id, caption=text, parse_mode="Markdown")
    elif file_id and file_type == "video":
        await query.message.reply_video(file_id, caption=text, parse_mode="Markdown")
    elif file_id and file_type == "document":
        await query.message.reply_document(file_id, caption=text, parse_mode="Markdown")
    else:
        await query.edit_message_text(text, parse_mode="Markdown")