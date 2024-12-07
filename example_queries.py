import src.queries as q
from datetime import datetime

q.create_tables()
q.load_cities_from_json("./docs/city_codes.json")

# перед добавлением маршрута в базу ВСЕГДА надо сначала проверить, что станции есть в базе, и если нет, то добавить (инфу из апи)
# надо еще подумать как это по красивому делать. через flush ли?
q.add_station(station_name="пупупу", station_id=58858, city_id=2010359)
q.add_station(station_name="у черта на куличиках", station_id=3933, city_id=2060533)

# функция добавления маршрута возвращает сразу айдишник полученного маршрута
added_route_id = q.add_route(from_station_id=58858, from_date=datetime(2024, 6, 19, 9, 14, 10), to_station_id=3933, to_date=datetime(2024, 7, 23, 7, 34, 11), train_no=None)

q.add_user(user_id=19999)
q.add_subscription(user_id=19999, route_id=added_route_id)

print(*q.get_routes_subscribed())  # >> 1  как раз маршрут добавленный с номером 1