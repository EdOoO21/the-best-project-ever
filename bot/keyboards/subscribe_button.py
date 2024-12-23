from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscribe_button(index: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подписаться на маршрут", callback_data=f"subscribe_{index}"
                )
            ]
        ]
    )
