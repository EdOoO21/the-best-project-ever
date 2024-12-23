import unittest
from unittest.mock import patch, MagicMock
from src.db.queries import add_city, add_station, add_route, add_user, add_subscription, add_ticket
from src.db.models import City, Station, Route, User, Subscription, Ticket

class TestAddFunctions(unittest.TestCase):

    @patch('src.db.queries.session')
    def test_add_city(self, mock_session):
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.add = MagicMock()
        city_name = "Москва"
        city_id = 1

        # Act
        add_city(city_name, city_id)

        # Assert
        mock_session.add.assert_called_once_with(City(city_id=city_id, city_name=city_name))
        mock_session.commit.assert_called_once()

    @patch('src.db.queries.session')
    def test_add_station(self, mock_session):
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.add = MagicMock()
        city_id = 1
        station_id = 1
        station_name = "Станция 1"

        # Act
        add_station(city_id, station_id, station_name)

        # Assert
        mock_session.add.assert_called_once_with(Station(city_id=city_id, station_name=station_name, station_id=station_id))
        mock_session.commit.assert_called_once()

    @patch('src.db.queries.session')
    def test_add_route(self, mock_session):
        # Arrange
        mock_session.add = MagicMock()
        from_station_id = 1
        to_station_id = 2
        from_date = "2023-10-01 10:00:00"
        to_date = "2023-10-01 12:00:00"
        train_no = "123"
        class_name = "купе"

        # Act
        route_id = add_route(from_station_id, to_station_id, from_date, to_date, train_no, class_name)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch('src.db.queries.session')
    def test_add_user(self, mock_session):
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.add = MagicMock()
        user_id = 1
        status = "chill"

        # Act
        add_user(user_id, status)

        # Assert
        mock_session.add.assert_called_once_with(User(user_id=user_id, status=status))
        mock_session.commit.assert_called_once()

    @patch('src.db.queries.session')
    def test_add_subscription(self, mock_session):
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.add = MagicMock()
        user_id = 1
        route_id = 1

        # Act
        add_subscription(user_id, route_id)

        # Assert
        mock_session.add.assert_called_once_with(Subscription(user_id=user_id, route_id=route_id))
        mock_session.commit.assert_called_once()

    @patch('src.db.queries.session')
    def test_add_ticket(self, mock_session):
        # Arrange
        mock_session.add = MagicMock()
        route_id = 1
        best_price = 100

        # Act
        add_ticket(route_id, best_price)

        # Assert
        mock_session.add.assert_called_once_with(Ticket(route_id=route_id, best_price=best_price))
        mock_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
