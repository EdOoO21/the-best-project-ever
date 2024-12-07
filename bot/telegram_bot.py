from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import re
from pprint import pprint

from src.queries import (
    add_subscription,
    add_user,
    delete_subscription,
    add_route,
    load_cities_from_json
)
from src.database import session
from src.models import TicketType, User, Subscription, Route, Station, UserStatus, City
from requests_and_update.api_requests import (
    get_train_routes_with_session,
    get_station_code
)
from requests_and_update.update_db import update as update_db
load_cities_from_json("./docs/city_codes.json")
from bot.config import settings
import requests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)

dp = Dispatcher(storage=MemoryStorage())
router = Router()

class AlertForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()

class TicketSearchForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    class_type = State()

class DeleteAlertForm(StatesGroup):
    alert_id = State()

FORBIDDEN_WORDS = []
try:
    with open('input.txt', 'r', encoding='utf-8') as f:
        for line in f:
            words = [word.strip() for word in line.rstrip().split(",")]
            FORBIDDEN_WORDS.extend(words)
    logger.info("Запрещенные слова успешно загружены.")
except FileNotFoundError:
    logger.warning("Файл input.txt не найден. Запрещенные слова не загружены.")

registered = set()
banned_users = set()

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Установить оповещение", callback_data="set_alert"),
            InlineKeyboardButton(text="Мои оповещения", callback_data="my_alerts")
        ],
        [
            InlineKeyboardButton(text="Удалить оповещение", callback_data="delete_alert")
        ],
        [
            InlineKeyboardButton(text="Получить билеты", callback_data="get_tickets")
        ],
        [
            InlineKeyboardButton(text="Мои подписки", callback_data="my_subscriptions")
        ]
    ])
    return keyboard

def ticket_options_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Плацкарт", callback_data="ticket_econom"),
            InlineKeyboardButton(text="Купе", callback_data="ticket_business")
        ],
        [
            InlineKeyboardButton(text="СВ", callback_data="ticket_first"),
            InlineKeyboardButton(text="Сидячий", callback_data="ticket_seated")
        ]
    ])
    return keyboard

def subscribe_button(route_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подписаться на маршрут", callback_data=f"subscribe_{route_id}")
        ]
    ])
    return keyboard

async def handle_inappropriate_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer("Обнаружено неподобающее поведение. Вы заблокированы.")
    banned_users.add(user_id)
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.status = UserStatus.banned
        session.commit()
    await state.clear()
    logger.warning(f"Пользователь {user_id} был заблокирован за неподобающий ввод.")

def contains_forbidden_words(text):
    if not FORBIDDEN_WORDS:
        return False
    pattern = re.compile('|'.join(map(re.escape, FORBIDDEN_WORDS)), re.IGNORECASE)
    return bool(pattern.search(text))

def list_user_subscriptions(user_id: int):
    """
    Получаем все подписки пользователя с деталями маршрутов.
    Возвращаем список словарей.
    """
    subs = (session.query(Subscription, Route)
            .join(Route, Subscription.route_id == Route.route_id)
            .filter(Subscription.user_id == user_id)
            .all())
    
    results = []
    for sub, route in subs:
        from_st = session.query(Station).filter_by(station_id=route.from_station_id).first()
        to_st = session.query(Station).filter_by(station_id=route.to_station_id).first()

        origin_name = from_st.station_name if from_st else "неизвестно"
        destination_name = to_st.station_name if to_st else "неизвестно"
        date_str = route.from_date.strftime("%d.%m.%Y") if route.from_date else "неизвестно"

        results.append({
            "subscription_id": f"{sub.user_id}_{sub.route_id}",
            "route_id": route.route_id,
            "origin": origin_name,
            "destination": destination_name,
            "date": date_str
        })
    return results


def create_or_get_station(station_code: int, station_name: str):
    """
    Создаём или получаем станцию по коду.
    """
    st = session.query(Station).filter_by(station_id=station_code).first()
    if not st:
        c = session.query(City).filter_by(city_id=station_code).first()
        if not c:
            c = City(city_id=station_code, city_name=station_name)
            session.add(c)
            session.commit()

        st = Station(station_id=station_code, city_id=c.city_id, station_name=station_name)
        session.add(st)
        session.commit()
    return st.station_id

def check_date_correctness(date_str: str):
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None, "Некорректный формат даты или несуществующая дата."
    if date_obj < datetime.now():
        return None, "Дата уже прошла, введите будущую дату."
    return date_obj, None

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
        return

    logger.info(f"Получена команда /start от пользователя {user_id}.")

    if user_id not in registered:
        registered.add(user_id)
        if not user:
            add_user(user_id)
        welcome_text = (
            f"Добро пожаловать, {message.from_user.first_name}! Вы успешно зарегистрированы.\n"
            "Выберите действие ниже:"
        )
        logger.info(f"Новый пользователь {user_id} зарегистрировался.")
    else:
        welcome_text = (
            f"С возвращением, {message.from_user.first_name}! Что вы хотите сделать сегодня?"
        )
        logger.info(f"Пользователь {user_id} повторно использовал команду /start.")

    await message.answer(welcome_text, reply_markup=main_menu_keyboard())
    logger.info(f"Пользователь {user_id} получил главное меню.")

