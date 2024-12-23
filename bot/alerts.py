import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from src.db.database import session
from src.db.models import User, UserStatus
from src.db.queries import get_user_alerts, delete_alert
from bot.keyboards.main_menu import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "my_alerts")
async def show_my_alerts(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки «Мои оповещения».
    Показываем пользователю список его оповещений и даём кнопки для удаления.
    """
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()

    # Проверим, не заблокирован ли пользователь.
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        return
    
    # Получаем список оповещений пользователя
    alerts = get_user_alerts(user_id)
    if not alerts:
        await callback_query.message.answer(
            "У вас пока нет ни одного оповещения.", 
            reply_markup=main_menu_keyboard()
        )
        await callback_query.answer()
        return

    # Формируем сообщение со списком оповещений
    text_lines = ["Ваши оповещения:"]
    for alert in alerts:
        # Содержимое alert может отличаться, зависит от вашей модели
        # Допустим, у нас есть alert_id и текст (или дата, цена и т.д.)
        text_lines.append(
            f"ID: {alert.alert_id}, {alert} "  # или любое формирование текста
        )
    alerts_text = "\n".join(text_lines)
    
    keyboard = []
    for alert in alerts:
        button_text = f"Удалить оповещение #{alert.alert_id}"
        callback_data = f"delete_alert_{alert.alert_id}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback_query.message.answer(
        alerts_text,
        reply_markup=inline_kb
    )
    await callback_query.answer()