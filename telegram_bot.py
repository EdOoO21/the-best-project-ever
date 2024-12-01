import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

TOKEN = '7694466685:AAF28AYYL9LA6BboWipzM51JZVeF0qv0DPM'

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()


class AlertForm(StatesGroup):
    origin = State()
    destination = State()
    date = State()
    price = State()


alerts = {} # надеюсь временное хранилище для алертов


@router.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать! Я помогу вам отслеживать цены на билеты.\n\n"
        "Доступные команды:\n"
        "/set_alert - Установить новое оповещение\n"
        "/my_alerts - Просмотреть ваши оповещения\n"
        "/delete_alert - Удалить оповещение"
    )


@router.message(Command('set_alert'))
async def cmd_set_alert(message: types.Message, state: FSMContext):
    await state.set_state(AlertForm.origin)
    await message.answer("Введите город отправления:")


@router.message(AlertForm.origin)
async def process_origin(message: types.Message, state: FSMContext):
    await state.update_data(origin=message.text)
    await state.set_state(AlertForm.destination)
    await message.answer("Введите город назначения:")


@router.message(AlertForm.destination)
async def process_destination(message: types.Message, state: FSMContext):
    await state.update_data(destination=message.text)
    await state.set_state(AlertForm.date)
    await message.answer("Введите дату поездки в формате ДД.ММ.ГГГГ:")


@router.message(AlertForm.date)
async def process_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(AlertForm.price)
    await message.answer("Введите максимальную цену билета:")


@router.message(AlertForm.price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену:")
        return
    data = await state.get_data()

    user_id = message.from_user.id
    if user_id not in alerts:
        alerts[user_id] = []
    alerts[user_id].append({
        "origin": data['origin'],
        "destination": data['destination'],
        "date": data['date'],
        "price": price
    })

    await message.answer("Оповещение успешно установлено!")
    await state.clear()


@router.message(Command('my_alerts'))
async def cmd_my_alerts(message: types.Message):
    user_id = message.from_user.id
    user_alerts = alerts.get(user_id, [])

    if not user_alerts:
        await message.answer("У вас нет установленных оповещений.")
        return

    response = "Ваши оповещения:\n"
    for i, alert in enumerate(user_alerts, start=1):
        response += (
            f"{i}. Маршрут: {alert['origin']} -> {alert['destination']}\n"
            f"   Дата: {alert['date']}\n"
            f"   Макс. цена: {alert['price']} руб.\n\n"
        )
    await message.answer(response)


@router.message(Command('delete_alert'))
async def cmd_delete_alert(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_alerts = alerts.get(user_id, [])

    if not user_alerts:
        await message.answer("У вас нет оповещений для удаления.")
        return

    removed_alert = user_alerts.pop()
    await message.answer(f"Оповещение {removed_alert} удалено.")
    await state.clear()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
