from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("Установить оповещение", callback_data="set_alert"),
                InlineKeyboardButton("Мои оповещения", callback_data="my_alerts"),
            ],
            [
                InlineKeyboardButton("Удалить оповещение", callback_data="delete_alert"),
            ],
            [
                InlineKeyboardButton("Получить билеты", callback_data="get_tickets"),
            ],
            [
                InlineKeyboardButton("Мои подписки", callback_data="my_subscriptions"),
            ],
        ]
    )
    return keyboard
