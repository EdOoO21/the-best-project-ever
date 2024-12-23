import logging
import re
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.subscribe_button import subscribe_button
from bot.keyboards.ticket_options import ticket_options_keyboard
from src.core.rzd import get_train_routes_with_session
from src.db.database import session
from src.db.models import User, UserStatus
from src.db.queries import (add_route, add_station, add_subscription,
                            add_ticket, check_user_is_banned, get_city_code,
                            get_user_subscrtions)

router = Router()
logger = logging.getLogger(__name__)


class TicketSearchForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()


def check_date_correctness(date_str: str):
    """
    Проверяет, что дата в формате ДД.ММ.ГГГГ и она не в прошлом
    """
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None, "Некорректный формат даты. Введите заново."
    if date_obj < datetime.now():
        return None, "Дата уже прошла, введите будущую дату. Введите заново."
    return date_obj, None


@router.callback_query(F.data == "get_tickets")
async def cb_get_tickets(callback_query: CallbackQuery, state: FSMContext):
    """
    Нажали кнопку получить билеты
    """
    user_id = callback_query.from_user.id
    if check_user_is_banned(user_id):
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
    await message.answer(
        "Выберите класс билета:", reply_markup=ticket_options_keyboard()
    )


@router.callback_query(
    TicketSearchForm.class_type,
    F.data.in_(["ticket_econom", "ticket_business", "ticket_first", "ticket_seated"]),
)
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if check_user_is_banned(user_id):
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
    origin = data["origin"]
    destination = data["destination"]
    date_str = data["date"]
    date_obj, error = check_date_correctness(date_str)
    if error:
        await callback_query.message.answer(error)
        await state.set_state(TicketSearchForm.date)
        return

    try:
        code_from = get_city_code(origin)
        code_to = get_city_code(destination)
    except ValueError:
        await callback_query.message.answer(
            "Не удалось найти коды станций, попробуйте другие города."
        )
        await state.clear()
        return

    result_data = get_train_routes_with_session(
        code_from, code_to, date_obj, place_type=class_type_str
    )

    if result_data == "NO TICKETS":
        await callback_query.message.answer("Билеты по этому маршруту не найдены.")
        await state.clear()
        return

    if not result_data:
        await callback_query.message.answer("Билеты не найдены.")
        await state.clear()
        return

    await state.update_data(searched_routes=result_data)

    for index, route in enumerate(result_data):
        resp = (
            f"Маршрут №{index + 1}\n"
            f"ID: {route['route_id']}\n"
            f"{route['station_from']} -> {route['station_to']}\n"
            f"Отправление: {route['datetime0']}\n"
            f"Прибытие: {route['datetime1']}\n"
            f"Класс: {route['class']}\n"
            f"Свободные места: {route['frseats']}\n"
            f"Цена: {route['best_price']} руб.\n"
        )
        await callback_query.message.answer(resp, reply_markup=subscribe_button(index))

    await callback_query.message.answer(
        "Нажмите «Подписаться» для интересующего вас маршрута."
    )
    await callback_query.answer(reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("subscribe_"))
async def cb_subscribe_route(callback_query: CallbackQuery, state: FSMContext):
    """
    Когда пользователь нажимает «Подписаться» на конкретный маршрут
    """
    user_id = callback_query.from_user.id
    if check_user_is_banned(user_id):
        await callback_query.answer("Вы заблокированы.")
        return
    data_parts = callback_query.data.split("_")
    print(data_parts)
    stored_data = await state.get_data()
    routes = stored_data.get("searched_routes")
    route_info = routes[int(data_parts[1])]

    from_station_name = route_info["station_from"]
    to_station_name = route_info["station_to"]
    from_date = route_info["datetime0"]
    to_date = route_info["datetime1"]
    train_no = route_info["route_id"]
    class_name = route_info["class"]
    city_from = route_info["from"]
    city_from_code = route_info["fromCode"]
    station_code_from = route_info["station_code_from"]
    station_code_to = route_info["station_code_to"]
    city_where_code = route_info["whereCode"]

    add_station(city_from_code, station_code_from, from_station_name)
    add_station(city_where_code, station_code_to, to_station_name)

    route_id_db = add_route(
        from_station_id=station_code_from,
        to_station_id=station_code_to,
        from_date=from_date,
        to_date=to_date,
        train_no=train_no,
        class_name=class_name.lower(),
    )
    add_subscription(user_id, route_id_db)
    add_ticket(route_id_db, route_info["best_price"])

    await callback_query.message.answer(
        f"Вы подписались на маршрут \n" f"({from_station_name} -> {to_station_name})."
    )

    await callback_query.answer(reply_markup=main_menu_keyboard())
