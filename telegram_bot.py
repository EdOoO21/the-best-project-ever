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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)

dp = Dispatcher()
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

FORBIDDEN_WORDS = []
with open('input.txt', 'r', ) as f:
    for line in f:
        words = [word.strip() for word in line.rstrip().split(",")]
        FORBIDDEN_WORDS.extend(words)
logger.info("Запрещенные слова успешно загружены.")

alerts = {}  # временное хранилище оповещений
registered = set()
banned_users = set()

# TODO: подключение к базе данных и удалите временные хранилища

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
    await bot.send_message(user_id, "Введите город отправления:")
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
    await message.answer("Введите город назначения:")
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

    # TODO: Сохранение оповещения в базе данных

    # Заглушка
    if user_id not in alerts:
        alerts[user_id] = []
    alerts[user_id].append({
        "origin": origin,
        "destination": destination,
        "date": date,
        "class_type": class_type,
        "price": price
    })
    logger.info(f"Пользователь {user_id} установил оповещение: {origin} -> {destination}, {date}, {class_type}, {price} руб.")

    await message.answer("Оповещение успешно установлено!", reply_markup=main_menu_keyboard())
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
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

    await callback_query.answer()

    # TODO: Получение оповещений пользователя из базы данных

    # Заглушка
    user_alerts = alerts.get(user_id, [])

    if not user_alerts:
        await bot.send_message(user_id, "У вас нет установленных оповещений.")
        logger.info(f"Пользователь {user_id} не имеет оповещений.")
        return

    response = "Ваши оповещения:\n"
    for i, alert in enumerate(user_alerts, start=1):
        response += (
            f"{i}. Маршрут: {alert['origin']} -> {alert['destination']}\n"
            f"   Дата: {alert['date']}\n"
            f"   Класс: {alert['class_type']}\n"
            f"   Макс. цена: {alert['price']} руб.\n\n"
        )
    await bot.send_message(user_id, response)
    logger.info(f"Пользователь {user_id} получил список своих оповещений.")

@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery):
    """
    Обрабатывает нажатие кнопки "Удалить оповещение": удаляет все оповещения пользователя
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Удалить оповещение'.")
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return
    await callback_query.answer()

    # TODO: Удаление всех оповещений пользователя из базы данных

    # Заглушка
    if user_id in alerts and alerts[user_id]:
        del alerts[user_id]
        success = True
    else:
        success = False

    if success:
        await bot.send_message(user_id, "Все оповещения успешно удалены.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} удалил все оповещения.")
    else:
        await bot.send_message(user_id, "У вас нет оповещений для удаления.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} попытался удалить оповещения, но их нет.")

@router.callback_query(F.data == "get_tickets")
async def cb_get_tickets(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Получить билеты": начинает сбор данных для поиска билетов
    """
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} запросил список билетов.")
    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
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
    logger.info(f"Пользователь {user_id} вводит город отправления: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город отправления.")
        return

    await state.update_data(origin=text)
    await state.set_state(TicketSearchForm.destination)
    await message.answer("Введите город назначения:")
    logger.info(f"Пользователь {user_id} установил город отправления: {text}")

@router.message(TicketSearchForm.destination)
async def process_ticket_destination(message: Message, state: FSMContext):
    """
    Обрабатывает ввод города назначения для поиска билетов
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит город назначения: {message.text}")

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающий город назначения.")
        return

    await state.update_data(destination=text)
    await state.set_state(TicketSearchForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")
    logger.info(f"Пользователь {user_id} установил город назначения: {text}")

@router.message(TicketSearchForm.date)
async def process_ticket_date(message: Message, state: FSMContext):
    """
    Обрабатывает ввод даты поездки для поиска билетов
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
    await state.set_state(TicketSearchForm.class_type)
    await message.answer("Выберите класс билета:", reply_markup=ticket_options_keyboard())
    logger.info(f"Пользователь {user_id} установил дату поездки: {text}")

@router.callback_query(TicketSearchForm.class_type, F.data.in_(['ticket_econom', 'ticket_business', 'ticket_first']))
async def process_ticket_class(callback_query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор класса билета для поиска
    """
    user_id = callback_query.from_user.id
    class_data = callback_query.data
    logger.info(f"Пользователь {user_id} выбрал класс билета: {class_data}")

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

    # Получаем данные из состояния
    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date = data['date']
    class_type = data['class_type']

    # TODO: Получение списка билетов из базы данных на основе введенных данных

    # Заглушка
    tickets = [
        {"origin": origin, "destination": destination, "date": date, "class": class_type, "price": 1500.0},
        {"origin": origin, "destination": destination, "date": date, "class": class_type, "price": 2000.0},
    ]

    if not tickets:
        await bot.send_message(user_id, "Билеты не найдены.")
        logger.info(f"Для пользователя {user_id} не найдены билеты.")
    else:
        response = "Доступные билеты:\n"
        for ticket in tickets:
            response += (
                f"Маршрут: {ticket['origin']} -> {ticket['destination']}\n"
                f"Дата: {ticket['date']}\n"
                f"Класс: {ticket['class']}\n"
                f"Цена: {ticket['price']} руб.\n\n"
            )
        await bot.send_message(user_id, response)
        logger.info(f"Пользователь {user_id} получил список билетов.")

    await state.clear()

async def main():
    dp.include_router(router)

    # TODO: Запуск планировщика задач для проверки цен и отправки уведомлений

    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
