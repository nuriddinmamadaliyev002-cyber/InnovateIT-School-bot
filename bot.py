"""
bot.py — Entry point
"""
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)
from telegram.request import HTTPXRequest

from config import BOT_TOKEN, PROXY_URL, logger
from telegram.error import NetworkError, TimedOut
from handlers.start import cmd_start
from handlers.message_router import handle_message
from callbacks_router import handle_callback


def main():
    # Timeout va connection pool sozlamalari
    request_kwargs = dict(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        connection_pool_size=8,
    )
    if PROXY_URL:
        request_kwargs["proxy"] = PROXY_URL
        logger.info(f"🔌 Proxy ishlatilmoqda: {PROXY_URL}")

    request = HTTPXRequest(**request_kwargs)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO,
        handle_message
    ))

    async def error_handler(update, context):
        err = context.error
        # Tarmoq xatolari — faqat logga yozamiz, foydalanuvchiga xabar yo'q
        if isinstance(err, (NetworkError, TimedOut)):
            logger.warning("Tarmoq xatosi: %s", err)
            return
        # Boshqa xatoliklar — logga yozamiz va foydalanuvchiga xabar beramiz
        logger.error("Xatolik:", exc_info=err)
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring."
                )
            except Exception:
                pass

    app.add_error_handler(error_handler)

    logger.info("🤖 Bot ishga tushdi!")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,   # Eski xabarlarni o'tkazib yuborish
    )


if __name__ == "__main__":
    main()