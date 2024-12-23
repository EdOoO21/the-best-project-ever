import enum

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Integer, String,
                        text)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class City(Base):
    """модель таблички городов"""

    __tablename__ = "t_city"
    __table_args__ = {"extend_existing": True}

    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(50), nullable=False)

    # связь со станциями - станции в этом населенном пункте
    stations = relationship("Station", back_populates="city")


class Station(Base):
    """модель таблички станций/вокзалов"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "t_station"

    station_id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("t_city.city_id"), nullable=False)
    # каждая станция в каком-то населенном пункте
    station_name = Column(String(100), nullable=False)

    # связь с городом - город, в котором находится станция
    city = relationship("City", back_populates="stations")
    # связь с маршрутами - маршуты из этой станции
    from_routes = relationship(
        "Route", back_populates="from_station", foreign_keys="Route.from_station_id"
    )
    # связь с маршрутами - маршруты в эту станцию
    to_routes = relationship(
        "Route", back_populates="to_station", foreign_keys="Route.to_station_id"
    )


class RouteType(enum.Enum):
    """я хз как это на английский переводится вот честное слово)))"""
    plackart = "плацкарт"
    cupe = "купе"
    seated = "сидячий"
    sv = "св"


class Route(Base):
    """модель таблички маршрутов поездов"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "t_route"

    route_id = Column(Integer, primary_key=True, autoincrement=True)
    from_station_id = Column(
        Integer, ForeignKey("t_station.station_id"), nullable=False
    )
    from_date = Column(DateTime, nullable=False)
    to_station_id = Column(Integer, ForeignKey("t_station.station_id"), nullable=False)
    to_date = Column(DateTime, nullable=False)
    train_no = Column(String(25))
    class_name = Column(Enum(RouteType), nullable=False)

    # связь с станциями - станция отправления
    from_station = relationship(
        "Station", foreign_keys=[from_station_id], back_populates="from_routes"
    )
    # связь с станциями - станция прибытия
    to_station = relationship(
        "Station", foreign_keys=[to_station_id], back_populates="to_routes"
    )
    # cвязь с юзерами - юзеры, которые следят за этим маршрутом
    users = relationship(
        "User", secondary="t_subscription", back_populates="subscriptions"
    )
    # связь с билетами - все стоимости для этого маршрута, которые когда-либо были + сортируем в порядке возрастания стоимости
    tickets = relationship(
        "Ticket",
        back_populates="route",
        foreign_keys="Ticket.route_id",
        order_by="Ticket.best_price.asc()",
    )

    def __str__(self) -> str:
        return f"route_id {self.route_id}: {self.from_station.station_name} {self.from_date} -> {self.to_station.station_name} {self.to_date}"


class UserStatus(enum.Enum):
    banned = "banned"
    chill = "chill"


class User(Base):
    """таблица пользователей бота"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "t_user"

    user_id = Column(Integer, primary_key=True)
    # статус юзера
    status = Column(Enum(UserStatus), nullable=False)

    # связь с маршрутами - все подписки пользователя
    subscriptions = relationship(
        "Route", secondary="t_subscription", back_populates="users"
    )


class Subscription(Base):
    """ассоциативная таблица с маршрутами, за которыми следят пользователи"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "t_subscription"

    user_id = Column(Integer, ForeignKey("t_user.user_id"), primary_key=True)
    route_id = Column(Integer, ForeignKey("t_route.route_id"), primary_key=True)

    # связь с юзерами - юзер, который следит за этим маршрутом
    user = relationship("User", back_populates="subscriptions")
    # связь с маршрутами - маршут, за которым следит юзер
    route = relationship("Route", back_populates="users")


class Ticket(Base):
    """табличка со стоимостью билетов для маршрутов"""

    __tablename__ = "t_ticket"
    __table_args__ = {"extend_existing": True}

    ticket_id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("t_route.route_id"), nullable=False)
    best_price = Column(
        Integer,
        nullable=False,
    )
    update_time = Column(
        DateTime, nullable=False, server_default=text("TIMEZONE('utc', now())")
    )  # постгрес автоматически подставит время получения инфы

    # связь с маршрутами - маршут, к которому относится билет
    route = relationship(
        "Route", back_populates="tickets", foreign_keys="Ticket.route_id"
    )

    def __str__(self):
        return f"--------- ticket_id {self.ticket_id}, for route_id {self.route_id}, {self.route.class_name.value}, {self.best_price} rub, updated: {self.update_time} \n"

    def __repr__(self):
        return f"--------- ticket_id {self.ticket_id}, for route_id {self.route_id}, {self.route.class_name.value}, {self.best_price} rub, updated: {self.update_time} \n"
