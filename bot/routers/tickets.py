import logging
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from src.db.database import session
from src.db.queries import get_city_code
from src.db.models import User, UserStatus
from src.core.rzd import get_station_code, get_train_routes_with_session
from bot.keyboards.ticket_options import ticket_options_keyboard
from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.subscribe_button import yes_no_button, subscribe_button

router = Router()
logger = logging.getLogger(__name__)

class TicketSearchForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()

class SubscriptionForm(StatesGroup):
    waiting_for_route_indices = State()

def check_date_correctness(date_str: str):
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None, "Некорректный формат даты. Введите заново."
    if date_obj < datetime.now():
        return None, "Дата уже прошла, введите будущую дату. Введите заново."
    return date_obj, None

@router.callback_query(F.data == "get_tickets")
async def cb_get_tickets(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(TicketSearchForm.origin)
    await callback_query.message.answer("Введите город отправления:")

@router.message(TicketSearchForm.origin)
async def process_ticket_origin(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(origin=text)
    await state.set_state(TicketSearchForm.destination)
    await message.answer("Введите город назначения:")

@router.message(TicketSearchForm.destination)
async def process_ticket_destination(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(destination=text)
    await state.set_state(TicketSearchForm.date)
    await message.answer("Введите дату поездки (ДД.ММ.ГГГГ):")

@router.message(TicketSearchForm.date)
async def process_ticket_date(message: Message, state: FSMContext):
    text = message.text.strip()
    date_obj, error = check_date_correctness(text)
    if error:
        await message.answer(error)
        return

    await state.update_data(date=text)
    await state.set_state(TicketSearchForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())

@router.callback_query(
    TicketSearchForm.class_type,
    F.data.in_(["ticket_econom", "ticket_business", "ticket_first", "ticket_seated"]),
)
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    class_data = callback_query.data
    class_map = {
        "ticket_econom": "Плацкартный",
        "ticket_business": "Купе",
        "ticket_first": "СВ",
        "ticket_seated": "Сидячий",
    }
    class_type_str = class_map.get(class_data, "Неизвестный")

    await callback_query.answer()
    await callback_query.message.answer(f"Вы выбрали класс: {class_type_str}.")
    await state.update_data(class_type=class_type_str)

    data = await state.get_data()
    origin = data.get("origin")
    destination = data.get("destination")
    date_str = data.get("date")

    date_obj, error = check_date_correctness(date_str)
    if error:
        await callback_query.message.answer(error)
        await state.set_state(TicketSearchForm.date)
        return

    try:
        code_from = get_city_code(origin)
        code_to = get_city_code(destination)
    except ValueError:
        await callback_query.message.answer("Не удалось найти коды станций, попробуйте другие города.")
        await state.clear()
        return

    result_data = get_train_routes_with_session(code_from, code_to, date_str, place_type=class_type_str)

    if result_data == "NO TICKETS":
        await callback_query.message.answer("Билеты по этому маршруту без пересадок не найдены.")
        await state.clear()
        return

    if not result_data:
        await callback_query.message.answer("Билеты не найдены.")
    else:
        route_ids = []
        for (index, route) in enumerate(result_data):
            resp = (
                f"Номер найденного маршрута: {index + 1}\n"
                f"Маршрут ID: {route['route_id']}\n"
                f"Маршрут: {route['station_from']} -> {route['station_to']}\n"
                f"Глобальный: {route['route_global']}\n"
                f"Время отправления: {route['datetime0']}\n"
                f"Время прибытия: {route['datetime1']}\n"
                f"Класс: {route['class']}\n"
                f"Цена: {route['best_price']} руб.\n\n"
            )
            await callback_query.message.answer(resp)
            route_ids.append(route['route_id'])

        if route_ids:
            await state.update_data(route_ids=route_ids)
            await callback_query.message.answer(
                "Хотите ли вы подписаться на 1 или несколько маршрутов?",
                reply_markup=yes_no_button(),
            )
        else:
            await callback_query.message.answer("Нет доступных маршрутов для подписки.")
@router.callback_query(F.data == "set_subscription")
async def cb_set_subscription(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(SubscriptionForm.waiting_for_route_indices)
    await callback_query.message.answer(
        "Введите номер(а) маршрута через пробел, которые хотите подписать."
    )

# Обработчик колбэка "Нет" (не подписываться)
@router.callback_query(F.data == "no_subscription")
async def cb_no_subscription(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await callback_query.message.answer(
        "Хорошо, возвращаемся в главное меню.", reply_markup=main_menu_keyboard()
    )
    await state.clear()

# Обработчик ввода номеров маршрутов для подписки
@router.message(SubscriptionForm.waiting_for_route_indices)
async def process_subscription_indices(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    # Получаем route_ids из состояния
    data = await state.get_data()
    route_ids = data.get("route_ids", [])

    if not route_ids:
        await message.answer("Нет маршрутов для подписки.")
        await state.clear()
        return

    # Разбиваем введённый текст по пробелам
    indices_str = text.split()
    if not indices_str:
        await message.answer("Вы не ввели ни одного номера маршрута. Попробуйте снова.")
        return

    # Преобразуем строки в числа и проверяем валидность
    indices = []
    errors = []
    for s in indices_str:
        try:
            i = int(s)
            if 1 <= i <= len(route_ids):
                indices.append(i - 1)  # индексы начинаются с 0
            else:
                errors.append(f"Номер маршрута {s} вне диапазона.")
        except ValueError:
            errors.append(f"'{s}' не является числом.")

    # Отправляем ошибки пользователю
    for error_msg in errors:
        await message.answer(error_msg)

    if not indices:
        await message.answer("Ни один маршрут не был добавлен в подписки.")
        await state.clear()
        return

    # Убираем дубликаты и сортируем
    indices = sorted(set(indices))

    # Добавляем подписки на выбранные маршруты
    subscribed_route_ids = []
    for i in indices:
        route_id = route_ids[i]
        add_subscription(user_id, route_id)
        subscribed_route_ids.append(route_id)

    if subscribed_route_ids:
        routes_str = ", ".join(map(str, subscribed_route_ids))
        await message.answer(f"Подписка успешно оформлена на маршруты: {routes_str}.")
    else:
        await message.answer("Ни один маршрут не был добавлен в подписки.")

    # Возвращаемся в главное меню и очищаем состояние
    await message.answer("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
    await state.clear()