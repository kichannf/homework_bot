import logging
import os
import requests
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import telegram
from telegram import Bot

from exceptions import (
    UniqueException, UnauthorizedError, InternalServerError,
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


def send_message(bot, message):
    """Отправка сообщения о статусе проверки ДР."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.info(f'Сообщение "{message}" успешно отправлено.')


def get_api_answer(current_timestamp):
    """Запрос к АПИ Яндекса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    logger.debug('Обращение к API')
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise UnauthorizedError('Ошибка авторизации. Ошибка в токене API')
    if response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        raise InternalServerError('Внутренняя ошибка сервера')
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise FoundNot('Сервер не может найти запрашиваемый ресурс.')
    if response.status_code == HTTPStatus.REQUEST_TIMEOUT:
        raise RequestTimeout(
            'Сервер хотел бы отключить это неиспользуемое соединение'
        )
    try:
        return response.json()
    except JSONDecodeError as error:
        logger.exception(error)
        raise error


def check_response(response):
    """Проверка ответа API на корректность."""
    """Если ответ API соответствует ожиданиям, возвращает список ДР."""
    if not isinstance(response, dict):
        raise TypeError('Не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Ошибка доступа по ключу "homeworks"')
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
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Потеряли переменную окружения')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 60 * 60 * 24 * 14
    last_status = 'last_status'
    homework_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            homework_status = parse_status(homework[0])
            if homework_status != last_status:
                send_message(bot, homework_status)
                last_status = homework_status
            else:
                logger.debug('Отсутствие в ответе новых статусов')

        except UniqueException as error:
            homework_status = str(error)
            logger.error(homework_status)

        except KeyError:
            homework_status = 'Ошибка получения ДР'
            logger.error(homework_status)

        except TypeError:
            homework_status = 'Ошибка получения ДР'
            logger.error(homework_status)

        except telegram.error.BadRequest:
            homework_status = 'Ошибка обработки запроса. Проверь ID клиента'
            logger.error(homework_status)
            time.sleep(RETRY_TIME)

        except telegram.error.Unauthorized:
            homework_status = 'Ошибка телеграмм токена'
            logger.error(homework_status)
            time.sleep(RETRY_TIME)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
