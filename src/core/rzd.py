import json
import logging
import time
import http
import requests


def get_train_routes_with_session(code_from, code_to, date, with_seats=True):
    """Получение маршрутов от города с кодом code_from в город с code_to."""

    base_url = "https://pass.rzd.ru/timetable/public/ru"
    session = requests.Session()

    file = open("resources/headers.json")
    headers = json.load(file)

    params = {
        "layer_id": 5827,
        "dir": 0,
        "tfl": 1,
        "checkSeats": 1 if with_seats else 0,
        "code0": code_from,
        "code1": code_to,
        "dt0": date,
    }

    response = session.get(base_url, params=params, headers=headers)
    if response.status_code == http.HTTPStatus.OK:
        try:
            result = response.json().get("result")
            if result == "RID":

                data = response.json()
                rid = data.get("RID")

                logging.info(f"Первый запрос выполнен успешно, JSON: {data}")

                time.sleep(3)

                second_url = f"{base_url}?layer_id=5827&rid={rid}"
                second_response = session.get(
                    second_url, headers=headers, params=params
                )

                if response.status_code == http.HTTPStatus.OK:
                    data = second_response.json()
                    logging.info(f"Второй запрос выполнен успешно, JSON: {data}")
                    try:
                        return data
                    except Exception as e:
                        logging.error(
                            f"Ошибка преобразования ответа второго запроса в JSON, статус ошибки: {second_response.status_code}, причина: {second_response.reason}, ошибка: {e}"
                        )
                        logging.debug(second_response.text)
                        return None
                else:
                    logging.error(
                        f"Что-то пошло не так при втором запросе, статус ошибки: {second_response.status_code}, причина: {second_response.reason}"
                    )
                    return None
            elif result == "OK":
                logging.info("Нет доступных билетов.")
                return "NO TICKETS"
            else:
                return None
        except Exception as e:
            logging.error(f"Ошибка преобразования ответа первого запроса в JSON,  \
                          статус ошибки: {second_response.status_code}, причина: {second_response.reason}, ошибка: {e}")
            logging.debug(response.text)
            return None
    else:
        logging.error(
            f"Что-то пошло не так при первом запросе, статус ошибки: {response.status_code}, причина: {response.reason}"
        )
        return None


def get_station_code(station_name):
    """
    Получает код города/станции по названию.
    """
    with open("resources/city_codes.json", "r") as file:
        file = json.load(file)
        ans = file.get(station_name)
        if ans:
            return ans
        raise ValueError("Город/станция не найдены")