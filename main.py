import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from config import Config
from handlers import start, admin, payment

dp = Dispatcher()
config = Config()

dp.include_router(start.router)
dp.include_router(payment.router)
dp.include_router(admin.router)

async def main():
    # session = AiohttpSession(proxy="http://45.153.160.6:50101")
    # bot = Bot(token=config.BOT_TOKEN, session=session)

    bot = Bot(token=config.BOT_TOKEN)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
