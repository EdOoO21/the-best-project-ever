from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def ticket_options_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("Плацкарт", callback_data="ticket_econom"),
                InlineKeyboardButton("Купе", callback_data="ticket_business"),
            ],
            [
                InlineKeyboardButton("СВ", callback_data="ticket_first"),
                InlineKeyboardButton("Сидячий", callback_data="ticket_seated"),
            ],
        ]
    )
    return keyboard