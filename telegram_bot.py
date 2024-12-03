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
storage = MemoryStorage()
dp = Dispatcher()
router = Router()
class AlertForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    price = State()

FORBIDDEN_WORDS = []
try:
    with open('input.txt', 'r') as f:
        for line in f:
            words = [word.strip() for word in line.rstrip().split(",")]
            FORBIDDEN_WORDS.extend(words)
except FileNotFoundError:
    logger.error("Файл input.txt не найден. Убедитесь, что файл существует.")
    FORBIDDEN_WORDS = []

alerts = {}
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
            InlineKeyboardButton(text="Выбрать билет", callback_data="select_ticket"),
            InlineKeyboardButton(text="Выбрать услугу", callback_data="select_service")
        ]
    ])
    return keyboard

def ticket_options_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Эконом", callback_data="ticket_econom"),
            InlineKeyboardButton(text="Бизнес", callback_data="ticket_business")
        ],
        [
            InlineKeyboardButton(text="Первый класс", callback_data="ticket_first")
        ]
    ])
    return keyboard

def service_options_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Дополнительный багаж", callback_data="service_baggage"),
            InlineKeyboardButton(text="Страховка", callback_data="service_insurance")
        ],
        [
            InlineKeyboardButton(text="VIP-зал ожидания", callback_data="service_vip")
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
    logger.info(f"Получена команда /start от пользователя {user_id}.")

    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался использовать бота.")
        return

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
    await bot.send_message(user_id, "Введите город отправления:")
    logger.info(f"Пользователь {user_id} переходит к вводу города отправления.")

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Мои оповещения'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался просмотреть оповещения.")
        return

    await callback_query.answer()
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
            f"   Макс. цена: {alert['price']} руб.\n\n"
        )
    await bot.send_message(user_id, response)
    logger.info(f"Пользователь {user_id} получил список своих оповещений.")

@router.message(AlertForm.origin)
async def process_origin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит город отправления: {message.text}")

    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

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
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит город назначения: {message.text}")

    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

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
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит дату поездки: {message.text}")

    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

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
    await state.set_state(AlertForm.price)
    await message.answer("Введите максимальную цену билета:")
    logger.info(f"Пользователь {user_id} установил дату поездки: {text}")

@router.message(AlertForm.price)
async def process_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} вводит максимальную цену билета: {message.text}")

    if user_id in banned_users:
        await message.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался установить оповещение.")
        return

    text = message.text.strip()
    if contains_forbidden_words(text):
        await handle_inappropriate_input(message, state)
        logger.warning(f"Пользователь {user_id} ввел неподобающую цену билета.")
        return

    try:
        price = int(text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (положительное целое число):")
        logger.warning(f"Пользователь {user_id} ввел некорректную цену билета: {text}")
        return

    data = await state.get_data()
    origin = data['origin']
    destination = data['destination']
    date = data['date']

    if user_id not in alerts:
        alerts[user_id] = []
    alerts[user_id].append({
        "origin": origin,
        "destination": destination,
        "date": date,
        "price": price
    })

    await message.answer("Оповещение успешно установлено!", reply_markup=main_menu_keyboard())
    logger.info(f"Пользователь {user_id} установил оповещение: {origin} -> {destination}, {date}, {price} руб.")
    await state.clear()

@router.callback_query(F.data == "delete_alert")
async def cb_delete_alert(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Удалить оповещение'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался удалить оповещения.")
        return

    await callback_query.answer()

    if user_id in alerts and alerts[user_id]:
        del alerts[user_id]
        await bot.send_message(user_id, "Все оповещения успешно удалены.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} удалил все оповещения.")
    else:
        await bot.send_message(user_id, "У вас нет оповещений для удаления.", reply_markup=main_menu_keyboard())
        logger.info(f"Пользователь {user_id} попытался удалить оповещения, но их нет.")

@router.callback_query(F.data == "select_ticket")
async def cb_select_ticket(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Выбрать билет'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать билет.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Выберите тип билета:", reply_markup=ticket_options_keyboard())
    logger.info(f"Пользователю {user_id} отправлена клавиатура выбора типа билета.")

@router.callback_query(F.data == "select_service")
async def cb_select_service(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} нажал кнопку 'Выбрать услугу'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать услугу.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Выберите услугу:", reply_markup=service_options_keyboard())
    logger.info(f"Пользователю {user_id} отправлена клавиатура выбора услуги.")

@router.callback_query(F.data == "ticket_econom")
async def cb_ticket_econom(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал билет в плацкарт.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать билет.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали билет в плацкарт.")
    logger.info(f"Пользователю {user_id} подтвержден выбор билета в плацкарт.")

@router.callback_query(F.data == "ticket_business")
async def cb_ticket_business(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал билет купе.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать билет.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали билет купе.")
    logger.info(f"Пользователю {user_id} подтвержден выбор билета купе.")

@router.callback_query(F.data == "ticket_first")
async def cb_ticket_first(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал билеты СВ класса.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать билет.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали билеты СВ класса.")
    logger.info(f"Пользователю {user_id} подтвержден выбор билетов СВ класса.")

@router.callback_query(F.data == "service_baggage")
async def cb_service_baggage(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал услугу 'Дополнительный багаж'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать услугу.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали дополнительный багаж.")
    logger.info(f"Пользователю {user_id} подтверждена услуга 'Дополнительный багаж'.")

@router.callback_query(F.data == "service_insurance")
async def cb_service_insurance(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал услугу 'Страховка'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать услугу.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали страховку.")
    logger.info(f"Пользователю {user_id} подтверждена услуга 'Страховка'.")

@router.callback_query(F.data == "service_vip")
async def cb_service_vip(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"Пользователь {user_id} выбрал услугу 'VIP-зал ожидания'.")

    if user_id in banned_users:
        await callback_query.answer("Вы заблокированы и не можете использовать этого бота.")
        logger.info(f"Блокированный пользователь {user_id} попытался выбрать услугу.")
        return

    await callback_query.answer()
    await bot.send_message(user_id, "Вы выбрали VIP-зал ожидания.")
    logger.info(f"Пользователю {user_id} подтверждена услуга 'VIP-зал ожидания'.")

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
