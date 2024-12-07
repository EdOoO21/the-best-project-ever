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

from src.queries import (
    add_subscription,
    # get_subscriptions,
    # remove_subscription,
    add_user,
    delete_subscription,
    add_route,
    add_ticket
)
from src.models import TicketType
from requests.api_requests import (
    get_train_routes_with_session,
    get_station_code
)
from requests.update_db import update as update_db

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
    price = State()

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
            InlineKeyboardButton(text="СВ", callback_data="ticket_first")
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
    await state.clear()
    logger.warning(f"Пользователь {user_id} был заблокирован за неподобающий ввод.")

def contains_forbidden_words(text):
    if not FORBIDDEN_WORDS:
        return False
    pattern = re.compile('|'.join(map(re.escape, FORBIDDEN_WORDS)), re.IGNORECASE)
    return bool(pattern.search(text))

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
        return

    logger.info(f"Получена команда /start от пользователя {user_id}.")

    if user_id not in registered:
        registered.add(user_id)
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
    logger.info(f"Пользователь {user_id} нажал кнопку 'Установить оповещение'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

    await callback_query.answer()
    await state.set_state(AlertForm.origin)
    await bot.send_message(user_id, "Введите точное наименование города отбытия с маленькой буквы:")
    logger.info(f"Пользователь {user_id} переходит к вводу города отправления.")

@router.message(AlertForm.origin)
async def process_origin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"Пользователь {user_id} вводит город отправления: {text}")

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
    logger.info(f"Пользователь {user_id} вводит город назначения: {text}")

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
    logger.info(f"Пользователь {user_id} вводит дату поездки: {text}")

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    if not re.match(r'\d{2}\.\d{2}\.\d{4}', text):
        await message.answer("Некорректный формат даты. Пожалуйста, используйте ДД.ММ.ГГГГ:")
        return

    await state.update_data(date=text)
    await state.set_state(AlertForm.class_type)
    await message.answer("Выберите класс билета для оповещения:", reply_markup=ticket_options_keyboard())

