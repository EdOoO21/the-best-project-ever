from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, Text
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

from ed_requests import (
    get_routes,
    add_subscription,
    get_subscriptions,
    remove_subscription,
    clean_old_subscriptions,
)

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
    """
    Создает главное меню бота с набором кнопок
    """
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
    """
    Клавиатура для выбора типа билета
    """
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
    """
    Создает кнопку для подписки на маршрут
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подписаться на маршрут", callback_data=f"subscribe_{route_id}")
        ]
    ])
    return keyboard

async def handle_inappropriate_input(message: Message, state: FSMContext):
    """
    Блокирует пользователя и уведомляет его о нарушении
    """
    user_id = message.from_user.id
    await message.answer("Обнаружено неподобающее поведение. Вы заблокированы.")
    banned_users.add(user_id)
    await state.clear()
    logger.warning(f"Пользователь {user_id} был заблокирован за неподобающий ввод.")

def contains_forbidden_words(text):
    """
    Проверяет, содержит ли текст запрещенные слова
    """
    if not FORBIDDEN_WORDS:
        return False
    pattern = re.compile('|'.join(map(re.escape, FORBIDDEN_WORDS)), re.IGNORECASE)
    return bool(pattern.search(text))

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    """
    Обрабатывает команду /start: регистрирует пользователя и показывает главное меню
    """
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
        return

    logger.info(f"Получена команда /start от пользователя {user_id}.")

    if user_id not in registered:
        registered.add(user_id)
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
    """
    Обрабатывает нажатие кнопки "Установить оповещение": переходит к вводу города отправления
    """
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
    """
    Обрабатывает ввод города отправления и переходит к вводу города назначения
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит город отправления: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город отправления.")
        return

    await state.update_data(origin=text)
    await state.set_state(AlertForm.destination)
    await message.answer("Введите точное наименование города назначения с маленькой буквы:")
    logger.info(f"Пользователь {user_id} установил город отправления: {text}")

@router.message(AlertForm.destination)
async def process_destination(message: Message, state: FSMContext):
    """
    Обрабатывает ввод города назначения и переходит к вводу даты поездки
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит город назначения: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город назначения.")
        return

    await state.update_data(destination=text)
    await state.set_state(AlertForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")
    logger.info(f"Пользователь {user_id} установил город назначения: {text}")

@router.message(AlertForm.date)
async def process_date(message: Message, state: FSMContext):
    """
    Обрабатывает ввод даты поездки и переходит к выбору класса билета
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит дату поездки: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающую дату поездки.")
        return

    if not re.match(r'\d{2}\.\d{2}\.\d{4}', text):
        await message.answer("Некорректный формат даты. Пожалуйста, используйте ДД.ММ.ГГГГ:")
        logger.warning(f"Пользователь {user_id} ввел некорректный формат даты: {text}")
        return

    await state.update_data(date=text)
    await state.set_state(AlertForm.class_type)
    await message.answer("Выберите класс билета для оповещения:", reply_markup=ticket_options_keyboard())
    logger.info(f"Пользователь {user_id} установил дату поездки: {text}")

