from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Получить билеты", callback_data="get_tickets"),
            ],
            
            [
                InlineKeyboardButton(text="Мои оповещения", callback_data="my_alerts"),
            ],
            [
                InlineKeyboardButton(text="Установить оповещение", callback_data="set_alert"),
            ],
        ]
    )
    return keyboard
