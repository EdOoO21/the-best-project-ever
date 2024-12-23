from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def ticket_options_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Плацкарт", callback_data="ticket_econom"),
                InlineKeyboardButton(text="Купе", callback_data="ticket_business"),
            ],
            [
                InlineKeyboardButton(text="СВ", callback_data="ticket_first"),
                InlineKeyboardButton(text="Сидячий", callback_data="ticket_seated"),
            ],
        ]
    )
    return keyboard