@router.callback_query(AlertForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first']))
async def process_alert_class(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор класса билета для оповещения и переходит к вводу максимальной цены
    """
    user_id = callback_query.from_user.id
    class_data = callback_query.data
    logger.info(f"Пользователь {user_id} выбрал класс билета для оповещения: {class_data}")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
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
    logger.info(f"Пользователь {user_id} выбрал класс билета: {class_type}")

    # Переходим к вводу максимальной цены
    await state.set_state(AlertForm.price)
    await bot.send_message(user_id, "Введите максимальную цену билета:")
    logger.info(f"Пользователь {user_id} переходит к вводу максимальной цены.")

@router.message(AlertForm.price)
async def process_price(message: Message, state: FSMContext):
    """
    Обрабатывает ввод максимальной цены билета и сохраняет оповещение
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит максимальную цену билета: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающую цену билета.")
        return

    try:
        price = float(text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (положительное число):")
        logger.warning(f"Пользователь {user_id} ввел некорректную цену билета: {text}")
        return

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date = data['date']
    class_type = data['class_type']

    subscription_id = add_subscription(user_id, origin, destination, date, class_type, price)

    if subscription_id:
        await message.answer(
            f"Оповещение успешно установлено! (ID {subscription_id})", reply_markup=main_menu_keyboard()
        )
        logger.info(
            f"Пользователь {user_id} установил оповещение: {origin} -> {destination}, {date}, {class_type}, {price} руб. (ID {subscription_id})"
        )
    else:
        await message.answer("Не удалось установить оповещение. Попробуйте позже.", reply_markup=main_menu_keyboard())
        logger.error(f"Не удалось установить оповещение для пользователя {user_id}.")

    await state.clear()

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback_query: CallbackQuery):
    """
    Обрабатывает нажатие кнопки "Мои оповещения": показывает список установленных оповещений
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Мои оповещения'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался посмотреть оповещения.")
        return

    await callback_query.answer()

    user_alerts = get_subscriptions(user_id)

    if not user_alerts:
        await bot.send_message(user_id, "У вас нет установленных оповещений.")
        logger.info(f"Пользователь {user_id} не имеет оповещений.")
        return

    response = "Ваши оповещения:\n"
    for alert in user_alerts:
        response += (
            f"ID: {alert['id']}\n"
            f"Маршрут: {alert['origin']} -> {alert['destination']}\n"
            f"Дата: {alert['date']}\n"
            f"Класс: {alert['class_type']}\n"
            f"Макс. цена: {alert['price']} руб.\n\n"
        )
    response += "Для удаления оповещения используйте команду:\n" \
                "/unsubscribe <id>\n" \
                "Например: /unsubscribe 123"
    await bot.send_message(user_id, response)
    logger.info(f"Пользователь {user_id} получил список своих оповещений.")

@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Удалить оповещение": переходит к вводу ID оповещения для удаления
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Удалить оповещение'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался удалить оповещение.")
        return

    await callback_query.answer()
    await state.set_state(DeleteAlertForm.alert_id)
    await bot.send_message(user_id, "Введите ID оповещения, которое хотите удалить:")
    logger.info(f"Пользователь {user_id} переходит к вводу ID оповещения для удаления.")

@router.message(DeleteAlertForm.alert_id)
async def process_delete_alert_id(message: Message, state: FSMContext):
    """
    Обрабатывает ввод ID оповещения для удаления
    """
    user_id = message.from_user.id
    alert_id_text = message.text.strip()
    logger.info(f"Пользователь {user_id} вводит ID оповещения для удаления: {alert_id_text}")

    if contains_forbidden_words(alert_id_text):
        await handle_inappropriate_input(message, state)
        return

    try:
        alert_id = int(alert_id_text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID (число).")
        logger.warning(f"Пользователь {user_id} ввел некорректный ID оповещения: {alert_id_text}")
        return

    success = remove_subscription(user_id, alert_id)

    if success:
        await message.answer("Оповещение успешно удалено.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} удалил оповещение ID {alert_id}.")
    else:
        await message.answer("Оповещение с таким ID не найдено или не принадлежит вам.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} попытался удалить несуществующее или чужое оповещение ID {alert_id}.")

    await state.clear()

@router.callback_query(F.data == "get_tickets")
async def cb_get_tickets(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Получить билеты": начинает сбор данных для поиска билетов
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} запросил список билетов.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался получить билеты.")
        return

    await callback_query.answer()
    await state.set_state(TicketSearchForm.origin)
    await bot.send_message(user_id, "Введите город отправления:")
    logger.info(f"Пользователь {user_id} переходит к вводу города отправления для поиска билетов.")

@router.message(TicketSearchForm.origin)
async def process_ticket_origin(message: Message, state: FSMContext):
    """
    Обрабатывает ввод города отправления для поиска билетов
    """
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"Пользователь {user_id} вводит город отправления для поиска билетов: {text}")

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город отправления для билетов.")
        return

    await state.update_data(origin=text)
    await state.set_state(TicketSearchForm.destination)
    await message.answer("Введите город назначения:")
    logger.info(f"Пользователь {user_id} установил город отправления для билетов: {text}")

@router.message(TicketSearchForm.destination)
async def process_ticket_destination(message: Message, state: FSMContext):
    """
    Обрабатывает ввод города назначения для поиска билетов
    """
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"Пользователь {user_id} вводит город назначения для билетов: {text}")

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город назначения для билетов.")
        return

    await state.update_data(destination=text)
    await state.set_state(TicketSearchForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")
    logger.info(f"Пользователь {user_id} установил город назначения для билетов: {text}")

@router.message(TicketSearchForm.date)
async def process_ticket_date(message: Message, state: FSMContext):
    """
    Обрабатывает ввод даты поездки для поиска билетов
    """
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"Пользователь {user_id} вводит дату поездки для билетов: {text}")

    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающую дату поездки для билетов.")
        return

    if not re.match(r'\d{2}\.\d{2}\.\d{4}', text):
        await message.answer("Некорректный формат даты. Пожалуйста, используйте ДД.ММ.ГГГГ:")
        logger.warning(f"Пользователь {user_id} ввел некорректный формат даты для билетов: {text}")
        return

    await state.update_data(date=text)
    await state.set_state(TicketSearchForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())
    logger.info(f"Пользователь {user_id} установил дату поездки для билетов: {text}")

@router.callback_query(TicketSearchForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first']))
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор класса билета для поиска
    """
    user_id = callback_query.from_user.id
    class_data = callback_query.data
    logger.info(f"Пользователь {user_id} выбрал класс билета для поиска: {class_data}")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота для поиска билетов.")
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
    logger.info(f"Пользователь {user_id} выбрал класс билета: {class_type}")

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date = data['date']

    routes = get_routes(origin, destination, date, class_type)

    if not routes:
        await bot.send_message(user_id, "Билеты не найдены.")
        logger.info(f"Для пользователя {user_id} не найдены билеты.")
    else:
        for route in routes:
            response = (
                f"Маршрут ID: {route['route_id']}\n"
                f"Маршрут: {route['station_from']} -> {route['station_to']}\n"
                f"Глобальный маршрут: {route['route_global']}\n"
                f"Дата: {route['date']}\n"
                f"Класс: {class_type}\n"
                f"Цена: {route['best_price']} руб.\n\n"
            )
            await bot.send_message(user_id, response, reply_markup=subscribe_button(route['route_id']))
            logger.info(f"Пользователь {user_id} получил маршрут ID {route['route_id']}.")

    await state.clear()

@router.callback_query(F.data.startswith("subscribe_"))
async def cb_subscribe_route(callback_query: CallbackQuery):
    """
    Обрабатывает подписку на выбранный маршрут
    """
    user_id = callback_query.from_user.id
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался подписаться на маршрут.")
        return

    try:
        route_id = int(callback_query.data.split("_")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Некорректный идентификатор маршрута.")
        logger.warning(f"Пользователь {user_id} передал некорректный route_id.")
        return

    subscription_id = add_subscription(user_id, route_id=route_id)

    if subscription_id:
        await callback_query.answer("Подписка успешно оформлена!")
        await bot.send_message(user_id, f"Вы подписались на маршрут ID {route_id}!", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} подписался на маршрут ID {route_id} с подпиской ID {subscription_id}.")
    else:
        await callback_query.answer("Не удалось оформить подписку.")
        logger.error(f"Не удалось оформить подписку для пользователя {user_id} на маршрут ID {route_id}.")

@router.callback_query(F.data == "my_subscriptions")
async def cb_my_subscriptions(callback_query: CallbackQuery):
    """
    Обрабатывает нажатие кнопки "Мои подписки": показывает список подписок пользователя
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Мои подписки'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался посмотреть подписки.")
        return

    await callback_query.answer()

    subscriptions = get_subscriptions(user_id)

    if not subscriptions:
        await bot.send_message(user_id, "У вас нет активных подписок.")
        logger.info(f"Пользователь {user_id} не имеет активных подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['subscription_id']}\n"
            f"Маршрут: {sub['route_global']}\n"
            f"Дата: {sub['date']}\n"
            f"Цена: {sub['best_price']} руб.\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <id>\n" \
                "Например: /unsubscribe 123"
    await bot.send_message(user_id, response)
    logger.info(f"Пользователь {user_id} получил список своих подписок.")

@router.message(Command('subscribe'))
async def subscribe_route(message: Message):
    """
    Обрабатывает команду /subscribe для подписки на маршрут по ID
    """
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался подписаться на маршрут через команду.")
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

    subscription_id = add_subscription(user_id, route_id=route_id, max_price=max_price)

    if subscription_id:
        await message.answer(f"Подписка успешно оформлена! (ID {subscription_id})")
        logger.info(f"Пользователь {user_id} подписался на маршрут ID {route_id} с максимальной ценой {max_price}. Подписка ID {subscription_id}.")
    else:
        await message.answer("Не удалось подписаться на маршрут. Возможно, маршрут не найден.")
        logger.warning(f"Пользователь {user_id} попытался подписаться на несуществующий маршрут ID {route_id}.")

@router.message(Command('unsubscribe'))
async def unsubscribe_route(message: Message):
    """
    Обрабатывает команду /unsubscribe для удаления подписки по ID
    """
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался удалить подписку через команду.")
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
        logger.info(f"Пользователь {user_id} удалил подписку ID {sub_id}.")
    else:
        await message.answer("Подписка с таким ID не найдена или не принадлежит вам.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} попытался удалить несуществующую или чужую подписку ID {sub_id}.")

@router.message(Command('subscriptions'))
async def list_subscriptions(message: Message):
    """
    Обрабатывает команду /subscriptions для вывода списка подписок
    """
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался посмотреть подписки через команду.")
        return

    subscriptions = get_subscriptions(user_id)
    if not subscriptions:
        await message.answer("У вас нет действующих подписок.")
        logger.info(f"Пользователь {user_id} не имеет подписок.")
        return

    response = "Ваши подписки:\n"
    for sub in subscriptions:
        response += (
            f"ID подписки: {sub['subscription_id']}\n"
            f"Маршрут: {sub['route_global']}\n"
            f"Дата: {sub['date']}\n"
            f"Цена: {sub['best_price']} руб.\n\n"
        )
    response += "Для удаления подписки используйте команду:\n" \
                "/unsubscribe <id>"
    await message.answer(response)
    logger.info(f"Пользователь {user_id} получил список своих подписок.")

async def scheduled_clean():
    """
    Периодически очищает старые подписки
    """
    while True:
        clean_old_subscriptions()
        logger.info("Периодическая очистка старых подписок выполнена.")
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
