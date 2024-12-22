import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from src.db.database import session
from src.db.models import User, UserStatus, Subscription
from src.db.queries import (
    add_subscription,
    delete_subscription,
    get_route_by_id,
    update_user,
)
from bot.keyboards.main_menu import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

class DeleteAlertForm(StatesGroup):
    alert_id = State()

def list_user_subscriptions(user_id: int):
    """
    Возвращаем список подписок пользователя.
    """
    subs = (
        session.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .all()
    )
    results = []
    for sub in subs:
        route = get_route_by_id(sub.route_id)
        if route:
            date_str = route.from_date.strftime("%d.%m.%Y")
            results.append(
                {
                    "subscription_id": f"{user_id}_{route.route_id}",
                    "route_id": route.route_id,
                    "origin": route.from_station.station_name,
                    "destination": route.to_station.station_name,
                    "date": date_str,
                }
            )
    return results


@router.callback_query(F.data == "my_subscriptions")
async def cb_my_subscriptions(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    subscriptions = list_user_subscriptions(user_id)
    if not subscriptions:
        await callback_query.message.answer("У вас нет активных подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['subscription_id']}\n"
            f"Маршрут: {sub['origin']} -> {sub['destination']}\n"
            f"Дата: {sub['date']}\n\n"
        )
    response += "Чтобы отписаться: /unsubscribe <route_id>"
    await callback_query.message.answer(response)


@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(DeleteAlertForm.alert_id)
    await callback_query.message.answer("Введите ID оповещения (маршрута) для удаления:")


@router.message(DeleteAlertForm.alert_id)
async def process_delete_alert_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    try:
        route_id = int(text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
        return

    delete_subscription(user_id, route_id)
    await message.answer("Оповещение успешно удалено.", reply_markup=main_menu_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("subscribe_"))
async def cb_subscribe_route(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    try:
        route_id = int(callback_query.data.split("_")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Некорректный идентификатор маршрута.")
        return

    add_subscription(user_id, route_id)

    await callback_query.answer("Подписка успешно оформлена!")
    await callback_query.message.answer(
        f"Подписались на маршрут ID {route_id}!",
        reply_markup=main_menu_keyboard()
    )

@router.message(commands={"subscribe"})
async def subscribe_cmd(message: Message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используйте /subscribe <route_id>")
        return

    try:
        route_id = int(args[1])
    except ValueError:
        await message.answer("Неверный формат <route_id> (нужно число).")
        return

    add_subscription(user_id, route_id)
    await message.answer(f"Подписка успешно оформлена! (ID: {route_id})")


@router.message(commands={"unsubscribe"})
async def unsubscribe_cmd(message: Message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используйте /unsubscribe <route_id>")
        return

    try:
        route_id = int(args[1])
    except ValueError:
        await message.answer("Неверный формат <route_id> (нужно число).")
        return

    delete_subscription(user_id, route_id)
    await message.answer("Подписка успешно удалена.", reply_markup=main_menu_keyboard())
