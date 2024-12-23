import http
import json
import logging
import time
from datetime import datetime

import requests


def get_train_routes_with_session(code_from : int, code_to : int, date : datetime, place_type : str = None, with_seats : bool = True):
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
        "dt0": date.strftime("%d.%m.%Y"),
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
                        return get_parsed_data(data, place_type)
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
            logging.error(
                f"Ошибка преобразования ответа первого запроса в JSON,  \
                          статус ошибки: {second_response.status_code}, причина: {second_response.reason}, ошибка: {e}"
            )
            logging.debug(response.text)
            return None
    else:
        logging.error(
            f"Что-то пошло не так при первом запросе, статус ошибки: {response.status_code}, причина: {response.reason}"
        )
        return None

def get_parsed_data(result_data, place_type):
    try:
        routes = []
        tp = result_data.get("tp", [])
        if tp and isinstance(tp, list) and ("list" in tp[0]):
            trains = tp[0]["list"]

            for train in trains:

                cars = train.get("cars")

                if place_type is not None:
                    best_price = None
                    if cars:
                        prices = [c.get("tariff") for c in cars \
                                    if (c.get("tariff") is not None) \
                                          and (c.get("typeLoc") == place_type) \
                                            and (c.get("disabledPerson", None) is None)]
                        if prices:
                            best_price = min(prices)
                    if best_price is None:
                        best_price = "нет данных"
                        continue

                else:
                    best_price = None
                    if cars:
                        for c in cars:
                            price = c.get("tariff")
                            if (price is not None) \
                                    and (c.get("disabledPerson", None) is None):


                                if (best_price is None) or (best_price > price):
                                    best_price = price
                                    place_type = c.get("type")


                    if best_price is None:
                        best_price = "нет данных"
                        continue



                route_id = train.get("number")

                station_from = train.get("station0")
                station_to = train.get("station1")
                city_from = tp[0].get("from")
                city_from_code = tp[0].get("fromCode")
                city_where = tp[0].get("where")
                city_where_code = tp[0].get("whereCode")

                route_from = train.get("route0")
                route_to = train.get("route1")
                station_code_from = train.get("code0")
                station_code_to = train.get("code1")


                format = "%d.%m.%Y %H:%M"

                date_time0 = f'{train.get("date0")} {train.get("time0")}'
                date_time0 = datetime.strptime(date_time0, format)

                date_time1 = f'{train.get("date1")} {train.get("time1")}'
                date_time1 = datetime.strptime(date_time1, format)


                routes.append(
                    {
                        "route_id": route_id,
                        "station_from": station_from,
                        "station_to": station_to,
                        "station_code_from": station_code_from,
                        "station_code_to": station_code_to,
                        "route_global": f"{route_from}-{route_to}",
                        "datetime0": date_time0,
                        "datetime1": date_time1,
                        "best_price": best_price,
                        "class": place_type,
                        "from": city_from,
                        "fromCode": city_from_code,
                        "where": city_where,
                        "whereCode": city_where_code
                    }
                )
        return routes
    except Exception as e:
        logging.error(f"Ошибка при обработке данных маршрута: {e}")
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
