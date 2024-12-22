import json
import time
import logging
import requests

def get_train_routes_with_session(code_from, code_to, date, with_seats=True):
    """Получение маршрутов от города с кодом code_from в город с code_to."""

    base_url = "https://pass.rzd.ru/timetable/public/ru"
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
                Chrome/117.0.0.0 Safari/537.36",
        "Referer": "https://pass.rzd.ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
    }

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
    if response.status_code == 200:
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

                if second_response.status_code == 200:
                    data = second_response.json()
                    logging.info(f"Второй запрос выполнен успешно, JSON: {data}")
                    try:
                        return data
                    except ValueError:
                        logging.error(
                            f"Ошибка преобразования ответа второго запроса в JSON, статус ошибки: {second_response.status_code}, причина: {second_response.reason}"
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
            logging.error("Ошибка преобразования ответа первого запроса в JSON.")
            logging.debug(response.text)
            return None
    else:
        logging.error(
            f"Что-то пошло не так при первом запросе, статус ошибки: {response.status_code}, причина: {response.reason}"
        )
        return None
