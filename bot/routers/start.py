import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.database import session
from src.db.models import User, UserStatus
from src.db.queries import add_user
from bot.keyboards.main_menu import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()

    if not user:
        add_user(user_id)
        welcome_text = (
            f"Добро пожаловать, {message.from_user.first_name}! "
            "Вы успешно зарегистрированы.\nВыберите действие ниже:"
        )
        logger.info(f"Новый пользователь {user_id} зарегистрировался.")
    else:
        welcome_text = f"С возвращением, {message.from_user.first_name}! Что хотите сделать сегодня?"
        logger.info(f"Пользователь {user_id} повторно зашёл в /start.")

    await message.answer(welcome_text, reply_markup=main_menu_keyboard())
