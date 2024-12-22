import json

from src.db.database import engine, session
from src.db.models import (Base, City, Route, Station, Subscription, Ticket,
                           User, UserStatus)


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


def get_routes_subscribed():
    # ТУДУ добавить (айди, плюс достать старую стоимость)
    """получаем список уникальных айди маршрутов, которые находятся в таблице подписок"""
    try:
        result = session.query(Subscription.route_id).distinct().all()
        subscribed_routes_info = {}
        return [route_id[0] for route_id in result]
    except Exception:
        return []


def get_route_by_id(route_id: int):
    """получаем маршрут по его айди"""
    return session.query(Route).filter_by(route_id=route_id).first()


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
    from_date: str,
    to_date: str,
    train_no: str,
):
    """добавляем новый маршрут"""
    new_route = Route(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        from_date=from_date,
        to_date=to_date,
        train_no=train_no,
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


def add_ticket(route_id: int, class_name: str, best_price: int):
    """добавляем новую информацию по самому выгодному билету"""
    new_ticket = Ticket(route_id=route_id, class_name=class_name, best_price=best_price)
    # время добавления записи проставится автоматически см. models.Ticket
    session.add(new_ticket)
    session.commit()


def delete_ticket_by_id(ticket_id: int):
    """удаляем билет"""
    ticket = session.query(Ticket).filter_by(ticket_id=ticket_id).first()
    if ticket:
        session.delete(ticket)
        session.commit()
