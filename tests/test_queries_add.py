import unittest
from unittest.mock import patch
from datetime import datetime
from src.db.queries import add_city, add_station, add_route, add_user, add_subscription, add_ticket, load_cities_from_json
from src.db.models import City, Station, Route, User, Subscription, Ticket
from src.db.database import session

class TestAddFunctions(unittest.TestCase):
    def test_add_city(self):
        add_city(city_name="пупупу", city_id=11111)

        city = session.query(City).filter_by(city_id=11111).first()
        self.assertIsNotNone(city)
        self.assertEqual(city.city_name, "пупупу")

    def test_add_station_with_existed_city(self):
        add_station(station_name="у черта на куличиках", station_id=3933, city_id=2060533)
        station = session.query(Station).filter_by(station_id=3933).first()
        self.assertIsNotNone(station)
        self.assertEqual(station.station_name, "у черта на куличиках")
        self.assertEqual(station.city_id, 2060533)
    
    # def test_add_station_with_unexisted_city(self):
    #     add_station(station_name="у черта на куличиках", station_id=3933, city_id=101)
    #     station = session.query(Station).filter_by(station_id=3933).first()

    #     self.assertIsNotNone(station)
    #     self.assertEqual(station.station_name, "у черта на куличиках")
    #     self.assertEqual(station.city_id, 2060533)

    def test_add_route(self):
        add_station(station_name="пупупу", station_id=58858, city_id=2010359)
        add_station(station_name="у черта на куличиках", station_id=3933, city_id=2060533)

        route_id = add_route(
            from_station_id=58858,
            from_date=datetime(2024, 6, 19, 9, 14, 10),
            to_station_id=3933,
            to_date=datetime(2024, 7, 23, 7, 34, 11),
            train_no="ЪЫЪ",
            class_name="купе",
        )

        route = session.query(Route).filter_by(route_id=route_id).first()
        self.assertIsNotNone(route)
        self.assertEqual(route.train_no, "ЪЫЪ")
        self.assertEqual(route.class_name.value, "купе")
        self.assertEqual(route.from_station_id, 58858)
        self.assertEqual(route.from_date, datetime(2024, 6, 19, 9, 14, 10))
        self.assertEqual(route.to_station_id, 3933)
        self.assertEqual(route.to_date, datetime(2024, 7, 23, 7, 34, 11))
