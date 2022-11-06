import logging
import os
import requests
import sys
import time
from http import HTTPStatus

import telegram
from telegram import Bot

from exceptions import (
    UnauthorizedError, InternalServerError, NotDict,
    FoundNot, NotList, RequestTimeout
)

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# Последний отправленный статус
MESSAGE_STATUS = ''


def send_message(bot, message):
    """Отправка сообщения о статусе проверки ДР."""
    global MESSAGE_STATUS
    if MESSAGE_STATUS != message:
        try:
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )
            logger.info(f'Сообщение "{message}" успешно отправлено.')
            MESSAGE_STATUS = message
        except telegram.error.BadRequest:
            logger.error('Ошибка обработки запроса. Проверь ID клиента')
        except telegram.error.Unauthorized:
            logger.error('Ошибка телеграмм токена')
    else:
        logger.debug('Статус проверки ДР не поменялся')


def get_api_answer(current_timestamp):
    """Запрос к АПИ Яндекса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise UnauthorizedError('Ошибка авторизации. Ошибка в токене')
    if response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        raise InternalServerError('Внутренняя ошибка сервера')
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise FoundNot('Сервер не может найти запрашиваемый ресурс.')
    if response.status_code == HTTPStatus.REQUEST_TIMEOUT:
        raise RequestTimeout(
            'Сервер хотел бы отключить это неиспользуемое соединение'
        )
    homeworks = response.json()
    return homeworks


def check_response(response):
    """Проверка ответа API на корректность."""
    """Если ответ API соответствует ожиданиям, возвращает список ДР."""
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        raise NotDict('Объект не является словарем')
    if 'homeworks' not in response:
        raise LookupError('Ошибка доступа по ключу "homeworks"')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise NotList('Объект не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает статус работы."""
    """В случае успеха, функция возвращает статус проверки работы"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    """которые необходимы для работы программы."""
    environment_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(environment_variables):
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Потеряли переменную окружения')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 600

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message_result = parse_status(homework[0])
            send_message(bot, message_result)

        except UnauthorizedError:
            send_message(
                bot, 'Ошибка авторизации. Ошибка в токене'
            )
            logger.error('Ошибка авторизации. Ошибка в токене.')
        except InternalServerError:
            send_message(bot, 'Внутренняя ошибка сервера.')
            logger.error('Внутренняя ошибка сервера')
        except FoundNot:
            send_message(
                bot, 'Сервер не может найти запрашиваемый ресурс'
            )
            logger.error('Сервер не может найти запрашиваемый ресурс')
        except NotDict:
            send_message(bot, 'Объект не является словарем')
            logger.error('Ошибка получения статуса Домашней Работы')
        except NotList:
            send_message(bot, 'Объект не является списком')
            logger.error('Ошибка получения статуса Домашней Работы')
        except LookupError:
            logger.error('Ошибка получения ДР')
            send_message(bot, 'Ошибка получения ДР.')

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
