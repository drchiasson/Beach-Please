import os
import asyncio
from telegram import Update, ForceReply
from telegram.ext import CallbackContext, Application, MessageHandler, filters, ContextTypes

async def send_message_to_channel(application, message):
    print("Telegram Message" + str(message))
    await application.bot.send_message(os.environ.get("TELEGRAM_CHANNEL_KEY"), message)


def send_bot_message(message) -> None:
    application = Application.builder().token(os.environ.get("TELEGRAM_BOT_KEY")).build()
    asyncio.run(send_message_to_channel(application, message))