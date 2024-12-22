from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Установить оповещение", callback_data="set_alert"),
                InlineKeyboardButton(text="Мои оповещения", callback_data="my_alerts"),
            ],
            [
                InlineKeyboardButton(text="Удалить оповещение", callback_data="delete_alert"),
            ],
            [
                InlineKeyboardButton(text="Получить билеты", callback_data="get_tickets"),
            ],
            [
                InlineKeyboardButton(text="Мои подписки", callback_data="my_subscriptions"),
            ],
        ]
    )
    return keyboard
