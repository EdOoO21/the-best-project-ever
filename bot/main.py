import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from src.db.database import session
from src.db.queries import load_cities_from_json
from src.core.update_db import update as update_db

from bot.routers.start import router as start_router
#from bot.routers.subscribtions import router as subscriptions_router
#from bot.routers.alerts import router as alerts_router
from bot.routers.tickets import router as tickets_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

from bot.config import settings

TOKEN = settings.BOT_TOKEN
if not TOKEN:
    logger.error("Не найден токен бота в переменных окружения.")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def scheduled_clean():
    while True:
        update_db()
        logger.info("Периодическое обновление базы данных выполнено.")
        await asyncio.sleep(86400)


async def main():
    load_cities_from_json("./resources/city_codes.json")

    dp.include_router(start_router)
#    dp.include_router(alerts_router)
#    dp.include_router(subscriptions_router)
    dp.include_router(tickets_router)

    asyncio.create_task(scheduled_clean())

    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