@router.callback_query(AlertForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first']))
async def process_alert_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    class_data = callback_query.data

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        return

    class_types = {
        'ticket_econom': 'Плацкарт',
        'ticket_business': 'Купе',
        'ticket_first': 'СВ'
    }

    class_type = class_types.get(class_data, 'Неизвестный')
    await state.update_data(class_type=class_type)
    await callback_query.answer()
    await bot.send_message(user_id, f"Вы выбрали класс: {class_type}.")

    await state.set_state(AlertForm.price)
    await bot.send_message(user_id, "Введите максимальную цену билета:")

@router.message(AlertForm.price)
async def process_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        return

    try:
        price = float(text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (положительное число):")
        return

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date_str = data['date']
    class_type_str = data['class_type']

    class_map = {
        'Плацкарт': TicketType.plackart,
        'Купе': TicketType.cupe,
        'СВ': TicketType.sv
    }
    ticket_class = class_map.get(class_type_str, TicketType.cupe)

    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        await message.answer("Ошибка в формате даты. Попробуйте снова.")
        await state.clear()
        return

    try:
        code_from = get_station_code(origin)
        code_to = get_station_code(destination)
    except ValueError:
        await message.answer("Не удалось найти коды станций для указанных городов.")
        await state.clear()
        return

    route_id = add_route(
        from_station_id=int(code_from),
        to_station_id=int(code_to),
        from_date=date_obj,
        to_date=date_obj,
        train_no=None
    )

    add_subscription(user_id, route_id)

    add_ticket(route_id, ticket_class.value, int(price))

    await message.answer(
        f"Оповещение успешно установлено! (ID {route_id})", reply_markup=main_menu_keyboard()
    )
    logger.info(
        f"Пользователь {user_id} установил оповещение: {origin} -> {destination}, {date_str}, {class_type_str}, {price} руб. (ID {route_id})"
    )

    await state.clear()

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()

    user_alerts = get_subscriptions(user_id)

    if not user_alerts:
        await bot.send_message(user_id, "У вас нет установленных оповещений.")
        return

    response = "Ваши оповещения:\n"
    for alert in user_alerts:
        response += (
            f"ID: {alert['id']}\n"
            f"Маршрут: {alert['origin']} -> {alert['destination']}\n"
            f"Дата: {alert['date']}\n"
            f"Класс: {alert['class_type'] if alert['class_type'] else 'не указан'}\n"
            f"Макс. цена: {alert['price'] if alert['price'] else 'не указана'} руб.\n\n"
        )
    response += "Для удаления оповещения используйте команду:\n" \
                "/unsubscribe <id>\n" \
                "Например: /unsubscribe 123"
    await bot.send_message(user_id, response)

@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    await callback_query.answer()
    await state.set_state(DeleteAlertForm.alert_id)
    await bot.send_message(user_id, "Введите ID оповещения, которое хотите удалить:")

@router.message(DeleteAlertForm.alert_id)
async def process_delete_alert_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    alert_id_text = message.text.strip()

    if contains_forbidden_words(alert_id_text):
        await handle_inappropriate_input(message, state)
        return

    try:
        alert_id = int(alert_id_text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
        return

    success = remove_subscription(user_id, alert_id)

    if success:
        await message.answer("Оповещение успешно удалено.", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Оповещение с таким ID не найдено или не принадлежит вам.", reply_markup=main_menu_keyboard())

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

    if not re.match(r'\d{2}\.\d{2}\.\d{4}', text):
        await message.answer("Некорректный формат даты. Пожалуйста, используйте ДД.ММ.ГГГГ:")
        return

    await state.update_data(date=text)
    await state.set_state(TicketSearchForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())

@router.callback_query(TicketSearchForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first']))
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    class_data = callback_query.data

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы.")
        return

    class_types = {
        'ticket_econom': 'Плацкарт',
        'ticket_business': 'Купе',
        'ticket_first': 'СВ'
    }
    class_type_str = class_types.get(class_data, 'Неизвестный')

    await state.update_data(class_type=class_type_str)
    await callback_query.answer()
    await bot.send_message(user_id, f"Вы выбрали класс: {class_type_str}.")

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date_str = data['date']

    try:
        code_from = get_station_code(origin)
        code_to = get_station_code(destination)
    except ValueError:
        await bot.send_message(user_id, "Не удалось найти коды станций для указанных городов.")
        await state.clear()
        return

    result_data = get_train_routes_with_session(code_from, code_to, date_str)
    if result_data is None or result_data == 'NO TICKETS':
        await bot.send_message(user_id, "Билеты не найдены.")
        await state.clear()
        return

    routes = []
    try:
        tp = result_data.get('tp', [])
        if tp and 'list' in tp[0]:
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
                        price_value = car.get('tariff', {}).get('value')
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

    subscriptions = get_subscriptions(user_id)

    if not subscriptions:
        await bot.send_message(user_id, "У вас нет активных подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['id']}\n"
            f"Маршрут: {sub['origin']} -> {sub['destination']}\n"
            f"Дата: {sub['date']}\n"
            f"Цена: {sub['price'] if sub['price'] else 'не указана'} руб.\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <id>\n" \
                "Например: /unsubscribe 123"
    await bot.send_message(user_id, response)

@router.message(Command('subscribe'))
async def subscribe_route(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("Неверный формат команды. Используйте /subscribe <route_id> <max_price>")
        return

    try:
        route_id = int(args[1])
        max_price = float(args[2])
        if max_price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректные числовые значения для ID маршрута и максимальной цены.")
        return

    add_subscription(user_id, route_id)
    await message.answer(f"Подписка успешно оформлена! (ID {route_id})")

@router.message(Command('unsubscribe'))
async def unsubscribe_route(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Неверный формат команды. Используйте /unsubscribe <id>")
        return

    try:
        sub_id = int(args[1])
    except ValueError:
        await message.answer("Пожалуйста, введите числовой ID подписки.")
        return

    success = remove_subscription(user_id, sub_id)

    if success:
        await message.answer("Подписка успешно удалена.", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Подписка с таким ID не найдена или не принадлежит вам.", reply_markup=main_menu_keyboard())

@router.message(Command('subscriptions'))
async def list_subscriptions(message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы.")
        return

    subscriptions = get_subscriptions(user_id)
    if not subscriptions:
        await message.answer("У вас нет действующих подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['id']}\n"
            f"Маршрут: {sub['origin']} -> {sub['destination']}\n"
            f"Дата: {sub['date']}\n"
            f"Цена: {sub['price'] if sub['price'] else 'не указана'} руб.\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <id>"
    await message.answer(response)

async def scheduled_clean():
    while True:
        update_db()
        logger.info("Периодическая очистка/обновление базы данных выполнена.")
        await asyncio.sleep(86400)  # раз в сутки

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
