import logging
import regex
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
router = Router()
logger = logging.getLogger(__name__)

class TicketSearchForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()

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
    F.data.in_(["ticket_econom", "ticket_business", "ticket_first", "ticket_seated"])
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
        for route in result_data:
            resp = (
                f"Маршрут ID: {route['route_id']}\n"
                f"Маршрут: {route['station_from']} -> {route['station_to']}\n"
                f"Глобальный: {route['route_global']}\n"
                f"Время отправления: {route['datetime0']}\n"
                f"Время прибытия: {route['datetime1']}\n"
                f"Класс: {route['class']}\n"
                f"Цена: {route['best_price']} руб.\n\n"
            )
            await callback_query.message.answer(resp)

    await state.clear()
