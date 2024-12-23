import json
from datetime import datetime

from sqlalchemy import text 

from src.db.database import engine, session
from src.db.models import (Base, City, Route, Station, Subscription, Ticket,
                           RouteType, User, UserStatus)


def create_tables():
    Base.metadata.drop_all(engine)
    engine.echo = False
    Base.metadata.create_all(engine)
    engine.echo = True

def load_cities_from_json(file_path: str):
    """загружаем населенные пункты России в базу из city_codes.json"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        for city_name in data:
            city_id = int(data.get(city_name))
            new_city = City(city_id=city_id, city_name=city_name)
            session.add(new_city)

        session.commit()

def check_user_is_banned(user_id: int) -> bool | None:
    """проверяем статус пользователя"""
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        return user.status == UserStatus.banned
    raise Exception(f"Пользователь c ID {user_id} не найден")

def get_city_code(city_name) -> int:
    """получает код города по названию"""
    city_name = city_name.lower()

    city_precise = session.query(City).filter(City.city_name == city_name).first()

    # сначала точное совпадение
    if city_precise:
        return city_precise.city_id  
    
    city = session.query(City).filter(City.city_name.like(f"{city_name}%")).order_by(City.city_name.asc()).first()

    # если нет точного совпадения, то берем первый по алфавиту из похожих
    if city:
        return city.city_id
    
    raise ValueError("Город/станция не найдены")

def delete_unvalid_routes():
    """удаляет все подписки поезда которых уже ушли (т.е. дата маршрута прошла)"""
    routes = session.query(Route).filter(Route.from_date >= text("TIMEZONE('utc', now())")).all()
    if routes:
        # удаляем все подписки с прошедшедшими датами, а также все маршруты из этих подписок
        session.query(Subscription).filter(Subscription.route_id in [route.route_id for route in routes]).delete(
            synchronize_session=False
        )
        # удаляем все билеты с прошедшедшими датами, а также все маршруты из этих подписок
        session.query(Ticket).filter(Ticket.route.route.route_id in [route.route_id for route in routes]).delete(
            synchronize_session=False
        )
        # наконец все маршруты удаляем
        session.delete(routes)
        session.commit()
    return []

def get_routes_subscribed() -> list:
    """получаем список уникальных айди маршрутов, которые находятся в таблице подписок"""
    routes = session.query(Subscription.route_id).distinct().all()
    if routes:
        return [route_id[0] for route_id in routes]
    return []

def get_route_with_tickets_by_id(route_id: int) -> dict:
    """получаем маршрут (его данные + последнюю стоимость из собранных "билетов") по его айди"""
    result = {
        "route_id": None,
        "from_station": None,
        "to_station": None,
        "from_date": None,
        "to_date": None,
        "train_no": None,
        "class_name": None,
        "best_price": None
    }

    route = session.query(Route).filter_by(route_id=route_id).first()
    if route:
        result["route_id"] = route.route_id
        result["from_station"] = route.from_station.station_id
        result["from_station_city"] = route.from_station.city.city_id
        result["to_station"] = route.to_station.station_id
        result["to_station_city"] = route.to_station.city.city_id
        result["from_date"] = route.from_date
        result["to_date"] = route.to_date
        result["train_no"] = route.train_no

        # получили самый последний по времени обновления билет с таким маршрутом
        last_ticket = session.query(Ticket).filter_by(route_id=route_id).order_by(Ticket.update_time.desc()).first()

        if last_ticket:
            result["class_name"] = last_ticket.route.class_name.value
            result["best_price"] = last_ticket.best_price

    return result

def add_city(city_name: str, city_id: int):
    """загружаем город"""
    new_city = City(city_id=city_id, city_name=city_name)
    session.add(new_city)
    session.commit()

def add_station(city_id: int, station_id: int, station_name: str):
    """загружаем станцию"""
    new_station = Station(
        city_id=city_id, station_name=station_name, station_id=station_id
    )
    session.add(new_station)
    session.commit()

def add_route(
    from_station_id: int,
    to_station_id: int,
    from_date: datetime.datetime,
    to_date: datetime.datetime,
    train_no: str,
    class_name: str,
) -> int:
    """добавляем новый маршрут"""
    if class_name == "плацкарт":
        class_name = RouteType.plackart
    elif class_name == "купе":
        class_name = RouteType.cupe
    elif class_name == "сидячий":
        class_name = RouteType.seated
    elif class_name == "св":
        class_name = RouteType.sv
    else:
        raise Exception("Неправильно указан класс поезда (не \"купе\", \"плацкарт\", \"св\" или \"сидячий\")")

    new_route = Route(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        from_date=from_date,
        to_date=to_date,
        train_no=train_no,
        class_name=class_name
    )
    session.add(new_route)
    session.commit()
    return new_route.route_id

def delete_route(route_id: int):
    """удаляем маршрут"""
    route = session.query(Route).filter_by(route_id=route_id).first()
    if route:
        # удаляем все подписки с таким маршрутом
        session.query(Subscription).filter_by(route_id=route_id).delete(
            synchronize_session=False
        )
        session.delete(route)
        session.commit()

def add_user(user_id: int, status=UserStatus.chill):
    """добавляем пользователя"""
    new_user = User(user_id=user_id, status=status)
    session.add(new_user)
    session.commit()

def update_user(user_id: int, new_status: str):
    """обновляем статус пользователя, например, если его заблочили (в этом случае еще и удаляем все подписки)"""
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.status = new_status
        if new_status == "banned":
            # удаляем все подписки
            session.query(Subscription).filter_by(user_id=user_id).delete(
                synchronize_session=False
            )
        session.commit()
    raise Exception(f"Пользователь c ID {user_id} не найден")

def delete_user(user_id: int):
    """удаляем пользователя"""
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        # удаляем все подписки юзера
        session.query(Subscription).filter_by(user_id=user_id).delete(
            synchronize_session=False
        )
        session.delete(user)
        session.commit()

def add_subscription(user_id: int, route_id: int):
    """добавляем пользователю новую подписку"""
    new_subscription = Subscription(user_id=user_id, route_id=route_id)
    session.add(new_subscription)
    session.commit()

def delete_subscription(user_id: int, route_id: int):
    """удаляем подписку пользователя"""
    subscription = (
        session.query(Subscription)
        .filter_by(user_id=user_id, route_id=route_id)
        .first()
    )
    if subscription:
        session.delete(subscription)
        session.commit()

def add_ticket(route_id: int, best_price: int):
    """добавляем новую информацию по самому выгодному билету"""
    new_ticket = Ticket(route_id=route_id, best_price=best_price)
    # время добавления записи проставится автоматически см. models.Ticket
    session.add(new_ticket)
    session.commit()

def delete_ticket_by_id(ticket_id: int):
    """удаляем билет"""
    ticket = session.query(Ticket).filter_by(ticket_id=ticket_id).first()
    if ticket:
        session.delete(ticket)
        session.commit()
