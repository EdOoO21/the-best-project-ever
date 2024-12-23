from src.core.rzd import get_train_routes_with_session
from src.db.queries import get_route_with_tickets_by_id, get_routes_subscribed, delete_unvalid_routes
from datetime import datetime

def update():
    delete_unvalid_routes()
    subscribed = get_routes_subscribed()
    for route_id in subscribed:
        obj = get_route_with_tickets_by_id(route_id=route_id)
        data = get_train_routes_with_session(obj["from_station_city"], \
                                                obj["to_station_city"], \
                                                    obj["from_date"], \
                                                        place_type = obj["class_name"])

        for route in data:
            if route["station_code_from"] == obj["from_station"] \
            and route["station_code_to"] == obj["to_station"] \
            and route["class"] == obj["class_name"] \
            and route["datetime0"] == obj["from_date"] \
            and route["datetime1"] == obj["to_date"]:

                if obj["best_price"] != route["best_price"]:
                    pass
