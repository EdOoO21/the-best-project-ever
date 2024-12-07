import schedule
import time
from update_db import update


def job():
    """Задача, которая будет выполняться каждые 5 минут"""
    update()


schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
