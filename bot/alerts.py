import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from src.db.database import session
from src.db.models import User, UserStatus
from src.db.queries import (
    check_user_is_banned,
    get_user_subscrtions,
    delete_subscription,
    get_city,
    get_users_subscribed_to_route
)
from bot.keyboards.main_menu import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_alerts")
async def cb_get_alerts(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки Получить оповещения
    """
    user_id = callback_query.from_user.id

    is_banned = check_user_is_banned(user_id)
    if check_user_is_banned(user_id):
        await callback_query.answer("Вы заблокированы и не можете использовать бота.")
        return

    subscriptions_info = get_user_subscrtions(user_id)
    if not subscriptions_info:
        await callback_query.message.answer(
            "У вас пока нет оповещений (подписок).",
            reply_markup=main_menu_keyboard()
        )
        await callback_query.answer()
        return

    lines = ["Ваши подписки (оповещения):"]
    inline_kb = []

    for route_info in subscriptions_info:
        route_id = route_info["route_id"]
        text_route = (
            f"Маршрут #{route_info['route_id']}:\n"
            f"Станция отправления: {get_city(route_info['from_station']).city_name}\n"
            f"Станция прибытия: {get_city(route_info['to_station']).city_name}\n"
            f"Последняя цена:{route_info['best_price']} руб."
            f"Поезд: {route_info['train_no']} \n"
            f"Время отправления: {route_info['from_date']}\n"
            f"Время прибытия: {route_info['to_date']}\n"
        )
        lines.append(text_route)
        callback_data = f"del_sub_{route_id}"
        inline_kb.append([
            InlineKeyboardButton(
                text=f"Удалить подписку #{route_id}",
                callback_data=callback_data
            )
        ])
    
    text_all = "\n\n".join(lines)
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    await callback_query.message.answer(text_all, reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_sub_"))
async def cb_delete_subscription_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Удаляем подписку пользователя на этот маршрут (если она у него есть).
    """
    user_id = callback_query.from_user.id

    if check_user_is_banned(user_id):
        await callback_query.answer("Вы заблокированы.")
        return

    parts = callback_query.data.split("_")

    try:
        route_id = int(parts[2])
    except ValueError:
        await callback_query.answer("Некорректный ID маршрута.")
        return

    delete_subscription(user_id, route_id)

    await callback_query.message.answer(
        f"Подписка на маршрут #{route_id} удалена (если она у вас была).",
        reply_markup=main_menu_keyboard()
    )
    await callback_query.answer()