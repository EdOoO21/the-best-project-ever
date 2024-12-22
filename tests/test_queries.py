import unittest
from unittest.mock import MagicMock, patch

from src.db.queries import (add_city, add_route, add_station, add_subscription,
                            add_ticket, add_user, delete_route,
                            delete_subscription, delete_ticket_by_id,
                            delete_user, update_user)


class TestDatabaseQueries(unittest.TestCase):

    # @patch('bot.config.settings')
    @patch("src.queries.session")
    def test_add_city(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_city(city_name="караганда", city_id=1)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_add_station(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_city(city_name="караганда", city_id=1)
        add_station(city_id=1, station_id=1, station_name="у черта на куличиках")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_add_route(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_city(city_name="караганда", city_id=1)
        add_station(station_name="пупупу", station_id=1, city_id=1)

        add_city(city_name="мухосранск", city_id=2)
        add_station(station_name="у черта на куличиках", station_id=2, city_id=2)

        route_id = add_route(
            from_station_id=1,
            to_station_id=2,
            from_date="2024-12-24 10:00:00",
            to_date="2024-12-25 12:00:00",
            train_no="666",
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        self.assertIsNotNone(route_id)

    @patch("src.queries.session")
    def test_delete_route(self, mock_session):
        mock_route = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_route
        )
        mock_session.query.return_value.filter_by.return_value.delete = MagicMock()
        mock_session.delete = MagicMock()
        mock_session.commit = MagicMock()

        delete_route(1)

        mock_session.query.return_value.filter_by.return_value.first.assert_called_once()
        mock_session.query.return_value.filter_by.return_value.delete.assert_called_once()
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_add_user(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_user(1)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_update_user(self, mock_session):
        mock_user = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )
        mock_session.commit = MagicMock()

        update_user(1, "banned")

        mock_session.query.return_value.filter_by.return_value.first.assert_called_once()
        self.assertEqual(mock_user.status, "banned")
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_delete_user(self, mock_session):
        mock_user = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )
        mock_session.query.return_value.filter_by.return_value.delete = MagicMock()
        mock_session.delete = MagicMock()
        mock_session.commit = MagicMock()

        delete_user(1)

        mock_session.query.return_value.filter_by.return_value.first.assert_called_once()
        mock_session.query.return_value.filter_by.return_value.delete.assert_called_once()
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_add_subscription(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_subscription(1, 1)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_delete_subscription(self, mock_session):
        mock_subscription = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_subscription
        )
        mock_session.delete = MagicMock()
        mock_session.commit = MagicMock()

        delete_subscription(1, 1)

        mock_session.query.return_value.filter_by.return_value.first.assert_called_once()
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_add_ticket(self, mock_session):
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()

        add_ticket(1, "plackart", 1000)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.queries.session")
    def test_delete_ticket_by_id(self, mock_session):
        mock_ticket = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_ticket
        )
        mock_session.delete = MagicMock()
        mock_session.commit = MagicMock()

        delete_ticket_by_id(1)

        mock_session.query.return_value.filter_by.return_value.first.assert_called_once()
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()

# python3 -m unittest ./src/tests/queries_test.py
