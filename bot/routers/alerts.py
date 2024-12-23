import logging
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from src.db.database import session
from src.db.models import User, UserStatus, City, Station, Route, TicketType
from src.db.queries import add_subscription, add_route, add_user, update_user, delete_subscription
from src.db.queries import load_cities_from_json
from src.core.rzd import get_station_code
from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.ticket_options import ticket_options_keyboard

router = Router()
logger = logging.getLogger(__name__)

FORBIDDEN_WORDS = []
try:
    with open("./resources/forbidden_words.txt", "r") as f:
        for line in f:
            words = [word.strip() for word in line.rstrip().split(",")]
            FORBIDDEN_WORDS.extend(words)
    logger.info("Запрещённые слова загружены.")
except FileNotFoundError:
    logger.warning("Файл input.txt не найден. Запрещённые слова не загружены.")

class AlertForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()

def contains_forbidden_words(text: str) -> bool:
    if not FORBIDDEN_WORDS:
        return False
    pattern = re.compile("|".join(map(re.escape, FORBIDDEN_WORDS)), re.IGNORECASE)
    return bool(pattern.search(text))

def check_date_correctness(date_str: str):
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None, "Некорректный формат даты или несуществующая дата."
    if date_obj < datetime.now():
        return None, "Дата уже прошла, введите будущую дату."
    return date_obj, None

def create_or_get_station(station_code: int, station_name: str):
    """Создаём или получаем станцию по коду (через session)."""
    st = session.query(Station).filter_by(station_id=station_code).first()
    if not st:
        c = session.query(City).filter_by(city_id=station_code).first()
        if not c:
            c = City(city_id=station_code, city_name=station_name)
            session.add(c)
            session.commit()

        st = Station(
            station_id=station_code, city_id=c.city_id, station_name=station_name
        )
        session.add(st)
        session.commit()
    return st.station_id

async def handle_inappropriate_input(message: Message, state: FSMContext):
    """Блокируем пользователя в базе, если ввёл запрещённые слова."""
    user_id = message.from_user.id
    await message.answer("Обнаружено неподобающее поведение. Вы заблокированы.")
    update_user(user_id, "banned")
    await state.clear()
    logger.warning(f"Пользователь {user_id} заблокирован за неподобающий ввод.")


@router.callback_query(F.data == "set_alert")
async def cb_set_alert(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(AlertForm.origin)
    await callback_query.message.answer("Введите точное наименование города отбытия (строчными буквами):")


@router.message(AlertForm.origin)
async def process_origin(message: Message, state: FSMContext):
    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(origin=text)
    await state.set_state(AlertForm.destination)
    await message.answer("Введите точное наименование города назначения (строчными буквами):")


@router.message(AlertForm.destination)
async def process_destination(message: Message, state: FSMContext):
    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(destination=text)
    await state.set_state(AlertForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")


@router.message(AlertForm.date)
async def process_date(message: Message, state: FSMContext):
    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    date_obj, error = check_date_correctness(text)
    if error:
        await message.answer(error)
        return

    await state.update_data(date=text)
    await state.set_state(AlertForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())


@router.callback_query(
    AlertForm.class_type,
    F.data.in_(["ticket_econom", "ticket_business", "ticket_first", "ticket_seated"]),
)
async def process_alert_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    class_data = callback_query.data
    class_types = {
        "ticket_econom": TicketType.plackart,
        "ticket_business": TicketType.cupe,
        "ticket_first": TicketType.sv,
        "ticket_seated": TicketType.seated,
    }
    class_type = class_types.get(class_data, TicketType.cupe)

    await state.update_data(class_type=class_type.value)
    await callback_query.answer()

    data = await state.get_data()
    origin = data["origin"]
    destination = data["destination"]
    date_str = data["date"]

    date_obj, error = check_date_correctness(date_str)
    if error:
        await callback_query.message.answer(error)
        await state.set_state(AlertForm.date)
        return

    try:
        code_from = get_station_code(origin)
        code_to = get_station_code(destination)
    except ValueError:
        await callback_query.message.answer(
            "Не удалось найти коды станций для указанных городов. Попробуйте другие."
        )
        await state.clear()
        return

    from_station_id = create_or_get_station(int(code_from), origin)
    to_station_id = create_or_get_station(int(code_to), destination)

    route_id = add_route(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        from_date=date_obj,
        to_date=date_obj,
        train_no=None,
    )
    await state.update_data(new_route_id=route_id)

    await callback_query.message.answer(
        f"Маршрут ID {route_id} создан!\nХотите ли вы подписаться на этот маршрут?",
        reply_markup=yes_no_button()
    )


    await callback_query.message.answer(
        f"Оповещение успешно установлено! (ID маршрута: {route_id})",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()