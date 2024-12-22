from datetime import datetime, timedelta

from src.core.rzd import get_train_routes_with_session, get_station_code


def test_get_train_routes_with_seats():
    """Тест на получение маршрутов (места есть)"""
    code_from = "2000000"
    code_to = "2004000"
    date = (datetime.now() + timedelta(days=10)).strftime("%d.%m.%Y")

    result = get_train_routes_with_session(code_from, code_to, date, with_seats=True)
    assert result is not None, "Результат должен быть не None, это значит была ошибка"
    assert isinstance(result, dict) or (
        result == "NO TICKETS"
    ), "Ожидается, что результат будет словарем или строкой 'NO TICKETS'"


def test_get_train_routes_without_seats():
    """Тест на получение маршрутов (без мест)"""
    code_from = "2000000"
    code_to = "2004000"
    date = (datetime.now() + timedelta(days=10)).strftime("%d.%m.%Y")

    result = get_train_routes_with_session(code_from, code_to, date, with_seats=False)
    assert result is not None, "Результат должен быть не None"
    assert (
        isinstance(result, dict) or result == "NO TICKETS"
    ), "Ожидается, что результат будет словарем или строкой 'NO TICKETS'"


def test_get_train_routes_with_seats_get_codes():
    """Тест на получение маршрутов без кодов (места есть)"""
    code_from = get_station_code("москва")
    assert code_from == "2000000"
    code_to = get_station_code("владивосток")
    assert code_to == "2034130"
    date = (datetime.now() + timedelta(days=10)).strftime("%d.%m.%Y")

    result = get_train_routes_with_session(code_from, code_to, date, with_seats=True)
    assert result is not None, "Результат должен быть не None, это значит была ошибка"
    assert isinstance(result, dict) or (
        result == "NO TICKETS"
    ), "Ожидается, что результат будет словарем или строкой 'NO TICKETS'"


def test_get_train_routes_without_seats_get_codes():
    """Тест на получение маршрутов без кодов (мест нет)"""
    code_from = get_station_code("яя")
    assert code_from == "2028022"
    code_to = get_station_code("санкт-петербург")
    assert code_to == "2004000"
    date = (datetime.now() + timedelta(days=10)).strftime("%d.%m.%Y")

    result = get_train_routes_with_session(code_from, code_to, date, with_seats=False)
    assert result is not None, "Результат должен быть не None, это значит была ошибка"
    assert isinstance(result, dict) or (
        result == "NO TICKETS"
    ), "Ожидается, что результат будет словарем или строкой 'NO TICKETS'"
