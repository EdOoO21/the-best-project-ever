from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def yes_no_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="set_subscription"),
                InlineKeyboardButton(text="Нет", callback_data="no_subscribtion")
            ]
        ]
    )

def subscribe_button(route_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подписаться на маршрут",
                    callback_data=f"subscribe_{route_id}"
                )
            ]
        ]
    )