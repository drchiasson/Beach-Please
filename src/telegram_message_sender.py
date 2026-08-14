import os
import asyncio
from telegram import Bot

async def send_message_to_channel(message):
    print("Telegram Message" + str(message))
    bot = Bot(token=os.environ.get("TELEGRAM_BOT_KEY"))
    async with bot:
        await bot.send_message(chat_id=os.environ.get("TELEGRAM_CHANNEL_KEY"), text=message)

def send_bot_message(message) -> None:
    asyncio.run(send_message_to_channel(message))