@router.callback_query(F.data == "set_alert")
async def cb_set_alert(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        return

    await callback_query.answer()
    await state.set_state(AlertForm.origin)
    await bot.send_message(user_id, "Введите точное наименование города отбытия с маленькой буквы:")

@router.message(AlertForm.origin)
async def process_origin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(origin=text)
    await state.set_state(AlertForm.destination)
    await message.answer("Введите точное наименование города назначения с маленькой буквы:")


@router.message(AlertForm.destination)
async def process_destination(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(destination=text)
    await state.set_state(AlertForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")

@router.message(AlertForm.date)
async def process_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
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
    await message.answer("Выберите класс билета для оповещения:", reply_markup=ticket_options_keyboard())

@router.callback_query(AlertForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first', 'ticket_seated']))
async def process_alert_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if user and user.status == UserStatus.banned:
        await callback_query.answer("Вы заблокированы.")
        return

    class_data = callback_query.data
    class_types = {
        'ticket_econom': TicketType.plackart,
        'ticket_business': TicketType.cupe,
        'ticket_first': TicketType.sv,
        'ticket_seated': TicketType.seated
    }

    class_type = class_types.get(class_data, TicketType.cupe)
    await state.update_data(class_type=class_type.value)
    await callback_query.answer()

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date_str = data['date']

    date_obj, error = check_date_correctness(date_str)
    if error:
        await bot.send_message(user_id, error)
        await state.set_state(AlertForm.date)
        return

    try:
        code_from = get_station_code(origin)
        code_to = get_station_code(destination)
    except ValueError:
        await bot.send_message(user_id, "Не удалось найти коды станций для указанных городов. Попробуйте другие.")
        await state.clear()
        return

    from_station_id = create_or_get_station(int(code_from), origin)
    to_station_id = create_or_get_station(int(code_to), destination)

    route_id = add_route(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        from_date=date_obj,
        to_date=date_obj,
        train_no=None
    )

    add_subscription(user_id, route_id)

    await bot.send_message(user_id, f"Оповещение успешно установлено! (ID маршрута: {route_id})", reply_markup=main_menu_keyboard())
    await state.clear()

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()

    user_alerts = list_user_subscriptions(user_id)
    if not user_alerts:
        await bot.send_message(user_id, "У вас нет установленных оповещений.")
        return

    response = "Ваши оповещения:\n"
    for alert in user_alerts:
        response += (
            f"ID подписки: {alert['subscription_id']}\n"
            f"Маршрут: {alert['origin']} -> {alert['destination']}\n"
            f"Дата: {alert['date']}\n\n"
        )
    response += "Для удаления оповещения: /unsubscribe <route_id>"

    await bot.send_message(user_id, response)

@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(DeleteAlertForm.alert_id)
    await bot.send_message(user_id, "Введите ID оповещения (маршрута), которое хотите удалить:")

@router.message(DeleteAlertForm.alert_id)
async def process_delete_alert_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    alert_id_text = message.text.strip()

    if contains_forbidden_words(alert_id_text):
        await handle_inappropriate_input(message, state)
        return

    try:
        route_id = int(alert_id_text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
        return

    delete_subscription(user_id, route_id)
    await message.answer("Оповещение успешно удалено.", reply_markup=main_menu_keyboard())
    await state.clear()

@router.callback_query(F.data == "get_tickets")
async def cb_get_tickets(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(TicketSearchForm.origin)
    await bot.send_message(user_id, "Введите город отправления:")

@router.message(TicketSearchForm.origin)
async def process_ticket_origin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(origin=text)
    await state.set_state(TicketSearchForm.destination)
    await message.answer("Введите город назначения:")

@router.message(TicketSearchForm.destination)
async def process_ticket_destination(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    await state.update_data(destination=text)
    await state.set_state(TicketSearchForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")

@router.message(TicketSearchForm.date)
async def process_ticket_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    date_obj, error = check_date_correctness(text)
    if error:
        await message.answer(error)
        return

    await state.update_data(date=text)
    await state.set_state(TicketSearchForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())

@router.callback_query(TicketSearchForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first', 'ticket_seated']))
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    class_data = callback_query.data
    class_map = {
        'ticket_econom': 'Плацкарт',
        'ticket_business': 'Купе',
        'ticket_first': 'СВ',
        'ticket_seated': 'Сидячий'
    }
    class_type_str = class_map.get(class_data, 'Неизвестный')

    await state.update_data(class_type=class_type_str)
    await callback_query.answer()
    await bot.send_message(user_id, f"Вы выбрали класс: {class_type_str}.")

    data = await state.get_data()
    if not all(k in data for k in ('origin', 'destination', 'date')):
        await bot.send_message(user_id, "Произошла ошибка. Пожалуйста, начните заново /start.")
        await state.clear()
        return

    origin = data['origin']
    destination = data['destination']
    date_str = data['date']

    date_obj, error = check_date_correctness(date_str)
    if error:
        await bot.send_message(user_id, error)
        await state.set_state(TicketSearchForm.date)
        return

    try:
        code_from = get_station_code(origin)
        code_to = get_station_code(destination)
    except ValueError:
        await bot.send_message(user_id, "Не удалось найти коды станций для указанных городов. Попробуйте другие.")
        await state.clear()
        return

    result_data = get_train_routes_with_session(code_from, code_to, date_str)
    if not isinstance(result_data, dict):
        await bot.send_message(user_id, "Произошла ошибка при получении данных о маршрутах.")
        await state.clear()
        return

    if result_data == 'NO TICKETS':
        await bot.send_message(user_id, "Билеты не найдены.")
        await state.clear()
        return

    routes = []
    try:
        tp = result_data.get('tp', [])
        if tp and isinstance(tp, list) and 'list' in tp[0]:
            trains = tp[0]['list']
            for idx, train in enumerate(trains, start=1):
                route_id = train.get('number', f"train_{idx}")
                station_from = train.get('station0', origin)
                station_to = train.get('station1', destination)
                route_date = date_str
                cars = train.get('cars', [])
                best_price = None
                if cars:
                    prices = []
                    for car in cars:
                        price_value = car.get('tariff')
                        if price_value is not None:
                            prices.append(price_value)
                    if prices:
                        best_price = min(prices)
                if best_price is None:
                    best_price = "нет данных"

                routes.append({
                    'route_id': route_id,
                    'station_from': station_from,
                    'station_to': station_to,
                    'route_global': f"{station_from}-{station_to}",
                    'time': f"{train.get('time0')} - {train.get('time1')}",
                    'date': route_date,
                    'best_price': best_price
                })
    except Exception as e:
        logger.error(f"Ошибка при обработке данных маршрута: {e}")
        routes = []

    if not routes:
        await bot.send_message(user_id, "Билеты не найдены.")
    else:
        for route in routes:
            response = (
                f"Маршрут ID: {route['route_id']}\n"
                f"Маршрут: {route['station_from']} -> {route['station_to']}\n"
                f"Глобальный маршрут: {route['route_global']}\n"
                f"Дата: {route['date']}\n"
                f"Время: {route['time']}\n"
                f"Класс: {class_type_str}\n"
                f"Цена: {route['best_price']} руб.\n\n"
            )
            await bot.send_message(user_id, response)

    await state.clear()


@router.callback_query(F.data.startswith("subscribe_"))
async def cb_subscribe_route(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    try:
        route_id = int(callback_query.data.split("_")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Некорректный идентификатор маршрута.")
        return

    add_subscription(user_id, route_id)

    await callback_query.answer("Подписка успешно оформлена!")
    await bot.send_message(user_id, f"Вы подписались на маршрут ID {route_id}!", reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "my_subscriptions")
async def cb_my_subscriptions(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()

    subscriptions = list_user_subscriptions(user_id)
    if not subscriptions:
        await bot.send_message(user_id, "У вас нет активных подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['subscription_id']}\n"
            f"Маршрут: {sub['origin']} -> {sub['destination']}\n"
            f"Дата: {sub['date']}\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <route_id>"
    await bot.send_message(user_id, response)

@router.message(Command('subscribe'))
async def subscribe_route(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Неверный формат команды. Используйте /subscribe <route_id>")
        return

    try:
        route_id = int(args[1])
    except ValueError:
        await message.answer("Пожалуйста, введите числовой ID маршрута.")
        return

    add_subscription(user_id, route_id)
    await message.answer(f"Подписка успешно оформлена! (ID маршрута: {route_id})")

@router.message(Command('unsubscribe'))
async def unsubscribe_route(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Неверный формат команды. Используйте /unsubscribe <route_id>")
        return

    try:
        route_id = int(args[1])
    except ValueError:
        await message.answer("Пожалуйста, введите числовой ID маршрута.")
        return

    delete_subscription(user_id, route_id)
    await message.answer("Подписка успешно удалена.", reply_markup=main_menu_keyboard())

@router.message(Command('subscriptions'))
async def list_subscriptions_cmd(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    subscriptions = list_user_subscriptions(user_id)
    if not subscriptions:
        await message.answer("У вас нет действующих подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['subscription_id']}\n"
            f"Маршрут: {sub['origin']} -> {sub['destination']}\n"
            f"Дата: {sub['date']}\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <route_id>"
    await message.answer(response)

async def scheduled_clean():
    while True:
        update_db()
        logger.info("Периодическое обновление базы данных выполнено.")
        await asyncio.sleep(86400)

async def main():
    dp.include_router(router)
    asyncio.create_task(scheduled_clean())
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
