from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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