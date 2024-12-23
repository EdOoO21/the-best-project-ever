from datetime import datetime

from bot.utils import notify_price_change
from src.core.rzd import get_train_routes_with_session
from src.db.queries import (delete_unvalid_routes,
                            get_route_with_tickets_by_id,
                            get_routes_subscribed)


async def update():
    delete_unvalid_routes()
    subscribed = get_routes_subscribed()
    for route_id in subscribed:
        obj = get_route_with_tickets_by_id(route_id=route_id)
        data = get_train_routes_with_session(
            obj["from_station_city"],
            obj["to_station_city"],
            obj["from_date"],
            place_type=obj["class_name"],
        )

        for route in data:
            if (
                route["station_code_from"] == obj["from_station"]
                and route["station_code_to"] == obj["to_station"]
                and route["class"] == obj["class_name"]
                and route["datetime0"] == obj["from_date"]
                and route["datetime1"] == obj["to_date"]
            ):

                if obj["best_price"] != route["best_price"]:
                    old_price = obj["best_price"]
                    new_price = route["best_price"]
                    await notify_price_change(bot, route_id, old_price, new_price)
