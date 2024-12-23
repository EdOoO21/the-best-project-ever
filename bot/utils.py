import logging

from aiogram import Bot

from src.db.database import session
from src.db.models import Route
from src.db.queries import (get_route_with_tickets_by_id,
                            get_users_subscribed_to_route)

logger = logging.getLogger(__name__)


async def notify_price_change(bot: Bot, route_id: int, old_price: int, new_price: int):
    """
    Оповещает всех пользователей
    что цена изменилась
    """
    route = session.query(Route).filter_by(route_id=route_id).first()
    if not route:
        logger.warning(f"Не найден route_id={route_id} для оповещения о цене")
        return

    from_station_full = (
        f"{route.from_station.city.city_name} ({route.from_station.station_name})"
        if route.from_station and route.from_station.city
        else f"Станция ID {route.from_station_id}"
    )
    to_station_full = (
        f"{route.to_station.city.city_name} ({route.to_station.station_name})"
        if route.to_station and route.to_station.city
        else f"Станция ID {route.to_station_id}"
    )

    class_str = route.class_name.value
    text_msg = (
        f"ID: {route.train_no}\n"
        f"{from_station_full} -> {to_station_full}\n"
        f"Отправление: {route.from_date}\n"
        f"Прибытие: {route.to_date}\n"
        f"Класс: {class_str.capitalize()}\n"
        f"Старая цена: {old_price} руб.\n"
        f"Новая цена: {new_price} руб."
    )

    user_ids = get_users_subscribed_to_route(route_id)
    if not user_ids:
        logger.info(
            f"Нет подписчиков у route_id={route_id}, сообщение никому не отправляем."
        )
        return

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text_msg)
            logger.info(
                f"Уведомление отправлено user_id={uid} по маршруту #{route_id}."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление user_id={uid}: {e}")
