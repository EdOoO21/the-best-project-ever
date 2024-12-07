from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from datetime import datetime

from database import engine

Base = declarative_base()

class City(Base):
    """модель таблички городов"""
    __tablename__ = "t_city"

    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(25), nullable=False)

    # связь со станциями - станции в этом населенном пункте
    stations = relationship("Station", back_populates="city")


class Station(Base):
    """модель таблички станций/вокзалов"""
    __table_args__ = {'extend_existing': True}
    __tablename__ = "t_station"

    station_id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey('t_city.city_id'), nullable=False)
    # каждая станция в каком-то населенном пункте
    station_name = Column(String(100), nullable=False)

    # связь с городом - город, в котором находится станция
    city = relationship("City", back_populates="stations")
    # связь с маршрутами - маршуты из этой станции
    from_routes = relationship("Route", back_populates="from_station", foreign_keys="Route.from_station_id")
    # связь с маршрутами - маршруты в эту станцию
    to_routes = relationship("Route", back_populates="to_station", foreign_keys="Route.to_station_id")


class Route(Base):
    """модель таблички маршрутов поездов"""
    __table_args__ = {'extend_existing': True}
    __tablebname__= "t_route"

    route_id = Column(Integer, primary_key=True)
    from_station_id = Column(Integer, ForeignKey('t_station.station_id'), nullable=False)
    from_date = Column(DateTime, nullable=False)
    to_station_id = Column(Integer, ForeignKey('t_station.station_id'), nullable=False)
    to_date = Column(DateTime, nullable=False)
    train_no = Column(String(25))

    # связь с станциями - станция отправления
    from_station = relationship("Company", foreign_keys=[from_station_id], back_populates="from_routes")
    # связь с станциями - станция прибытия
    to_station = relationship("Company", foreign_keys=[to_station_id], back_populates="to_routes")
    # cвязь с юзерами - юзеры, которые следят за этим маршрутом
    users = relationship('User', secondary="t_subscription", back_populates='subscriptions')
    # связь с билетами - все стоимости для этого маршрута, которые когда-либо были 
    tickets = relationship("Ticket", back_populates="route", foreign_keys="Ticket.ticket_id")


class User(Base):
    """таблица пользователей бота"""
    __table_args__ = {'extend_existing': True}
    __tablename__ = "t_user"

    id = Column(Integer, primary_key=True)
    # статус юзера, пока 0 - обычный, 1 - забаненый
    status = Column(SmallInteger)

    # связь с маршрутами - все подписки пользователя
    subscriptions = relationship('Route', secondary="t_subscription", back_populates='subscribers')


class Subscription(Base):
    """ассоциативная таблица с маршрутами, за которыми следят пользователи"""
    __table_args__ = {'extend_existing': True}
    __tablename__ = 't_subscription'

    user_id = Column(Integer, ForeignKey('t_user.user_id'), primary_key=True)
    route_id = Column(Integer, ForeignKey('t_route.route_id'), primary_key=True)


class Ticket(Base):
    """табличка со стоимостями билетов для маршрутов"""
    __tablename__ = "t_ticket"
    __table_args__ = {'extend_existing': True}

    ticket_id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("t_route.route_id"), nullable=False)
    class_name = Column(String(10), nullable=False)
    best_price = Column(Integer, nullable=False, )
    update_time = Column(DateTime, nullable=False)

    # связь с маршрутами - маршут, к которому относится билет 
    route = relationship("Route", back_populates="tickets", foreign_keys="Route.route_id")


#ТЕСТ

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

station1 = Station(name='Станция 1')
station2 = Station(name='Станция 2')
route1 = Route(departure_station=station1, arrival_station=station2)

session.add(station1)
session.add(station2)
session.add(route1)
session.commit()


